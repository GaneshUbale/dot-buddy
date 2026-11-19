# Contributing to Dot Buddy

Thanks for helping. Bug reports, new agent integrations, terminal support and characters you drew yourself are all welcome.

## Build and run

You need macOS 13+ and the Xcode Command Line Tools (`xcode-select --install`). `python3` is optional; it draws the high-res built-in characters.

```bash
./build.sh                          # build bin/DotBuddy and install ~/Applications/Dot Buddy.app
APP=/tmp/Dot.app FORCE=1 ./build.sh # build a throwaway copy elsewhere, forcing a rebuild
./build.sh --universal              # arm64 + x86_64
```

The build skips compiling when no file in `Sources/` changed, and never relaunches a running app. Quit the pet (right-click → Quit) and open the app again to see your change.

`bin/DotBuddy` is the same binary as the app's. Its CLI is handy while developing:

```bash
bin/DotBuddy --state                     # current session verdict as JSON
bin/DotBuddy --preview /tmp/poses.png    # every character × a set of poses
bin/DotBuddy --charas                    # characters that loaded, with frame counts
bin/DotBuddy --lines idle on=window high=300   # 200 sample idle lines for a situation
DOTBUDDY_LANG=en bin/DotBuddy --lines done high=3000
```

## Self-test

```bash
python3 selftest.py
```

It builds fake session files in a temp folder and checks the session verdicts, `--report`, `--run`, click targets, `tools.json`, speech lines, character packs and Codex pets. It doesn't launch the app. It needs a built `bin/DotBuddy`. CI runs the same build and test on every push and pull request.

Please add a check to `selftest.py` when you fix a bug or add behavior that can be tested from the CLI.

## Code layout

Everything is plain Swift and AppKit compiled with `swiftc`. There is no Xcode project and no package manager.

| File | What it holds |
|---|---|
| `Sources/Main.swift` | Entry point and the CLI (`--report`, `--signal`, `--run`, `--state`, previews and exports). The header comment documents the CLI |
| `Sources/Pet.swift` | The pet window and the pet itself: movement, physics, reactions, notices, the right-click menu |
| `Sources/Scene.swift` | Finding floors: screen bottom, widgets, window top edges, the Dock |
| `Sources/Sessions.swift` | Session sources (Claude Code session files, the `--report` folder), `tools.json`, the file watcher |
| `Sources/Terminal.swift` | Click-to-jump: finding the terminal app and tab for a session |
| `Sources/Chatter.swift` | Following a working session's transcript, and everything the pet says |
| `Sources/Bubble.swift` | Drawing speech bubbles with the pixel fonts; saved settings |
| `Sources/Draw.swift` | Pixel drawing: poses, props, character effects |
| `Sources/Charas.swift` | Built-in characters, the character pack loader, Codex pet import and export |
| `Sources/Lang.swift` | Language selection and the `T()` helpers |
| `charas/chars.py`, `charas/pix.py` | Generator for the six built-in high-res character packs |
| `build.sh` | Build, font download, app bundle, ad-hoc signing |
| `selftest.py` | The self-test |

Adding an agent usually needs no Swift at all: its hooks call `--report` and `--signal` (see [docs/agents.md](docs/agents.md)). A built-in source is a class conforming to `SessionSource` in `Sessions.swift`, added to `makeSources()`. A new terminal for click-to-jump is one entry in `TAB_PICKERS` in `Terminal.swift`.

## Every user-facing string comes in two languages

Menus, bubbles, speech lines and CLI messages are shown in Korean or English. There are no string files; write both languages side by side with `T()`, Korean first:

```swift
say(T("다 했어!", "All done!"), now)
let lines = T(["안녕", "반가워"], ["hi", "hey there"])   // the two lists can differ in length
```

- Check both with `DOTBUDDY_LANG=ko` and `DOTBUDDY_LANG=en`.
- If you don't write Korean, put your English in both slots and say so in the pull request. Someone will translate it.
- Keep lines short; bubbles are small. The pet never repeats file paths, commands or question text.

## Characters and copyright

Do not submit characters you don't own the rights to: no characters from games, anime, films, brands or other people's art. Keep those in your own character folder (`~/Library/Application Support/DotBuddy/charas/`); the app only reads that folder and never sends it anywhere.

Original characters are welcome. The built-in ones are drawn in code by `charas/chars.py`, so a new built-in character is a new class there. See [CHARACTERS.md](CHARACTERS.md).

## Pull requests

- Keep each pull request to one change, and describe what a user will notice.
- Run `python3 selftest.py` before you push.
- Changes to what the app reads or runs (session files, transcripts, `tools.json` commands) need a note on the privacy or security impact.
- By contributing you agree that your work is released under the [MIT License](LICENSE).
