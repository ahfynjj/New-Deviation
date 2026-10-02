"""Decode bounded bench captures for inspection, not a replacement Lua UI.

Keep raw field bytes in the private session log; do not publish device secrets.
"""
TYPES={0:'uint8',1:'int8',2:'uint16',3:'int16',4:'uint32',5:'int32',
       8:'float',9:'selection',10:'string',11:'folder',12:'info',13:'command',127:'out_of_range'}

def decode(data):
    result={}
    pos=0
    def take(n):
        nonlocal pos
        if n<0 or pos+n>len(data):raise ValueError('Truncated field')
        value=data[pos:pos+n];pos+=n;return value
    def number(n=1,signed=False):return int.from_bytes(take(n),'big',signed=signed)
    def text():
        nonlocal pos
        end=data.find(b'\0',pos)
        if end<0:raise ValueError('Unterminated string')
        value=take(end-pos).decode('utf-8','replace');take(1);return value
    try:
        result['parent']=number();kind=number()
        result.update(hidden=bool(kind&128),type_id=kind&127,type=TYPES.get(kind&127,'unknown'))
        kind &=127
        if kind==127:return result
        result['name']=text()
        if kind<=5:
            n=(1,1,2,2,4,4)[kind]
            for key in ('value','min','max','default'):result[key]=number(n,bool(kind&1))
            result['unit']=text()
        elif kind==8:
            for key in ('raw_value','min','max','default'):result[key]=number(4,True)
            precision=number();result['precision']=precision;result['step']=number(4,True)
            result['unit']=text()
            if precision>6:raise ValueError('Unsupported decimal precision')
            result['value']=result['raw_value']/10**precision
        elif kind==9:
            result['options']=text().split(';')
            for key in ('index','min','max','default'):result[key]=number()
            result['unit']=text()
            if result['index']>=len(result['options']):raise ValueError('Selection index out of bounds')
            result['value']=result['options'][result['index']]
        elif kind in (10,12):result['value']=text()
        elif kind==13:
            result['status']=number();result['timeout']=number();result['info']=text()
        elif kind!=11:raise ValueError('Unsupported field type')
    except ValueError as error:result['error']=str(error)
    return result
