# fxs

Run persistent cloud coding agents (`fx`, `claude`, `codex`, `opencode`, or custom agent shims) in [Vercel Sandboxes](https://vercel.com/docs/sandbox) directly from your terminal, with snapshot-backed startup, `dtach` persistence across laptop sleep, idle auto-stop, and local session/file sync.

## Features

- **Pluggable agent shims:** Built-in support for `fx` (default), `claude` (Claude Code), `codex`, and `opencode`, plus custom JSON shims under `~/.config/fxs/agents/`.
- **First-class onboarding (`fxs init`):** Interactive setup (or `--yes` flags for automated agent setup) that configures your Vercel team/project, default agent, toolchains, optional skill repositories, optional warm repo caches, and base snapshot.
- **Persistent across laptop sleep (`dtach`):** Runs agents inside `dtach` on the sandbox host instead of `tmux`, keeping native terminal scrolling, selection, and copy/paste intact while letting long tasks continue in the cloud if your laptop sleeps.
- **Idle watchdog & bounded sessions:** Defaults to a `6h` session cap, auto-extends `+2h` while the agent is actively working, and stops the sandbox after `30` idle minutes (`FXS_IDLE_MINUTES`) so compute billing pauses while disk state stays preserved.
- **Local session & file sync:** Syncs `fx` session history back to your machine on exit (so `fx -r <id>` or `fxs local <id>` works even after removing the sandbox) and lets you pick which workspace files to copy locally (`fxs pull`).
- **Image paste sync:** Automatically detects local image paths pasted into the terminal (e.g. clipboard screenshots) and copies them to the matching path inside the sandbox before forwarding the paste.
- **Direct mobile/SSH access (`Tailscale SSH`):** Save a reusable Tailscale auth key with `fxs tailscale-key` (or run `fxs ssh <sandbox>`) so every sandbox joins your tailnet and accepts SSH connections (for example from Termius on iOS) with `fxs-attach` to attach to the live agent session.
- **Verified SSH commit signing (`fxs signing-setup`):** Generates a dedicated sandbox SSH signing key (`~/.ssh/fxs_signing`), configures `gpg.format=ssh` + `commit.gpgsign=true`, and registers the public key on GitHub when `gh` has `admin:ssh_signing_key`.
- **Side-by-side Rex panes:** `fxs --split` and `fxs group N` open multiple independent sandboxes side by side when running inside [Rex](https://www.superlogical.com/rex).

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/fazxes/fxs/main/install.sh | sh
```

Or clone and install locally:

```sh
git clone https://github.com/fazxes/fxs.git
cd fxs
./install.sh
```

## Quickstart

### Interactive onboarding

```sh
fxs init
```

### Non-interactive onboarding (for scripts or agents)

```sh
fxs init --yes \
  --team my-team \
  --project my-sandbox-project \
  --agent fx \
  --tools gh,node,bun,zig
```

### Daily usage

```sh
fxs                          # boot a new sandbox and start the default agent
fxs --agent claude           # boot a sandbox with Claude Code
fxs --agent codex            # boot a sandbox with Codex
fxs --agent opencode         # boot a sandbox with OpenCode
fxs --timeout 12h            # override session timeout

fxs resume                   # pick a recent sandbox to wake/reattach
fxs resume <sandbox-or-id>   # wake/reattach by sandbox name or session ID

fxs pull <sandbox>           # sync sessions and interactively pick files to keep
fxs pull <sandbox> --list    # JSON list of files in the sandbox
fxs local                    # list locally saved sandbox sessions

fxs watchdog status                  # inspect idle watchdog state
fxs tailscale-key                    # save reusable Tailscale auth key (auto-enables SSH)
fxs ssh <sandbox>                    # enable Tailscale SSH on an existing sandbox
fxs signing-setup [--sandbox NAME]   # enable SSH commit signing in base or one sandbox
fxs ls                               # list sandboxes
fxs stop <sandbox>           # stop sandbox (keeps disk, pauses billing)
fxs rm <sandbox>             # delete sandbox
```

### Rex multi-pane workflows

When running inside Rex:

```sh
fxs --split                  # open a second sandbox pane next to the current one
fxs group 3                  # open 3 side-by-side sandboxes in a new tab
fxs group 4 --workspace work # open a 2x2 sandbox grid in a new Rex workspace
```

## Pre-warming repositories and skills

During `fxs init` (or in `~/.config/fxs/config.json`), you can pre-warm tools, skills, and project caches into your base snapshot:

- `--tools gh,node,bun,zig,zsh,fish`: preinstalls selected toolchains.
- `--skill-repo owner/repo`: clones a skill repository and copies its `SKILL.md` directories into the base snapshot.
- `--warm-repo https://github.com/org/repo.git`: clones and pre-builds the repo (`zig build` with `.zig-cache` seed, `bun install` / `npm install`) in the base snapshot so new sandboxes start warm.
- `fxs mcp-login <server...>`: authenticates HTTP MCP servers configured in `~/.fx/mcp.json` using your local browser and saves them into your base snapshot.

## Custom agent shims

Add any CLI agent by dropping a JSON file in `~/.config/fxs/agents/<name>.json` or running:

```sh
fxs agents add mybot /usr/local/bin/mybot --install "npm i -g mybot"
```

## Configuration & environment variables

Configuration lives in `~/.config/fxs/config.json` and `~/.config/fxs/base.json`.

| Variable | Effect |
| --- | --- |
| `FXS_CONFIG_DIR` | Override `~/.config/fxs` |
| `FXS_CACHE_DIR` | Override `~/.cache/fxs` |
| `FXS_PULL_DIR` | Override default file pull folder (`~/sandbox-pulls`) |
| `FXS_IDLE_MINUTES` | Override idle stop timeout (`0` disables the watchdog) |
| `FXS_ZIG_VERSION` | Zig version installed when `zig` is in `tools` |
| `FXS_BUN_VERSION` | Bun version installed when `bun` is in `tools` |
