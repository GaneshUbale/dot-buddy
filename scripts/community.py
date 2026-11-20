#!/usr/bin/env python3
"""Community character packs (community/<id>/): check them, and build the list the app reads.

  python3 scripts/community.py check [--app bin/DotBuddy]   check every pack (CI runs this on pull requests)
  python3 scripts/community.py build  --app bin/DotBuddy    check, draw community/<id>/preview.gif with the app,
                                                            write community/index.json and the gallery in community/README.md

Contributors only add community/<id>/ (chara.json + PNGs). preview.gif, index.json and the gallery are made by CI after
the merge, so a pull request never needs to touch them. Standard library only.
"""
import hashlib, json, os, re, struct, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
COMMUNITY = os.path.join(HERE, "community")
INDEX = os.path.join(COMMUNITY, "index.json")
README = os.path.join(COMMUNITY, "README.md")

ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")
RESERVED = {"acorn", "mandu", "sprout", "cloud", "candle", "pebble", "index", "readme"}   # the built-in characters keep their names
LICENSES = {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT"}
KEYS = {"name", "names", "frame", "height", "fps", "eyes", "author", "license", "description"}
MAX_FILE, MAX_PACK, MAX_FRAMES = 64 << 10, 512 << 10, 16
MAX_W, MAX_H = 30, 32
GENERATED = {"preview.gif"}
START, END = "<!-- gallery:start -->", "<!-- gallery:end -->"


def motions():
    """Motion names, read from the app's source so the two never drift apart"""
    src = open(os.path.join(HERE, "Sources", "Charas.swift"), encoding="utf-8").read()
    block = src[src.index("let MOTIONS"):src.index("let MOTION_FALLBACK")]
    return re.findall(r'\("([a-z]+)", T\(', block)


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(33)
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def check_pack(d, names):
    """Problems with one pack folder (empty list = fine)"""
    pid, errs = os.path.basename(d), []
    if not ID.match(pid):
        errs.append("folder name must be 2-32 characters of a-z, 0-9 and '-', starting with a letter or digit")
    if pid in RESERVED:
        errs.append(f"'{pid}' is taken by a built-in character; pick another name")
    files = sorted(os.listdir(d))
    hidden = [f for f in files if f.startswith(".")]
    files = [f for f in files if not f.startswith(".")]
    if hidden:
        errs.append("remove hidden files: " + ", ".join(hidden))
    for f in files:
        p = os.path.join(d, f)
        if os.path.islink(p) or not os.path.isfile(p):
            errs.append(f"{f}: only plain files (no folders or links)")
        elif f in GENERATED:
            pass
        elif f != "chara.json" and not (f.endswith(".png") and f[:-4] in names):
            errs.append(f"{f}: not a motion name (see CHARACTERS.md) — allowed: chara.json and <motion>.png")
        elif os.path.getsize(p) > MAX_FILE:
            errs.append(f"{f}: {os.path.getsize(p)} bytes, the limit is {MAX_FILE}")
    total = sum(os.path.getsize(os.path.join(d, f)) for f in files if f not in GENERATED and os.path.isfile(os.path.join(d, f)))
    if total > MAX_PACK:
        errs.append(f"the pack is {total} bytes, the limit is {MAX_PACK}")
    if "idle.png" not in files:
        errs.append("idle.png is required")
    meta = {}
    if "chara.json" not in files:
        errs.append("chara.json is required (name, author, license)")
    else:
        try:
            meta = json.load(open(os.path.join(d, "chara.json"), encoding="utf-8"))
            if not isinstance(meta, dict):
                raise ValueError("not an object")
        except Exception as e:
            errs.append(f"chara.json: {e}")
            meta = {}
    if meta:
        extra = set(meta) - KEYS
        if extra:
            errs.append("chara.json: unknown keys " + ", ".join(sorted(extra)))
        for k, lim in (("name", 40), ("author", 39), ("description", 140)):
            v = meta.get(k, "")
            if k != "description" and not (isinstance(v, str) and v.strip()):
                errs.append(f"chara.json: '{k}' is required")
            elif not isinstance(v, str) or len(v) > lim:
                errs.append(f"chara.json: '{k}' must be text of at most {lim} characters")
        if meta.get("license") not in LICENSES:
            errs.append("chara.json: 'license' must be one of " + ", ".join(sorted(LICENSES)))
        if "names" in meta and not (isinstance(meta["names"], dict) and all(isinstance(v, str) and len(v) <= 40 for v in meta["names"].values())):
            errs.append("chara.json: 'names' must map languages to names, e.g. {\"en\": \"Teacup\", \"ko\": \"찻잔\"}")
    # frame sizes: every motion PNG is a strip of frames the size of one idle frame
    idle = png_size(os.path.join(d, "idle.png")) if "idle.png" in files else None
    if "idle.png" in files and not idle:
        errs.append("idle.png is not a PNG")
    fw, fh = (meta.get("frame") or [None, None]) if isinstance(meta.get("frame"), list) and len(meta.get("frame")) == 2 else (None, None)
    if idle:
        fw, fh = fw or idle[0], fh or idle[1]
        if not (isinstance(fw, int) and isinstance(fh, int) and 0 < fw <= MAX_W and 0 < fh <= MAX_H):
            errs.append(f"frame size {fw}x{fh}: at most {MAX_W}x{MAX_H} dots")
        else:
            for f in files:
                if not f.endswith(".png") or f[:-4] not in names:
                    continue
                s = png_size(os.path.join(d, f))
                if not s:
                    errs.append(f"{f}: not a PNG")
                elif s[1] != fh or s[0] % fw or not 1 <= s[0] // fw <= MAX_FRAMES:
                    errs.append(f"{f}: {s[0]}x{s[1]}, but frames are {fw}x{fh} side by side (1-{MAX_FRAMES} frames)")
    return errs


def packs():
    if not os.path.isdir(COMMUNITY):
        return []
    return sorted(os.path.join(COMMUNITY, n) for n in os.listdir(COMMUNITY) if os.path.isdir(os.path.join(COMMUNITY, n)) and not n.startswith("."))


def entry(d):
    meta = json.load(open(os.path.join(d, "chara.json"), encoding="utf-8"))
    files = []
    for f in sorted(os.listdir(d)):
        if f.startswith(".") or f in GENERATED:
            continue
        b = open(os.path.join(d, f), "rb").read()
        files.append({"name": f, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)})
    e = {"id": os.path.basename(d), "name": meta["name"].strip(), "author": meta["author"].strip(), "license": meta["license"],
         "description": meta.get("description", "").strip(), "files": files}
    if meta.get("names"):
        e["names"] = meta["names"]
    if os.path.exists(os.path.join(d, "preview.gif")):
        e["preview"] = "preview.gif"
    return e


