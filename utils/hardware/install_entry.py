"""Approval/session orchestration; all successful and failed writes stay halted."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import uuid
import sys
from flash_journal import Journal,execute

@contextmanager
def lease(folder,name='session.lock'):
    # Kernel lock releases on process death. Keep the inode/file to avoid races.
    path=Path(folder)/name
    with path.open('a+b') as stream:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

def active(kit):
    pointer=kit.folder/'active.json'
    if not pointer.exists():return None
    try:
        data=json.loads(pointer.read_text(encoding='utf8'))
        if data.get('schema')!=1:raise ValueError('Invalid active pointer schema')
        name=data['journal']
        if Path(name).name!=name or not name.startswith('transaction-') or not name.endswith('.json'):
            raise ValueError('Invalid journal path')
        record=Journal.read(kit.folder/name)
        if record['plan_seal']!=kit.plan.seal:raise ValueError('Active transaction belongs to a different kit')
        return record
    except (KeyError,OSError,ValueError) as exc:raise ValueError('Active journal invalid; install forbidden') from exc

def activate(kit,journal):
    path=kit.folder/'active.json';temp=kit.folder/('active-'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('x',encoding='utf8') as stream:
            json.dump({'schema':1,'journal':journal.path.name},stream);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()

def finish_context(context):
    primary=sys.exc_info()[1]
    errors=[]
    try:context.hold()
    except BaseException as exc:errors.append('Hold: '+type(exc).__name__+': '+str(exc))
    try:context.close()
    except BaseException as exc:errors.append('Close: '+type(exc).__name__+': '+str(exc))
    if errors:
        context.report['exit_errors']=errors
        if primary is None:raise RuntimeError('; '.join(errors))
        primary.add_note('Exit unconfirmed; '+ '; '.join(errors))

def authorized_run(kit,action,approval,opener):
    if action not in ('install','recover') or approval!=kit.approval(action):
        raise ValueError('Exact device-bound approval required before probe opening')
    with lease(Path(tempfile.gettempdir()),'new-deviation-tx15-pwlink2.lock'),lease(kit.folder):
        if action=='install':
            previous=active(kit)
            if previous and previous['original_resume_forbidden']:raise ValueError('Dirty/installed transaction exists; recover first')
        # Explicit recovery to this UID-bound, known original may repair even a
        # corrupt/missing active pointer; it never resumes unknown content.
        context=opener()
        try:
            context.enter(kit)
            path=kit.folder/('transaction-'+uuid.uuid4().hex+'.json')
            result=execute(kit.plan,lambda journal:context.backend(journal,read_only=False),action,
                kit.plan.seal if action=='install' else kit.plan.recovery_seal,path,
                on_create=lambda journal:activate(kit,journal))
            context.report['transaction_result']=result
            return context.report
        finally:
            finish_context(context)

def rehearse(kit,opener):
    with lease(Path(tempfile.gettempdir()),'new-deviation-tx15-pwlink2.lock'),lease(kit.folder):
        context=opener()
        try:
            observed=context.enter(kit)
            backend=context.backend(read_only=True)
            if backend.check_device()!=observed:raise RuntimeError('RAM and SWD Flash observations differ')
            if backend.read_internal(0x08000000,64)!=kit.plan.original_internal[:64]:raise RuntimeError('Original internal prefix differs')
            if backend.read_external(0,64)!=kit.plan.original_external[:64]:raise RuntimeError('Original external prefix differs')
            context.report['rehearsal']='reset/RAM/read-only-prefixes-verified'
            context.report['flash_mutation_commands']=0
            return context.report
        finally:
            finish_context(context)
