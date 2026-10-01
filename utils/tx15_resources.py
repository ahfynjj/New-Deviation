"""Generate bounded read-only resources from tracked Deviation assets."""
from pathlib import Path
import subprocess

def generate(root,out):
    files={}
    # Use drawn background: avoid embedding a full-screen background bitmap.
    for p in sorted((root/'src/fs/base_fonts/media').glob('*.fon')):
        files['media/'+p.name]=p.read_bytes()
    for p in sorted((root/'src/fs/320x240x16/media').glob('*.bmp')):
        if p.name not in ('backgrnd.bmp','splash.bmp'):
            files['media/'+p.name]=p.read_bytes()
    for name,size in (('15normal',15),('23bold',23)):
        dst=out/(name+'.fon')
        command=[str(root.parent/'tools/msys64/usr/bin/perl.exe'),str(root/'utils/font/bdf_to_font.pl'),
            '-maxsize',str(size),'-mode','bin',str(root/'src/fonts'/(name+'.bdf')),
            '-out',str(dst),'-minspace','8','-ascii']
        subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
        files['media/'+name+'.fon']=dst.read_bytes()
    files['media/config.ini']=(root/'src/fs/320x240x16/media/config.ini').read_bytes().replace(b'drawn_background=0',b'drawn_background=1')
    files['layout/default.ini']=(root/'src/fs/tx15/layout/default.ini').read_bytes()
    files['models/model1.ini']=b'name=TX15 RAM Test\nmixermode=Advanced\n[radio]\nprotocol=None\nnum_channels=4\n[mixer]\nsrc=AIL\ndest=Ch1\n[mixer]\nsrc=ELE\ndest=Ch2\n[mixer]\nsrc=THR\ndest=Ch3\n[mixer]\nsrc=RUD\ndest=Ch4\n'
    total=sum(map(len,files.values()))
    if total>512*1024: raise ValueError('Embedded resources exceed 512 KiB limit')
    dst=out/'resources.c'
    with dst.open('w') as f:
        f.write('#include "romfs.h"\n')
        for i,(name,data) in enumerate(files.items()):
            f.write('static const uint8_t asset%d[] __attribute__((section(".resources")))={%s};\n'%(i,','.join(str(b) for b in data)))
        f.write('const struct tx15_resource tx15_resources[]={\n')
        for i,(name,data) in enumerate(files.items()):
            f.write('{"%s",asset%d,sizeof(asset%d)},\n'%(name,i,i))
        f.write('};\nconst size_t tx15_resource_count=sizeof(tx15_resources)/sizeof(tx15_resources[0]);\n')
    print(f'Embedded {len(files)} read-only resources, {total} bytes')
    return dst
