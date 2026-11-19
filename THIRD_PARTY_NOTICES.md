# Third-party notices

Dot Buddy's own code is under the [MIT License](LICENSE). This file lists third-party material that the build pulls in, and projects that influenced the design.

## Fonts (bundled into the app at build time)

The fonts are **not** stored in this repository. `build.sh` downloads them, verifies a pinned checksum, and copies each font into `Dot Buddy.app/Contents/Resources/` together with its license text. Neither font is modified.

| Font | Version | Source | License | License file in the app |
|---|---|---|---|---|
| Galmuri 7, 9, 11 | 2.40.3 (npm package `galmuri`) | <https://github.com/quiple/galmuri> | SIL Open Font License 1.1 | `Galmuri-LICENSE.txt` |
| Neo둥근모 (NeoDunggeunmo) | 1.601 | <https://github.com/neodgm/neodgm> | SIL Open Font License 1.1, with Reserved Font Names | `neodgm-LICENSE.txt` |

The copyright notices are in the license files listed above. The full license text is at <https://openfontlicense.org>.

Under the OFL the fonts may be bundled and redistributed with software, but they may not be sold on their own, and a modified version may not use the Reserved Font Names. If you change a font, rename it.

## Design acknowledgements (no code copied)

### OpenPets

<https://github.com/alterhq/openpets>, MIT License.

A few behaviors were inspired by OpenPets:

- mouse clicks pass through the pet's transparent pixels;
- the animation runs fast ticks only while the pet is moving;
- throw velocity comes from the last ~0.1 s of drag samples.

Dot Buddy reimplements these ideas. No OpenPets source code is included.

### Codex pet format

Dot Buddy reads pets in the Codex app's format (`pet.json` plus an 8×9 spritesheet) for compatibility, and can export its own characters to that format. The row layout follows community documentation of the format. No Codex assets are included.

Dot Buddy is an independent project and is not affiliated with, endorsed by, or sponsored by OpenAI or Anthropic. "Codex", "Claude" and "Claude Code" are trademarks of their respective owners.
