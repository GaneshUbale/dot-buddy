# A small pixel drawing board: layer parts and add outline and shading automatically
import zlib, struct, math
def hexc(h): h=h.lstrip('#'); return (int(h[0:2],16),int(h[2:4],16),int(h[4:6],16),255)
class Cv:
    def __init__(s,w,h): s.w,s.h=w,h; s.px=[[None]*w for _ in range(h)]
    def set(s,x,y,c):
        if 0<=x<s.w and 0<=y<s.h and c: s.px[y][x]=c
    def get(s,x,y): return s.px[y][x] if 0<=x<s.w and 0<=y<s.h else None
    def blob(s, mask, fill, line, light=None, shade=None, lightdir=(-1,-1), clip=None):
        # mask: set of (x,y). edge = line, inner upper-left = light, lower-right = shade
        for (x,y) in mask:
            if clip and not clip(x,y): continue
            edge = any((x+dx,y+dy) not in mask for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))
            if edge: c=line
            elif light and (x+lightdir[0]*2,y+lightdir[1]*2) not in mask: c=light
            elif shade and ((x-lightdir[0]*2,y-lightdir[1]*2) not in mask or (x-lightdir[0],y-lightdir[1]*3) not in mask): c=shade
            else: c=fill
            s.set(x,y,c)
    def sprite(s, rows, x0, y0, pal, flip=False):
        for j,r in enumerate(rows):
            for i,ch in enumerate(r):
                c=pal.get(ch)
                if c: s.set(x0+(len(r)-1-i if flip else i), y0+j, c)
def ellipse(cx,cy,rx,ry,p=2.0):
    m=set()
    for y in range(int(cy-ry-1),int(cy+ry+2)):
        for x in range(int(cx-rx-1),int(cx+rx+2)):
            if abs((x+0.5-cx)/rx)**p+abs((y+0.5-cy)/ry)**p<=1: m.add((x,y))
    return m
def png(path, frames):
    W=frames[0].w; H=frames[0].h; raw=b''
    for y in range(H):
        raw+=b'\x00'
        for f in frames:
            for x in range(W):
                c=f.px[y][x]; raw+=bytes(c) if c else b'\0\0\0\0'
    def ch(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W*len(frames),H,8,6,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b''))
