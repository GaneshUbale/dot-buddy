# Other agents

Dot Buddy follows Claude Code on its own by reading Claude Code's session files. Any other agent can join by calling the CLI that ships inside the app from its hooks. No code changes are needed.

This page has copy-paste setups for Codex CLI, Gemini CLI, Cursor, opencode and Aider, plus a wrapper for anything else.

> **Status.** Every setup below was written against the agent's official documentation or source (links in [Sources](#sources), checked 2026-11). None of them has been run end-to-end by the maintainers yet, so each is marked **untested**. Hook formats change between versions. If one breaks or you got it working, please open an issue or pull request.

## The two commands

The binary lives inside the app:

```bash
DOTBUDDY="$HOME/Applications/Dot Buddy.app/Contents/MacOS/DotBuddy"
```

**Session state.** Call this when the agent's state changes:

```bash
"$DOTBUDDY" --report <tool> <id> busy|idle|ask|end [--name NAME] [--label LABEL] [--pid PID]
```

| Argument | Meaning |
|---|---|
| `<tool>` | Short agent name such as `codex`. It's also the key for that agent in `tools.json` |
| `<id>` | Any stable session id from the agent. One file per `<tool>`+`<id>` |
| `busy` | Working (laptop out) |
| `idle` | Finished its turn and waiting for you (the "done" bubble) |
| `ask` | Waiting for an answer or an approval (the `?` bubble) |
| `end` | Session closed; remove it |
| `--name` | Title shown in the bubble (defaults to the id) |
| `--label` | What the pet calls this agent (defaults to `<tool>`; `tools.json` can set it too) |
| `--pid` | The agent's process. The session disappears when that process exits, and clicking the bubble jumps to its terminal tab. Without it, a session is dropped 30 minutes after its last `idle`, or 2 hours after its last `busy` |

**Gestures.** Call this from tool hooks so the pet reacts the way it does for Claude Code:

```bash
"$DOTBUDDY" --signal event <name> [--from <tool>]
```

`<name>` is one of `read`, `edit`, `test`, `commit`, `shell`, `web`, `skill`, `error`, `bg-start`, `bg-done`, `agent-start[:name]`, `agent-done`.

Both commands return immediately, print nothing on success, and exit with 2 on a bad argument. `--signal` does nothing if the app isn't running.

Check what the pet currently sees with `"$DOTBUDDY" --state`.

## Helper script for JSON hooks

Codex, Gemini CLI and Cursor pass hook data as JSON. This helper pulls the session id out of it with the built-in `plutil`, calls Dot Buddy, prints an optional reply for agents that expect JSON on stdout, and always exits 0 so it can't block the agent.

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/dotbuddy-hook <<'EOF'
#!/bin/sh
# dotbuddy-hook TOOL ID_KEY ACTION [REPLY]
#   TOOL    short agent name, e.g. codex, gemini, cursor (also the key in tools.json)
#   ID_KEY  JSON key on stdin that holds the session id, e.g. session_id
#   ACTION  busy | idle | ask | end, or event:NAME (read, edit, shell, ...)
#   REPLY   text to print on stdout afterwards, for agents that expect JSON
# Reads the hook's JSON from stdin. Always exits 0 and prints nothing else,
# so it can never block or confuse the agent.
HOME=${HOME:-$(echo ~)}
DOTBUDDY="${DOTBUDDY:-$HOME/Applications/Dot Buddy.app/Contents/MacOS/DotBuddy}"
tool=$1 key=$2 action=$3 reply=${4-}
input=$(cat)
field() { printf '%s' "$input" | /usr/bin/plutil -extract "$1" raw -o - - 2>/dev/null; }
case $action in
  event:*)
    "$DOTBUDDY" --signal event "${action#event:}" --from "$tool" >/dev/null 2>&1 ;;
  *)
    id=$(field "$key")
    dir=$(field cwd || field workspace_roots.0)
    [ -n "$id" ] && "$DOTBUDDY" --report "$tool" "$id" "$action" \
      ${dir:+--name "$tool · ${dir##*/}"} ${DOTBUDDY_PID:+--pid "$DOTBUDDY_PID"} >/dev/null 2>&1 ;;
