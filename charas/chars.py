# Dot Buddy original character pack generator — 26×26 cells per frame, thick outline and 3-tone shading, frames drawn for each motion
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from pix import *
W = H = 26
INK = hexc('#1d1411'); WH = hexc('#ffffff'); CK = hexc('#f1958a'); MOUTH = hexc('#7a2f2a')

def face(cv, ex, ey, eyes, mouth, ck=CK, blush=False):
    if eyes == 'down': ey += 1
    for x in (ex, ex + 4):
        if eyes == 'dizzy': cv.sprite(['e.e', '.e.', 'e.e'], x, ey, {'e': INK})
        elif eyes == 'down': cv.sprite(['ee', 'ee'], x, ey + 1, {'e': INK}); cv.set(x, ey + 1, WH)
        elif eyes == 'open': cv.sprite(['ee', 'ee', 'ee'], x, ey, {'e': INK}); cv.set(x, ey, WH)
        elif eyes == 'wide': cv.sprite(['eee', 'eee', 'eee'], x, ey - 1, {'e': INK}); cv.set(x, ey - 1, WH); cv.set(x + 1, ey - 1, WH)
        elif eyes == 'closed': cv.sprite(['ee'], x, ey + 2, {'e': INK})
        elif eyes == 'happy': cv.sprite(['.e.', 'e.e'], x, ey, {'e': INK})
    for x in (ex - 2, ex - 1, ex + 6, ex + 7):
        cv.set(x, ey + 3, ck)
        if blush: cv.set(x, ey + 2, ck); cv.set(x, ey + 4, ck)
    mx, my = ex + 2, ey + 3
    if mouth == 'smile': cv.sprite(['m.m', '.m.'], mx, my, {'m': INK})
    elif mouth == 'open': cv.sprite(['mmm', 'mrm', '.m.'], mx, my, {'m': INK, 'r': MOUTH})
    elif mouth == 'o': cv.sprite(['.m.', 'm.m', '.m.'], mx, my, {'m': INK})
    elif mouth == 'flat': cv.sprite(['mm'], mx + 1, my + 1, {'m': INK})
    elif mouth == 'yawn': cv.sprite(['mmm', 'mrm', 'mrm', '.m.'], mx, my, {'m': INK, 'r': MOUTH})
    elif mouth == 'pout': cv.sprite(['.m.', 'm.m'], mx, my + 1, {'m': INK})

