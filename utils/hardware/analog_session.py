"""ADC12 reset/clock recovery for reset-entry RAM application sessions."""
ENABLE=0x580244d8
RESET=0x58024480
BIT=1<<5
CONTROL_ADDRS={ENABLE,RESET}
def capture(read):
    saved={a:read(a) for a in CONTROL_ADDRS}
    if any(v&BIT for v in saved.values()):
        raise RuntimeError('ADC12 must be reset-idle before application')
    return saved

def restore(read,write,saved):
    write(ENABLE,read(ENABLE)|BIT)
    read(ENABLE)
    write(RESET,read(RESET)|BIT)
    if not read(RESET)&BIT: raise RuntimeError('ADC12 reset failed')
    write(RESET,saved[RESET])
    write(ENABLE,saved[ENABLE])
    if any(read(a)!=saved[a] for a in CONTROL_ADDRS):
        raise RuntimeError('ADC12 clock/reset restore mismatch')
    return {hex(a):hex(read(a)) for a in CONTROL_ADDRS}