esac
[ -n "$reply" ] && printf '%s\n' "$reply"
exit 0
EOF
chmod +x ~/.local/bin/dotbuddy-hook
```

Set `DOTBUDDY=/path/to/DotBuddy` if you installed the app somewhere else. The bubble title becomes `<tool> · <folder>`.

## Codex CLI

**Untested.** Two options: `notify` is one line but only knows "turn finished"; hooks cover the full cycle. Use one, not both.

### Option A: `notify` (done only)

Codex runs the `notify` program after each turn with one JSON argument (`type` is `agent-turn-complete`, plus `thread-id`, `cwd` and more). In `~/.codex/config.toml`:

```toml
notify = ["/bin/sh", "-c", 'printf "%s" "$1" | DOTBUDDY_PID=$PPID ~/.local/bin/dotbuddy-hook codex thread-id idle', "dotbuddy"]
```

`DOTBUDDY_PID=$PPID` ties the session to the Codex process, so it disappears when Codex exits and clicking the bubble finds the terminal tab. If the session vanishes right after the bubble appears, Codex launched the command through another process; drop `DOTBUDDY_PID=$PPID`.

The pet won't show Codex as busy with this option, only done.

### Option B: hooks (busy, question, done, end)

Codex loads lifecycle hooks from `~/.codex/hooks.json`. Every command hook gets JSON on stdin with `session_id` and `cwd`. Create or merge:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "~/.local/bin/dotbuddy-hook codex session_id busy" }] }
    ],
    "PermissionRequest": [
      { "hooks": [{ "type": "command", "command": "~/.local/bin/dotbuddy-hook codex session_id ask" }] }
    ],
    "PostToolUse": [
      { "hooks": [{ "type": "command", "command": "~/.local/bin/dotbuddy-hook codex session_id busy" }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "~/.local/bin/dotbuddy-hook codex session_id idle '{}'" }] }
    ],
    "Interrupt": [
      { "hooks": [{ "type": "command", "command": "~/.local/bin/dotbuddy-hook codex session_id idle" }] }
    ],
    "SessionEnd": [
      { "hooks": [{ "type": "command", "command": "~/.local/bin/dotbuddy-hook codex session_id end" }] }
    ],
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "~/.local/bin/dotbuddy-hook codex session_id event:shell" }] },
      { "matcher": "apply_patch", "hooks": [{ "type": "command", "command": "~/.local/bin/dotbuddy-hook codex session_id event:edit" }] }
    ]
  }
}
```

Then run `/hooks` inside Codex and trust the new hooks; Codex skips hooks it hasn't been told to trust. The `Stop` hook replies `{}` because Codex expects JSON (or nothing) from it. `PostToolUse` puts the session back to busy after you approve a request. `PreToolUse` is only for gestures; drop it if you don't want them.

| Codex hook | Dot Buddy |
|---|---|
| `UserPromptSubmit`, `PostToolUse` | `--report codex <session_id> busy` |
| `PermissionRequest` | `--report … ask` |
| `Stop`, `Interrupt` | `--report … idle` |
| `SessionEnd` | `--report … end` |
| `PreToolUse` `Bash` / `apply_patch` | `--signal event shell` / `edit` |

## Gemini CLI

**Untested.** Gemini CLI reads hooks from `~/.gemini/settings.json` (user) or `.gemini/settings.json` (project). Each hook gets JSON on stdin with `session_id` and `cwd`, and must print only JSON on stdout, so every command below replies `{}`. Merge this into your settings:

```json
{
  "hooks": {
    "BeforeAgent": [
      { "hooks": [{ "name": "dot-buddy-busy", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id busy '{}'" }] }
    ],
    "AfterTool": [
      { "hooks": [{ "name": "dot-buddy-resume", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id busy '{}'" }] }
    ],
    "Notification": [
      { "hooks": [{ "name": "dot-buddy-ask", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id ask '{}'" }] }
    ],
    "AfterAgent": [
      { "hooks": [{ "name": "dot-buddy-done", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id idle '{}'" }] }
    ],
    "SessionEnd": [
      { "hooks": [{ "name": "dot-buddy-end", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id end '{}'" }] }
    ],
    "BeforeTool": [
      { "matcher": "run_shell_command", "hooks": [{ "name": "dot-buddy-shell", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id event:shell '{}'" }] },
      { "matcher": "write_file|replace", "hooks": [{ "name": "dot-buddy-edit", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id event:edit '{}'" }] },
      { "matcher": "read_file|read_many_files|glob|grep_search", "hooks": [{ "name": "dot-buddy-read", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id event:read '{}'" }] },
      { "matcher": "google_web_search|web_fetch", "hooks": [{ "name": "dot-buddy-web", "type": "command", "command": "~/.local/bin/dotbuddy-hook gemini session_id event:web '{}'" }] }
    ]
  }
}
```

