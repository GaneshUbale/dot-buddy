#!/bin/bash
# Dot Buddy one-line installer:
#   curl -fsSL https://raw.githubusercontent.com/doldoldol21/dot-buddy/main/install.sh | bash
#
# Downloads the latest signed release, checks its Ed25519 signature, and puts "Dot Buddy.app" in ~/Applications.
# Files downloaded with curl carry no quarantine flag, so macOS opens the app without the "Open Anyway" detour.
# Running it again updates an existing install (the old app goes to the Trash). The app keeps itself updated afterwards
# if you allow it on first launch.
#
# Options (environment variables):
#   DOTBUDDY_DEST=/Applications   install somewhere else (default ~/Applications)
#   DOTBUDDY_CLI=1                also link `dotbuddy` and `dotbuddy-hook` into ~/.local/bin
#   DOTBUDDY_NO_OPEN=1            don't launch the app at the end
set -euo pipefail

REPO="doldoldol21/dot-buddy"
DEST="${DOTBUDDY_DEST:-$HOME/Applications}"
APP="$DEST/Dot Buddy.app"

say() { printf '%s\n' "$*"; }
die() { printf 'dot-buddy install: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = Darwin ] || die "Dot Buddy is a macOS app."
major="$(sw_vers -productVersion | cut -d. -f1)"
[ "$major" -ge 13 ] || die "macOS 13 or later is required (this Mac has $(sw_vers -productVersion))."
for t in curl ditto; do command -v "$t" >/dev/null || die "missing $t"; done

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

# The latest release tag, from github.com's redirect (no API rate limit)
tag="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest" | sed -n 's#.*/releases/tag/##p')"
[ -n "$tag" ] || die "couldn't find the latest release."
ver="${tag#v}"
base="https://github.com/$REPO/releases/download/$tag"

if [ -x "$APP/Contents/MacOS/DotBuddy" ] && [ "$("$APP/Contents/MacOS/DotBuddy" --version 2>/dev/null)" = "$ver" ]; then
  say "Dot Buddy $ver is already installed in $DEST."
else
  say "Downloading Dot Buddy ${ver}…"
  curl -fsSL "$base/Dot-Buddy-$ver.zip" -o "$tmp/app.zip" || die "download failed."
  curl -fsSL "$base/Dot-Buddy-$ver.zip.sig" -o "$tmp/app.zip.sig" || die "this release has no signature; refusing to install."
  ditto -x -k "$tmp/app.zip" "$tmp/x"
  new="$tmp/x/Dot Buddy.app"
  [ -d "$new" ] || die "the download has no Dot Buddy.app."

  # Check the signature with the installed app when there is one (already trusted), otherwise with the new one
  verifier="$new/Contents/MacOS/DotBuddy"
  if /usr/libexec/PlistBuddy -c 'Print :DotBuddyBuild' "$APP/Contents/Info.plist" >/dev/null 2>&1; then   # 0.1.1+ has the updater
    verifier="$APP/Contents/MacOS/DotBuddy"
  fi
  "$verifier" --verify-update "$tmp/app.zip" "$tmp/app.zip.sig" || die "the signature doesn't match; refusing to install."
  [ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$new/Contents/Info.plist")" = io.github.doldoldol21.dot-buddy ] || die "unexpected bundle id."
  codesign --verify --deep --strict "$new" 2>/dev/null || die "the app's code signature is broken."

  if [ "$DEST" = "$HOME/Applications" ] || [ "$DEST" = /Applications ]; then pkill -x DotBuddy 2>/dev/null || true; fi
  mkdir -p "$DEST"
  if [ -e "$APP" ]; then mv "$APP" "$HOME/.Trash/Dot Buddy $(date +%Y%m%d-%H%M%S).app"; fi
  mv "$new" "$APP"
  say "Installed Dot Buddy $ver in $DEST."
fi

if [ "${DOTBUDDY_CLI:-0}" = 1 ]; then "$APP/Contents/MacOS/DotBuddy" --install-cli; fi
if [ "${DOTBUDDY_NO_OPEN:-0}" != 1 ]; then open "$APP"; say "Right-click the pet for settings."; fi
