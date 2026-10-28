"""Render proposed 480x320 screens. Design artifacts, not a radio simulator.

Requires Pillow and Windows Segoe UI. No firmware assets or dependencies change.
"""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
SCALE = 3
BG, CARD, EDGE = '#14181E', '#232A33', '#35404D'
FG, MUTED, ACCENT = '#F3F5F7', '#AEB8C4', '#FF9E32'


class Screen:
    def __init__(self):
        self.image = Image.new('RGB', (480*SCALE, 320*SCALE), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320" viewBox="0 0 480 320">',
                    f'<rect width="480" height="320" fill="{BG}"/>']
        self.hits = []

    def rect(self, x, y, w, h, fill=CARD, stroke=None, radius=6, thickness=1):
        assert x >= 0 and y >= 0 and x+w <= 480 and y+h <= 320
        self.draw.rounded_rectangle(tuple(round(v*SCALE) for v in (x, y, x+w, y+h)),
                                    radius=radius*SCALE, fill=fill, outline=stroke,
                                    width=thickness*SCALE)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
                        f'fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{thickness}"/>')

    def line(self, points, color=FG, width=2):
        self.draw.line([(round(x*SCALE), round(y*SCALE)) for x, y in points], fill=color, width=width*SCALE)
        self.svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" '
                        f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')

    def text(self, x, y, label, size=18, color=FG, bold=False, align='left'):
        font = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf', size*SCALE)
        width = self.draw.textlength(label, font=font)/SCALE
        left = x-(width/2 if align == 'center' else width if align == 'right' else 0)
        assert left >= 0 and left+width <= 480, (label, left, width)
        self.draw.text((round(left*SCALE), y*SCALE), label, font=font, fill=color, anchor='lt')
        anchor = {'left': 'start', 'center': 'middle', 'right': 'end'}[align]
        self.svg.append(f'<text x="{x}" y="{y}" dy="{size*.8}" text-anchor="{anchor}" '
                        f'font-family="Segoe UI,sans-serif" font-size="{size}" '
                        f'font-weight="{700 if bold else 400}" fill="{color}">{escape(label)}</text>')

    def hit(self, name, x, y, w, h):
        assert w >= 40 and h >= 40
        for _, a, b, c, d in self.hits:
            assert x+w <= a or a+c <= x or y+h <= b or b+d <= y, name
        self.hits.append((name, x, y, w, h))

    def button(self, x, y, w, label, primary=False):
        self.rect(x, y, w, 40, ACCENT if primary else CARD, None if primary else EDGE)
        self.text(x+w/2, y+10, label, 18, BG if primary else FG, bold=True, align='center')
        self.hit(label, x, y, w, 40)

    def save(self, stem):
        self.image.save(OUT/(stem+'.png'))
        (OUT/(stem+'.svg')).write_text('\n'.join(self.svg+['</svg>'])+'\n', encoding='utf8')


def icon(s, kind, x, y, color):
    if kind == 'model':
        s.line([(x+20,y),(x+24,y+14),(x+39,y+22),(x+39,y+25),(x+23,y+22),
                (x+23,y+31),(x+29,y+35),(x+11,y+35),(x+17,y+31),(x+17,y+22),
                (x+1,y+25),(x+1,y+22),(x+16,y+14),(x+20,y)],color)
    elif kind == 'tx':
        s.rect(x+2,y+8,36,28,fill=None,stroke=color,radius=5,thickness=2)
        s.line([(x+16,y+8),(x+22,y)],color)
        for a in (12,28):
            s.rect(x+a-5,y+17,10,10,fill=None,stroke=color,radius=5,thickness=2)
            s.line([(x+a,y+18),(x+a+3,y+14)],color)
    elif kind == 'usb':
        s.line([(x+20,y+36),(x+20,y+1),(x+15,y+6),(x+20,y+1),(x+25,y+6)],color)
        s.line([(x+20,y+25),(x+8,y+18),(x+8,y+10)],color)
        s.line([(x+20,y+19),(x+32,y+12),(x+32,y+8)],color)
        s.rect(x+5,y+6,6,6,color,radius=3)
        s.rect(x+29,y+3,6,6,color,radius=0)
    elif kind == 'rf':
        for off in (0,8,16):
            s.line([(x+20-off,y+18+off),(x+20-off,y+6+off/2),
                    (x+20,y+off/2),(x+20+off,y+6+off/2),(x+20+off,y+18+off)],color)
        s.line([(x+20,y+18),(x+20,y+36)],color)
    elif kind == 'audio':
        s.line([(x+3,y+14),(x+12,y+14),(x+23,y+5),(x+23,y+34),
                (x+12,y+25),(x+3,y+25),(x+3,y+14)],color)
        s.line([(x+29,y+12),(x+34,y+19),(x+29,y+27)],color)
        s.line([(x+34,y+6),(x+40,y+19),(x+34,y+33)],color)
    else:
        s.rect(x+9,y+1,23,34,fill=None,stroke=color,radius=4,thickness=2)
        s.line([(x+20,y+25),(x+20,y+12),(x+24,y+12),(x+25,y+23),
                (x+32,y+20),(x+36,y+24),(x+31,y+37)],color)


