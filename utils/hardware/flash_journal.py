"""Persistent command intentions. No CLI, device opening, or implicit approval.

fsync + atomic replacement protects against process/USB interruption. It is not
a guarantee against every Windows/storage power-loss failure; keep backups on
separate media before installation. Never resume an old PC after a dirty intent.
"""
import copy
import hashlib
import json
import os
import time
from pathlib import Path
import uuid

def _digest(record):
    data={k:v for k,v in record.items() if k!='record_sha256'}
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Journal:
    def __init__(self,path,plan,record):
        self.path=Path(path);self.plan=plan;self.record=record

    @staticmethod
    def read(path):
        record=json.loads(Path(path).read_text(encoding='utf8'))
        if record.get('schema')!=1 or record.get('record_sha256')!=_digest(record):
            raise ValueError('Corrupt/incomplete journal; forbid original resume')
        return record

    @classmethod
    def create(cls,path,plan,action,authorization):
        if action not in ('install','recover'):raise ValueError('Unknown transaction action')
        expected=plan.seal if action=='install' else plan.recovery_seal
        if authorization!=expected:raise ValueError('Exact transaction authorization required')
        path=Path(path)
        record=dict(schema=1,plan_seal=plan.seal,manifest=plan.manifest(),action=action,
            sequence=0,state='prepared',external_dirty=action=='recover',
            internal_dirty=action=='recover',original_resume_forbidden=action=='recover',
            checkpoints=[],last_intent=None)
        record['record_sha256']=_digest(record)
        # Exclusive creation: never silently overwrite evidence of a dirty run.
        with path.open('x',encoding='utf8') as stream:
            json.dump(record,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        return cls(path,plan,record)

    def _save(self,record):
        if self.read(self.path)!=self.record:raise ValueError('Journal changed by another process')
        record['record_sha256']=_digest(record)
        temp=self.path.with_name(self.path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with temp.open('x',encoding='utf8') as stream:
                json.dump(record,stream,indent=2);stream.flush();os.fsync(stream.fileno())
            # Windows readers/virus scanners may briefly deny replacement.
            # Retry only that OS failure, before any new hardware command;
            # persistent denial still leaves the previous durable intent intact.
            for attempt in range(10):
                if self.read(self.path)!=self.record:
                    raise ValueError('Journal changed by another process')
                try:
                    os.replace(temp,self.path)
                    break
                except PermissionError as error:
                    if getattr(error,'winerror',None) not in (5,32,33) or attempt==9:
                        raise
                    time.sleep(0.05)
            self.record=record
        finally:
            if temp.exists():temp.unlink()

    def before(self,operation,address,value):
        if self.record['state'] not in ('prepared','command-complete','checkpoint'):
            raise ValueError('Unfinished/failed intent; recovery required')
        install=self.record['action']=='install'
        external=self.plan.payload if install else self.plan.original_external
        internal=self.plan.boot if install else self.plan.original_internal
        erase_bytes=self.plan.erase_bytes if install else 1048576
        size=len(value) if type(value) is bytes else value
        valid=False
        if operation=='external-erase':valid=size==4096 and address%4096==0 and 0<=address<=erase_bytes-4096
        elif operation=='external-program':
            valid=type(value) is bytes and size==256 and address%256==0 and 0<=address<=len(external)-256 and value==external[address:address+256]
        elif operation=='internal-erase':valid=(address,size)==(0x08000000,131072)
        elif operation=='internal-program':
            offset=address-0x08000000
            valid=type(value) is bytes and size==32 and offset%32==0 and 0<=offset<=len(internal)-32 and value==internal[offset:offset+32]
        if not valid:raise ValueError('Intent differs from bounded reviewed image')
        is_internal=operation.startswith('internal-')
        stage='internal' if is_internal else 'external'
        if stage in self.record['checkpoints']:raise ValueError('Verified stage cannot be mutated again')
        if is_internal and 'external' not in self.record['checkpoints']:
            raise ValueError('External verification must precede internal mutation')
        r=copy.deepcopy(self.record)
        r['sequence']+=1;r['state']='intent';r['original_resume_forbidden']=True
        r['internal_dirty' if is_internal else 'external_dirty']=True
        r['last_intent']=dict(operation=operation,address=hex(address),bytes=size,
            data_sha256=hashlib.sha256(value).hexdigest() if type(value) is bytes else None)
        self._save(r) # Must succeed BEFORE WREN/FLASH KEY/start/data.

    def command_complete(self):
        if self.record['state']!='intent':raise ValueError('No pending command')
        r=copy.deepcopy(self.record);r['state']='command-complete';self._save(r)

    def checkpoint(self,stage):
        if stage not in ('external','internal') or self.record['state'] not in ('command-complete','checkpoint'):
            raise ValueError('Invalid verification checkpoint')
        if stage=='internal' and 'external' not in self.record['checkpoints']:raise ValueError('Wrong verification order')
        r=copy.deepcopy(self.record);r['state']='checkpoint'
        if stage not in r['checkpoints']:r['checkpoints'].append(stage)
        self._save(r)

    def failed(self,message):
        r=copy.deepcopy(self.record);r['state']='failed';r['error']=str(message);self._save(r)

    def finish(self,result):
        recovery=self.record['action']=='recover'
        expected=['original-external-verified','original-internal-verified'] if recovery else ['external-verified','internal-verified']
        if self.record['state']!='checkpoint' or result!=expected or self.record['checkpoints']!=['external','internal']:
            raise ValueError('Both verified stages required')
        r=copy.deepcopy(self.record);r['state']='recovered' if recovery else 'installed'
        r['original_resume_forbidden']=not recovery
        if recovery:r['external_dirty']=r['internal_dirty']=False
        self._save(r)

def execute(plan,backend_factory,action,authorization,path,on_create=None):
    """Software coordinator, not a probe-opening or recovery-entry CLI.

    Caller must already hold a reviewed RAM context and explicit human approval.
    Does not reset, resume, disconnect, or replace a prior failed journal.
    """
    from flash_transaction import install,recover
    journal=Journal.create(path,plan,action,authorization)
    try:
        if on_create is not None:on_create(journal)
        backend=backend_factory(journal)
        result=(install if action=='install' else recover)(plan,backend,authorization)
        journal.finish(result)
        return result
    except BaseException as error:
        # If disk fails here, the previously durable intent stays unresolved.
        # Never mask the primary target/interrupt error with a logging failure.
        try:journal.failed(error)
        except Exception as log_error:
            error.add_note('Journal update failed; preserve last intent: '+str(log_error))
        raise