class Chara:
    name = ''; name_en = ''; feet = True; foot = None; armc = None; line = None
    fps = {'default': 3, 'walk': 8, 'talk': 6, 'wave': 5, 'cheer': 4, 'drag': 6, 'sleep': 1, 'climb': 5, 'hang': 2, 'work': 6, 'roll': 16, 'dizzy': 4, 'ask': 2, 'hum': 3, 'party': 6, 'sneak': 5, 'stalk': 6, 'spin': 8}
    def body(self, cv, y0, sq, ph, P): raise NotImplementedError   # → box (x0, x1, top, bot) and face position (ex, ey)
    def front(self, cv, box, ph, P): pass                          # things to put over the face and arms
    def back(self, cv, box, ph, P): pass                           # things placed behind the body
    def draw(self, bob=0, feet='stand', arms='down', eyes='open', mouth='smile', squash=0, ph=0, blush=False, rot=0, flip=False, **P):
        cv = Cv(W, H)
        if self.feet:
            for fx, lift in ((9, feet == 'l'), (15, feet == 'r')):
                yy = 24 - (1 if lift else 0) - (2 if feet == 'tuck' else 0) + (1 if feet == 'dangle' else 0)
                cv.blob(ellipse(fx + 0.5, yy + 0.5, 2.4, 1.6), self.foot, self.line)
        # the body box must be known first to place the arms — draw once on a blank canvas just to get the box
        tmp = Cv(W, H); box, _ = self.body(tmp, bob, squash, ph, P)
        x0, x1, top, bot = box; my = (top + bot) // 2
        def edge(y, side):                                                         # leftmost and rightmost point of the body on that row
            xs = [x for x in range(W) if tmp.get(x, y)]
            return (min(xs) if side < 0 else max(xs)) if xs else (x0 if side < 0 else x1)
        L = lambda y, d=0: (edge(y, -1) - d, y); R = lambda y, d=0: (edge(y, 1) + d, y)
        pos = {'down': [L(my + 2), R(my + 3, -1)], 'up': [(edge(top + 2, -1) + 1, top - 1), (edge(top + 2, 1) - 1, top - 1)],
               'out': [L(my - 1, 1), R(my - 1, 1)], 'wave0': [L(my + 2), R(top + 3, 1)], 'wave1': [L(my + 2), R(top + 2, 2)],
               'hug': [((x0 + x1) // 2 - 4, bot - 3), ((x0 + x1) // 2 + 3, bot - 3)],
               'type0': [(6, 19), (19, 20)], 'type1': [(6, 20), (19, 19)],          # hit both sides of the laptop the app draws (x 8–18, y 20–24)
               'climb0': [(x1 - 2, top - 1), R(my, 1)], 'climb1': [R(my, 1), (x1 - 1, top)],                  # alternately grab the right wall
               'cover': [((x0 + x1) // 2 - 2, my - 1), ((x0 + x1) // 2 + 3, my - 1)]}[arms]
        arm = lambda a: cv.blob(ellipse(a[0] + 0.5, a[1] + 0.5, 1.8, 1.8), self.armc, self.line)
        self.back(cv, box, ph, P)
        arm(pos[0])
        box, (ex, ey) = self.body(cv, bob, squash, ph, P)
        face(cv, ex, ey, eyes, mouth, getattr(self, 'cheek', CK), blush)
        arm(pos[1])
        self.front(cv, box, ph, P)
        if flip:                                                                   # spin: the turned-around frame
            n = Cv(W, H)
            for y in range(H):
                for x in range(W): n.px[y][W - 1 - x] = cv.px[y][x]
            cv = n
        if rot % 8:                                                                # roll: 45 degrees at a time around the middle of the body, axis height fixed (points that go below the floor are underground, so they are not drawn)
            x0, x1, top, bot = box
            px, py = (x0 + x1 + 1) / 2, (top + bot + 1) / 2
            R = max(x1 - x0, bot - top) / 2 + 0.5
            cv = rotate(cv, (rot % 8) * math.pi / 4, px, py, W / 2, 25 - R)
        return cv
    def frames(self):
        d = self.draw
        return {
            'idle': [d(ph=0), d(bob=1, ph=1)],
            'blink': [d(eyes='closed')],
            'walk': [d(feet='l', ph=0), d(bob=1, ph=1), d(feet='r', ph=0), d(bob=1, ph=1)],
            'happy': [d(eyes='happy', mouth='open', arms='out')],
            'cheer': [d(eyes='happy', mouth='open', arms='up'), d(bob=-1, eyes='happy', mouth='open', arms='up', feet='tuck', ph=1)],
            'crouch': [d(squash=2, bob=1, eyes='closed', mouth='flat')],
            'jump': [d(bob=-1, feet='tuck', arms='up', eyes='happy', mouth='open')],
            'fall': [d(feet='dangle', arms='up', eyes='wide', mouth='o')],
            'drag': [d(feet='dangle', arms='up', eyes='wide', mouth='o'), d(feet='dangle', arms='out', eyes='closed', mouth='o', ph=1)],
            'sleep': [d(eyes='closed', mouth='flat', squash=1, bob=1, sleep=1), d(eyes='closed', mouth='flat', bob=1, ph=1, sleep=1)],
            'talk': [d(mouth='open'), d(mouth='smile', ph=1)],
            'wave': [d(arms='wave0', eyes='happy', mouth='open'), d(arms='wave1', eyes='happy', mouth='open', ph=1)],
            'startle': [d(bob=-1, eyes='wide', mouth='o', arms='out')],
            'sit': [d(feet='tuck', bob=1, arms='hug')],
            'climb': [d(arms='climb0', feet='l', eyes='open', mouth='flat'), d(bob=-1, arms='climb1', feet='r', eyes='open', mouth='flat', ph=1)],
            'hang': [d(arms='up', feet='dangle', eyes='wide', mouth='o'), d(arms='up', feet='dangle', eyes='closed', mouth='o', ph=1)],
            'work': [d(arms='type0', eyes='down', mouth='flat'), d(arms='type1', eyes='down', mouth='flat', ph=1)],
            'roll': [d(feet='tuck', arms='hug', eyes='closed', mouth='flat', squash=1, rot=k) for k in range(8)],   # 8 frames of 45 degrees each
            'peek': [d(eyes='down', mouth='o')],
            'shy': [d(arms='cover', eyes='closed', mouth='flat', blush=True)],
            'dizzy': [d(eyes='dizzy', mouth='o', ph=0), d(eyes='dizzy', mouth='o', bob=1, ph=1)],
            'petted': [d(eyes='happy', mouth='smile', blush=True, squash=1, bob=1)],
            'ask': [d(arms='wave0', mouth='o'), d(arms='wave1', mouth='o', bob=-1, ph=1)],                        # hand up, "excuse me"
            'yawn': [d(eyes='closed', mouth='o'), d(eyes='closed', mouth='yawn', arms='out', squash=-1), d(eyes='closed', mouth='flat', squash=1, bob=1)],
            'stretch': [d(eyes='closed', mouth='o', arms='up', squash=-1, bob=-1), d(eyes='happy', mouth='smile', arms='up')],
            'pout': [d(eyes='closed', mouth='pout', arms='hug', blush=True, squash=1, bob=1)],
            'party': [d(eyes='happy', mouth='open', arms='up', bob=-2, feet='tuck'), d(eyes='happy', mouth='open', arms='out', ph=1), d(eyes='happy', mouth='open', arms='up', bob=-1, feet='l')],
            'hum': [d(eyes='happy', mouth='smile'), d(eyes='happy', mouth='o', bob=1, ph=1)],
            'sneak': [d(feet='l', squash=1, bob=1, eyes='down', mouth='flat'), d(squash=1, bob=1, eyes='down', mouth='flat', ph=1), d(feet='r', squash=1, bob=1, eyes='down', mouth='flat'), d(squash=1, bob=1, eyes='down', mouth='flat', ph=1)],
            'squish': [d(squash=3, bob=2, eyes='closed', mouth='flat', arms='out')],
            'stalk': [d(squash=1, bob=1, eyes='wide', mouth='flat'), d(squash=2, bob=1, eyes='wide', mouth='flat', ph=1)],  # wiggling butt, stalking
            'spin': [d(eyes='happy', mouth='open', arms='out'), d(eyes='closed', mouth='smile', squash=1), d(eyes='happy', mouth='open', arms='out', flip=True), d(eyes='closed', mouth='smile', squash=1, flip=True)],
            'dive': [d(eyes='closed', mouth='flat', arms='up', feet='tuck', squash=-1)],
        }
    def save(self, out, eyes):
        os.makedirs(out, exist_ok=True); F = self.frames()
        for k, v in F.items(): png(f'{out}/{k}.png', v)
        json.dump({'name': self.name, 'names': {'ko': self.name, 'en': self.name_en}, 'frame': [W, H], 'height': 24, 'fps': self.fps, 'eyes': eyes}, open(f'{out}/chara.json', 'w'), ensure_ascii=False, indent=1)
        return [f for v in F.values() for f in v]

def turn(cv):                                                                     # 90 degrees clockwise (rolls forward)
    n = Cv(cv.w, cv.h)
    for y in range(cv.h):
        for x in range(cv.w): n.px[x][cv.w - 1 - y] = cv.px[y][x]
    return n

def rotate(cv, ang, px, py, tx, ty, floor=24):
    """화면 기준(y 아래) 시계 방향으로 ang 만큼 — 도착 칸마다 원래 칸을 거꾸로 찾아 가장 가까운 점(도트 그대로)"""
    n = Cv(cv.w, cv.h); c, s = math.cos(ang), math.sin(ang)
    for y in range(min(n.h, floor + 1)):
        for x in range(n.w):
            dx, dy = x + 0.5 - tx, y + 0.5 - ty
            sx, sy = c * dx + s * dy + px, -s * dx + c * dy + py
            ix, iy = math.floor(sx), math.floor(sy)
            if 0 <= ix < cv.w and 0 <= iy < cv.h and cv.px[iy][ix]: n.px[y][x] = cv.px[iy][ix]
    return n

def settle(cv, floor=24):
    pts = [(x, y) for y in range(cv.h) for x in range(cv.w) if cv.px[y][x]]
    if not pts: return cv
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts); y1 = max(p[1] for p in pts)
    dx = (cv.w - 1 - x1 - x0) // 2; dy = floor - y1
    n = Cv(cv.w, cv.h)
    for (x, y) in pts: n.set(x + dx, y + dy, cv.px[y][x])
    return n

def tex(cv, mask, cols, col, test):
    for (x, y) in mask:
        if cv.get(x, y) in cols and test(x, y): cv.set(x, y, col)

class Acorn(Chara):
    name = '도토리'; name_en = 'Acorn'
    C = dict(o=hexc('#2a1a12'), b=hexc('#e6ad6e'), l=hexc('#f7d6a6'), s=hexc('#c4844a'), belly=hexc('#f9e2bb'),
             cap=hexc('#8f5a33'), capl=hexc('#b07a48'), caps=hexc('#6b3f22'), x=hexc('#5c351b'), stem=hexc('#4a2f1c'))
    def __init__(s): s.line = s.C['o']; s.foot = hexc('#a8693a'); s.armc = s.C['b']
    def body(s, cv, y0, sq, ph, P):
        C = s.C; m = ellipse(12.5, 16.5 + y0 + sq / 2, 8.2 + sq / 2, 7.6 - sq / 2, 2.1)
        cv.blob(m, C['b'], C['o'], C['l'], C['s'])
        tex(cv, ellipse(11.5, 19.5 + y0, 3.6, 2.6), (C['b'], C['s']), C['belly'], lambda x, y: True)
        cy = 10.5 + y0 + sq
        cap = {p for p in ellipse(12.5, cy, 10.2, 5.6, 2.3) if p[1] <= int(cy) + 1}
        cv.blob(cap, C['cap'], C['o'], C['capl'], C['caps'])
        tex(cv, cap, (C['cap'], C['capl'], C['caps']), C['x'], lambda x, y: (x + y) % 3 == 0 and (x - y) % 3 != 0)
        cv.sprite(['..oo', '.oso', 'oso.', 'oo..'], 12, int(cy - 5.6) - 3, {'o': C['o'], 's': C['stem']})
        return (4, 21, int(cy) - 4, 24 + y0), (12, 14 + y0 + sq)

class Mandu(Chara):
    name = '만두'; name_en = 'Dumpling'; feet = False
    C = dict(o=hexc('#3a2a1e'), b=hexc('#f7efe0'), l=hexc('#ffffff'), s=hexc('#e0cdae'), p=hexc('#c9b08a'), steam=hexc('#ffffff'))
    def __init__(s): s.line = s.C['o']; s.armc = s.C['b']
    def body(s, cv, y0, sq, ph, P):
        C = s.C; cy = 25 + y0
        m = {p for p in ellipse(12.5, cy - 0.5, 10.5 + sq / 2, 13 - sq, 1.9) if p[1] <= 24}
        cv.blob(m, C['b'], C['o'], C['l'], C['s'])
        top = min(y for _, y in m)
        cv.blob(ellipse(12.5, top + 0.5, 2.2, 1.8), C['b'], C['o'], C['l'])      # top knot
        for k in (-3, -2, 2, 3):                                                   # pleats spreading from the top
            for j in range(1, 4): cv.set(12 + k * j // 2 + (1 if k > 0 else 0), top + 1 + j, C['p'])
        return (2, 23, top, 24), (11, top + 7 + sq // 2)
    def front(s, cv, box, ph, P):
        if ph == 1 and not P.get('sleep'):                                         # steam wafting up
            for (x, y) in ((17, box[2] - 2), (18, box[2] - 3), (17, box[2] - 4)): cv.set(x, y, hexc('#d8e4f0'))

class Sprout(Chara):
    name = '새싹 화분'; name_en = 'Sprout'
    C = dict(o=hexc('#3a1e14'), b=hexc('#d9774f'), l=hexc('#f0a07a'), s=hexc('#b05a38'), rim=hexc('#e58a60'),
             g=hexc('#79c25a'), G=hexc('#b8e690'), go=hexc('#24461d'))
    def __init__(s): s.line = s.C['o']; s.foot = hexc('#8a4a2e'); s.armc = s.C['b']
    def body(s, cv, y0, sq, ph, P):
        C = s.C; top = 10 + y0 + sq
        pot = set()
        for y in range(top + 3, 24):
            hw = 7.5 - (y - top - 3) * 0.25
            for x in range(int(12.5 - hw), int(12.5 + hw) + 1): pot.add((x, y))
        cv.blob(pot, C['b'], C['o'], C['l'], C['s'])
        rim = {(x, y) for y in range(top, top + 4) for x in range(3, 23)} - {(3, top), (22, top)}
        cv.blob(rim, C['rim'], C['o'], C['l'], C['s'])
        return (4, 21, top, 24), (11, top + 6)
    def back(s, cv, box, ph, P):
        C = s.C; top = box[2]; sw = ph if not P.get('sleep') else 0
        pal = {'o': C['go'], 'g': C['g'], 'G': C['G']}
        leafs = ['.oo.....oo.', 'oGgo...ogGo', 'oggoo.ooggo', '.ooo.o.ooo.', '.....o.....', '.....o.....']
        if P.get('sleep'): leafs = ['...........', '.oo.....oo.', 'oGgoo.ooGgo', '.oooo.oooo.', '.....o.....', '.....o.....']
        cv.sprite(leafs, 7 + sw, top - 6, pal)

class Cloud(Chara):
    name = '구름'; name_en = 'Cloud'; feet = False
    C = dict(o=hexc('#36456e'), b=hexc('#f3f7ff'), l=hexc('#ffffff'), s=hexc('#c9d6ef'))
    def __init__(s): s.line = s.C['o']; s.armc = s.C['b']; s.cheek = hexc('#f5a3b5')
    def body(s, cv, y0, sq, ph, P):
        C = s.C; b = 21 + y0
        m = ellipse(12.5, b - 2.5, 11, 4.2 - sq / 2, 2.4) | ellipse(8, b - 6.5 + sq, 5, 4.8) | ellipse(15.5, b - 8 + sq, 6.2, 6) | ellipse(20, b - 5 + sq, 3.6, 3.4)
        cv.blob(m, C['b'], C['o'], C['l'], C['s'])
        top = min(y for _, y in m)
        return (2, 23, top, b), (11, b - 8 + sq)
    def front(s, cv, box, ph, P):
        if P.get('sleep'):                                                         # a raindrop drips when asleep
            for (x, y) in ((7, box[3] + 2 + ph), (16, box[3] + 3 - ph)): cv.set(x, y, hexc('#7fb2ea'))

class Candle(Chara):
    name = '촛불'; name_en = 'Candle'
    C = dict(o=hexc('#3a2618'), b=hexc('#fbefd6'), l=hexc('#fffaf0'), s=hexc('#e6cba0'), drip=hexc('#fffdf6'),
             f=hexc('#ff8a2a'), F=hexc('#ffcf3f'), W=hexc('#fff6c8'), wick=hexc('#2a1a12'))
    def __init__(s): s.line = s.C['o']; s.foot = hexc('#b08a60'); s.armc = s.C['b']
    def body(s, cv, y0, sq, ph, P):
        C = s.C; top = 8 + y0 + sq * 2
        m = {(x, y) for y in range(top, 24) for x in range(6, 19)} - {(6, top), (18, top)}
        cv.blob(m, C['b'], C['o'], C['l'], C['s'])
        for x in range(7, 18): cv.set(x, top + 1, C['drip'])                        # melted top surface and dripped wax
        for (x, n) in ((8, 3), (12, 2), (16, 4)):
            for j in range(n): cv.set(x, top + 2 + j, C['drip'])
        return (6, 18, top, 24), (10, top + 6 + (1 if sq else 0))
    def front(s, cv, box, ph, P):
        C = s.C; top = box[2]
        cv.set(12, top - 1, C['wick']); cv.set(12, top - 2, C['wick'])
        if P.get('sleep'):
            cv.sprite(['.s.', '..s', '.s.'], 12, top - 6, {'s': hexc('#b8b8c8')}); return  # when asleep the flame goes out and there is smoke
        fl = [['..o..', '.ofo.', '.ofo.', 'ofFfo', 'oFWFo', '.oFo.'], ['...o.', '..ofo', '.ofo.', 'ofFfo', 'oFWFo', '.oFo.']][ph]
        cv.sprite(fl, 10, top - 8, {'o': C['f'], 'f': C['f'], 'F': C['F'], 'W': C['W']})

class Pebble(Chara):
    name = '이끼돌'; name_en = 'Pebble'
    C = dict(o=hexc('#232a33'), b=hexc('#aab4c0'), l=hexc('#d6dde5'), s=hexc('#86919e'), dot=hexc('#7a8592'),
             m=hexc('#7db352'), M=hexc('#b6dc84'), mo=hexc('#2b4a22'), fl=hexc('#ffffff'), fy=hexc('#ffcf3f'))
    def __init__(s): s.line = s.C['o']; s.foot = hexc('#6c7682'); s.armc = s.C['b']
    def body(s, cv, y0, sq, ph, P):
        C = s.C; cyy = 17 + y0 + sq / 2
        m = ellipse(12.5, cyy, 10.5 + sq / 2, 6.8 - sq / 2, 2.2)
        cv.blob(m, C['b'], C['o'], C['l'], C['s'])
        for (x, y) in ((5, 19), (7, 21), (19, 20), (17, 22), (8, 15)): 
            if (x, y + y0) in m and cv.get(x, y + y0) != C['o']: cv.set(x, y + y0, C['dot'])
        top = min(y for _, y in m)
        moss = {p for p in ellipse(11.5, top + 1, 7.5, 3.2) if p[1] <= top + 2}
        cv.blob(moss, C['m'], C['mo'], C['M'])
        for (x, y) in ((6, top + 3), (9, top + 3), (15, top + 3)): cv.set(x, y, C['m'])   # dripped moss
        fx, fy = 15, top - 2 - (1 if ph else 0)
        cv.sprite(['.w.', 'wyw', '.w.', '.g.'], fx, fy, {'w': C['fl'], 'y': C['fy'], 'g': C['mo']})
        return (2, 23, top, 24), (11, top + 6)

if __name__ == '__main__':
    # python3 -I chars.py <charas folder> [--sheet] — writes the six packs to <folder>/<id>/ (a folder with the same name is overwritten)
    out = sys.argv[1]; sheet = []
    for cls, key, eyes in ((Acorn, 'acorn', None), (Mandu, 'mandu', None), (Sprout, 'sprout', None), (Cloud, 'cloud', None), (Candle, 'candle', None), (Pebble, 'pebble', None)):
        c = cls(); _, (ex, ey) = c.body(Cv(W, H), 0, 0, 0, {})
        sheet.append(c.save(f'{out}/{key}', [[ex, ey, 2, 3], [ex + 4, ey, 2, 3]]))
    if '--sheet' not in sys.argv: sys.exit(0)
    n = max(len(r) for r in sheet); big = Cv(W * n, H * len(sheet))
    for j, row in enumerate(sheet):
        for i, f in enumerate(row):
            for y in range(H):
                for x in range(W): big.set(i * W + x, j * H + y, f.px[y][x])
    png(f'{out}/_all.png', [big])   # overall sample sheet