Gemini CLI runs hooks with a reduced environment. If they don't fire, replace `~` with your full home path. `/hooks` inside Gemini CLI lists and toggles them.

| Gemini CLI hook | Dot Buddy |
|---|---|
| `BeforeAgent`, `AfterTool` | `--report gemini <session_id> busy` |
| `Notification` (tool permission prompts) | `--report … ask` |
| `AfterAgent` | `--report … idle` |
| `SessionEnd` | `--report … end` |
| `BeforeTool` by tool name | `--signal event shell` / `edit` / `read` / `web` |

## Cursor

**Untested.** Cursor reads user hooks from `~/.cursor/hooks.json`. Each hook gets JSON on stdin with `conversation_id`. Cursor has no hook for "waiting for approval" that can't block, so there is no `ask` here.

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": "~/.local/bin/dotbuddy-hook cursor conversation_id busy '{\"continue\": true}'" }
    ],
    "stop": [
      { "command": "~/.local/bin/dotbuddy-hook cursor conversation_id idle '{}'" }
    ],
    "sessionEnd": [
      { "command": "~/.local/bin/dotbuddy-hook cursor conversation_id end '{}'" }
    ],
    "afterFileEdit": [
      { "command": "~/.local/bin/dotbuddy-hook cursor conversation_id event:edit '{}'" }
    ],
    "afterShellExecution": [
      { "command": "~/.local/bin/dotbuddy-hook cursor conversation_id event:shell '{}'" }
    ]
  }
}
```

`beforeSubmitPrompt` replies `{"continue": true}` so the prompt always goes through. Avoid Cursor's `before…` permission hooks (`beforeShellExecution`, `preToolUse` and others) for this: Cursor blocks the action when their output isn't the JSON it expects.

Cursor isn't a terminal, so clicking a Cursor bubble can't find a tab. Make it bring Cursor to the front in `~/Library/Application Support/DotBuddy/tools.json`:

```json
{ "cursor": { "label": "Cursor", "open": ["open", "-a", "Cursor"] } }
```

| Cursor hook | Dot Buddy |
|---|---|
| `beforeSubmitPrompt` | `--report cursor <conversation_id> busy` |
| `stop` | `--report … idle` |
| `sessionEnd` | `--report … end` |
| `afterFileEdit` / `afterShellExecution` | `--signal event edit` / `shell` |

## opencode

**Untested.** For opencode V2. A plugin subscribes to the server's event stream and calls Dot Buddy. Save as `~/.config/opencode/plugins/dot-buddy.ts`:

```ts
import { Plugin } from "@opencode/plugin"
import { execFile } from "node:child_process"
import { homedir } from "node:os"

const BIN = `${homedir()}/Applications/Dot Buddy.app/Contents/MacOS/DotBuddy`
const call = (...args: string[]) => execFile(BIN, args, () => {}) // ignore errors
const report = (sessionID: string, status: string) => call("--report", "opencode", sessionID, status)

const GESTURES: Record<string, string> = {
  shell: "shell", edit: "edit", write: "edit", patch: "edit",
  read: "read", grep: "read", glob: "read", webfetch: "web", websearch: "web",
}

export default Plugin.define({
  id: "dot-buddy",
  async setup(ctx) {
    await ctx.tool.hook("execute.before", (event) => {
      const g = GESTURES[event.tool]
      if (g) call("--signal", "event", g, "--from", "opencode")
    })

    const controller = new AbortController()
    void (async () => {
      for await (const event of ctx.event.subscribe({
        types: ["session.status", "permission.asked", "permission.replied", "session.deleted"],
        signal: controller.signal,
      })) {
        if (event.type === "session.status") report(event.data.sessionID, event.data.status.type === "idle" ? "idle" : "busy")
        else if (event.type === "permission.asked") report(event.data.sessionID, "ask")
        else if (event.type === "permission.replied") report(event.data.sessionID, "busy")
        else if (event.type === "session.deleted") report(event.data.sessionID, "end")
      }
    })()
    return () => controller.abort()
  },
})
```

| opencode event | Dot Buddy |
|---|---|
| `session.status` with status `busy` or `retry` | `--report opencode <sessionID> busy` |
| `session.status` with status `idle` | `--report … idle` |
| `permission.asked` / `permission.replied` | `--report … ask` / `busy` |
| `session.deleted` | `--report … end` |
| tool hook `execute.before` | `--signal event shell` / `edit` / `read` / `web` |

Subagent sessions report their own status, so they may show up as extra sessions. Sessions aren't deleted when you quit opencode; they drop off 30 minutes after going idle. opencode V1 plugins use a different API (an `event` hook with `session.idle`); this file won't load there.

## Aider

**Untested.** Aider has no lifecycle hooks, but it can run a command when it finishes a reply and waits for input. `--notifications-command` runs only together with `--notifications`, through a shell, so `$PPID` there is the Aider process:

```bash
aider --notifications --notifications-command \
  '"$HOME/Applications/Dot Buddy.app/Contents/MacOS/DotBuddy" --report aider "$PPID" idle --pid "$PPID" --name "aider · ${PWD##*/}"'