def digest(e):
    return hashlib.sha256("\n".join(f"{f['name']}:{f['sha256']}" for f in e["files"]).encode()).hexdigest()


def app_load(app):
    """Ids the app itself loads from community/ (the real loader, with its own limits)"""
    r = subprocess.run([app, "--charas"], capture_output=True, text=True, timeout=60, env=dict(os.environ, DOTBUDDY_CHARAS=COMMUNITY))
    return {c["id"]: c for c in json.loads(r.stdout or '{"charas": []}')["charas"]}


def check(app=None):
    names, bad = set(motions()), 0
    loaded = app_load(app) if app else {}
    for d in packs():
        errs = check_pack(d, names)
        pid = os.path.basename(d)
        if app and not errs:
            c = loaded.get("pack:" + pid)
            if not c:
                errs.append("the app could not load this pack")
            elif "idle" not in c["motions"] and not c["size"][0]:
                errs.append("the app loaded no picture")
        print(("ok    " if not errs else "FAIL  ") + pid)
        for e in errs:
            print("      - " + e)
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::error file=community/{pid}::{e}")
        bad += bool(errs)
    if bad:
        print(f"\n{bad} pack(s) need fixing. The rules are in community/README.md.")
    return bad == 0


def gallery(entries):
    if not entries:
        return "No characters yet. Be the first!"
    rows = ["| | Character | By | License |", "|---|---|---|---|"]
    for e in entries:
        img = f'<img src="{e["id"]}/preview.gif" width="220" alt="{e["name"]}">' if e.get("preview") else ""
        desc = f'<br>{e["description"]}' if e["description"] else ""
        rows.append(f'| {img} | **{e["name"]}**{desc} | [@{e["author"]}](https://github.com/{e["author"]}) | {e["license"]} |')
    return "\n".join(rows)


def build(app):
    if not check(app):
        return False
    old = {}
    if os.path.exists(INDEX):
        old = {e["id"]: e for e in json.load(open(INDEX, encoding="utf-8")).get("packs", [])}
    out = []
    for d in packs():
        pid, e = os.path.basename(d), entry(d)
        gif = os.path.join(d, "preview.gif")
        if not os.path.exists(gif) or pid not in old or digest(old[pid]) != digest(e):    # draw the preview again only when the pack changed
            r = subprocess.run([app, "--demo-gif", gif, "chara:pack:" + pid], capture_output=True, timeout=120, env=dict(os.environ, DOTBUDDY_CHARAS=COMMUNITY))
            if r.returncode:                                                              # (with DOTBUDDY_CHARAS set the built-in packs aren't loaded, so ids can't clash)
                print(f"preview for {pid} failed: {r.stderr.decode()[:200]}")
                return False
            e = entry(d)
        out.append(e)
    json.dump({"version": 1, "packs": out}, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(INDEX, "a").write("\n")
    if os.path.exists(README):
        s = open(README, encoding="utf-8").read()
        if START in s and END in s:
            s = s[:s.index(START) + len(START)] + "\n" + gallery(out) + "\n" + s[s.index(END):]
            open(README, "w", encoding="utf-8").write(s)
    print(f"index: {len(out)} pack(s)")
    return True


if __name__ == "__main__":
    a = sys.argv[1:]
    app = a[a.index("--app") + 1] if "--app" in a and a.index("--app") + 1 < len(a) else None
    if a[:1] == ["check"]:
        sys.exit(0 if check(app) else 1)
    if a[:1] == ["build"] and app:
        sys.exit(0 if build(app) else 1)
    print(__doc__)
    sys.exit(2)