def main_menu():
    s = Screen()
    s.text(12,9,'Main menu',22,bold=True)
    s.text(468,13,'8.18 V',16,MUTED,align='right')
    s.line([(0,36),(480,36)],EDGE,1)
    entries = [('Model menu','model'),('Transmitter','tx'),('USB','usb'),
               ('ELRS Lua','rf'),('Audio test','audio'),('Touch test','touch')]
    for i,(label,kind) in enumerate(entries):
        x,y=12+(i%3)*155,52+(i//3)*104
        selected=i==0
        s.rect(x,y,146,96,CARD,ACCENT if selected else EDGE,8,2 if selected else 1)
        icon(s,kind,x+53,y+12,ACCENT if selected else MUTED)
        s.text(x+73,y+64,label,18,FG,bold=selected,align='center')
        s.hit(label,x,y,146,96)
    s.line([(0,268),(480,268)],EDGE,1)
    s.button(12,276,112,'Back')
    s.button(264,276,44,'<')
    s.text(366,287,'1 / 2',16,MUTED,align='center')
    s.button(424,276,44,'>')
    s.save('ethos-main-menu')
    return s


def mix_editor():
    s=Screen()
    s.text(12,9,'CH1 / Complex',22,bold=True)
    s.text(468,13,'Mix 1 / 2',16,MUTED,align='right')
    s.line([(0,36),(480,36)],EDGE,1)
    fields=[('Source','AIL'),('Switch','SA1'),('Mux','Replace'),('Scale','100 %'),('Offset','0 %')]
    for i,(label,value) in enumerate(fields):
        x,y=12,44+i*44
        s.rect(x,y,292,40,CARD,ACCENT if i==0 else EDGE,6,2 if i==0 else 1)
        s.text(x+12,y+11,label,16,MUTED)
        s.text(x+254,y+8,value,20,bold=True,align='right')
        s.text(x+278,y+10,'>',18,MUTED,align='right')
        if i==0:s.text(x+82,y+14,'EDIT',10,ACCENT,bold=True)
        s.hit(label,x,y,292,40)
    s.rect(316,44,152,172,CARD,EDGE)
    s.text(328,54,'Curve',16,MUTED)
    s.text(456,55,'1-to-1',14,MUTED,align='right')
    for x in (328,360,392,424,456):s.line([(x,84),(x,180)],EDGE,1)
    for y in (84,108,132,156,180):s.line([(328,y),(456,y)],EDGE,1)
    s.line([(392,84),(392,180)],MUTED,1)
    s.line([(328,132),(456,132)],MUTED,1)
    s.line([(328,180),(456,84)],ACCENT,2)
    s.rect(411,112,6,6,ACCENT,radius=3)
    s.text(328,193,'Output',14,MUTED)
    s.text(456,191,'+34 %',16,FG,bold=True,align='right')
    s.button(316,224,152,'Curve >')
    s.line([(0,268),(480,268)],EDGE,1)
    s.button(12,276,144,'Cancel')
    s.button(168,276,144,'More 1 / 2')
    s.button(324,276,144,'OK',True)
    s.save('ethos-mix-editor')
    return s


if __name__ == '__main__':
    a,b=main_menu(),mix_editor()
    print(f'Rendered two 480x320 concepts at {SCALE}x; {len(a.hits)+len(b.hits)} nonoverlapping hit targets checked.')