```

Each reply shows a done bubble, clicking it jumps to Aider's terminal tab, and the session disappears when Aider exits. Aider never reports busy this way. For one-shot runs (`aider --message …`) use the `--run` wrapper below instead.

## Anything else: `--run`

Wrap any command line tool. Dot Buddy shows it as busy while it runs and done when it exits. Input, output and the exit code pass through unchanged, and a non-zero exit also triggers the error gesture.

```bash
"$DOTBUDDY" --run [--tool NAME] [--name NAME] [--label LABEL] -- <command …>

# examples
"$DOTBUDDY" --run -- make test
"$DOTBUDDY" --run --tool aider --name "fix flaky test" -- aider --message "fix the flaky test" --yes
```

While running, the session is tied to the wrapper's process. When the command exits, the done state is tied to the shell you started it from, so it goes away when you close that shell, and clicking it jumps to that tab. The default tool name is the command's name and the default title is `<command> · <current folder>`.

An alias makes it automatic:

```bash
alias mytool='"$HOME/Applications/Dot Buddy.app/Contents/MacOS/DotBuddy" --run -- mytool'
```

This fits batch jobs and one-shot agent runs. For an interactive agent it shows busy for the whole session, so prefer the agent's hooks when it has them.

## Making it look right

Give each agent its own name, bubble colors and lines in `~/Library/Application Support/DotBuddy/tools.json`, keyed by the `<tool>` you used above:

```json
{
  "codex":  { "label": "Codex", "fill": "#eef4ff", "showLabel": true },
  "gemini": { "label": "Gemini", "done": ["Gemini is done!"] }
}
```

All keys are listed in the README under [Configuration](../README.md#configuration).

## Sources

Checked 2026-11-19.

| Agent | What was checked | Source |
|---|---|---|
| Codex CLI | `notify` program, JSON argument, `agent-turn-complete`, `thread-id` | <https://learn.chatgpt.com/docs/config-file/config-advanced> (redirected from developers.openai.com/codex/config-advanced) |
| Codex CLI | `hooks.json` location, event names, stdin fields (`session_id`, `cwd`), `PermissionRequest`, `Stop` output rule, `/hooks` trust review | <https://learn.chatgpt.com/docs/hooks> |
| Gemini CLI | `settings.json` hook shape, event names, stdin `session_id`, JSON-only stdout | <https://geminicli.com/docs/hooks/>, <https://geminicli.com/docs/hooks/reference> |
| Gemini CLI | Built-in tool names for matchers | <https://geminicli.com/docs/reference/tools> |
| Cursor | `~/.cursor/hooks.json` shape, event names, `conversation_id`, `beforeSubmitPrompt` output, permission-hook blocking | <https://cursor.com/docs/hooks> |
| opencode | V2 plugin loading, `Plugin.define`, `ctx.event.subscribe`, `ctx.tool.hook` | <https://opencode.ai/docs/plugins/>, <https://opencode.ai/docs/build/plugins/server>, <https://opencode.ai/docs/build/plugins/migrate-v1> |
| opencode | Event payloads (`session.status`, `permission.asked`/`replied`, `session.deleted` carry `sessionID`), tool names | `packages/schema/src/session-status-event.ts`, `permission.ts`, `session-event.ts` in <https://github.com/anomalyco/opencode>; <https://opencode.ai/docs/tools> |
| Aider | `--notifications-command`, needs `--notifications`, runs with `shell=True` | <https://aider.chat/docs/usage/notifications.html>, `aider/io.py` in <https://github.com/Aider-AI/aider> |
| Dot Buddy | `--report`, `--signal`, `--run` | `Sources/Main.swift`, `selftest.py` |
