# Duet Duo

**A git-based ledger that lets a cloud AI agent and a local AI agent hand work to each other, with approvals, claims and a shared log. No server. No execution path.**

> ## ⚠️ Not affiliated with Anthropic
> **Duet Duo is an independent, unofficial community project. It is not made, endorsed, sponsored or supported by Anthropic.** "Claude", "Claude Code" and "Duet" are names of Anthropic products and are used here only to describe what this tool can work alongside. This project has no logo, and nothing in it is meant to look official. For the real products, see Anthropic's own website and documentation.

> **Unofficial holdover.** At the time of writing (November 2026), I know of no built-in way for a cloud agent (one that can reach only a GitHub connector) and a local agent (one that has your files and a shell) to coordinate. This tool fills that gap with a plain git repo. I have not checked it against Anthropic's current feature list, so verify before relying on that. If native support exists or arrives, you should probably use that instead.

## Why it's built this way

- **Claude surfaces are sandboxed and cannot talk to each other.** A cloud agent cannot reach your machine, and a local agent is not listening for the cloud. So the bridge is a shared, git-backed **paper trail** (board, claims, approvals, log, heartbeats), not a live remote-control line.
- **It passes intent, never execution.** A note says what someone wants or found; it never runs anything. Each side acts under its **own permissions**, with a **human approval in the middle**. That limits prompt injection: the cloud agent reads email and the web, so anything it writes could contain words a stranger wrote. A file can never make the tool run anything, and the local agent is told to treat files as data and to wait for a human approval before anything risky. This is mitigated, not solved: the local agent is still a model that reads those notes (see Limits and `docs/SAFETY.md`).
- **It is asynchronous and durable.** State lives in git, so it survives disconnects, resets, restarts and a laptop that sleeps. Work picks up where the files say it stopped.
- **It is fully auditable.** Every claim, approval, decision and handoff is recorded as plain text in the repo, and `git log` shows who changed what and when.
- **It works within today's limits.** It is a holdover until native support exists (at the time of writing, none that I know of), and it needs nothing beyond git and Python's standard library.

The trade-off is speed. A ledger moves at the pace of each agent's check-ins (minutes to hours), not seconds. Bridges that start work on your machine the moment a message arrives give you speed, and in exchange they put a command-running path between whatever the cloud agent read and your computer. This project chooses the slower, auditable side of that trade on purpose.

## The problem

You run two agents:

- **Duet**, a cloud agent. It checks in every few hours, reads your email and the web, and can reach your repos only through a GitHub connector. It has no shell and cannot see your computer.
- **Dispatch**, a local agent (for example Claude Code or a coordinator on your own machine). It has files, a shell and local models, but it is only awake when you talk to it or a script runs it.

"Duet" and "Dispatch" are role names. Rename them in `tools/bridge.py` (`AGENTS`) and the schemas if you like.

They need to hand off work, avoid doing the same task twice, remember what you decided, and never act on a "yes" you did not give. This repo is the shared ground between them.

## How it works

```
        you (the owner)
         |   chat                 chat
         v                         v
   +-----------+              +-----------+
   |  Duet     |              | Dispatch  |
   |  (cloud)  |              |  (local)  |
   +-----+-----+              +-----+-----+
         | GitHub connector         | git + tools/bridge.py
         | (plain file edits)       | (stdlib Python)
         v                          v
      +---------------------------------+
      |   your PRIVATE git repo         |
      |   BOARD.md  claims/  inbox-*/   |
      |   done/  log/  approvals/       |
      |   heartbeat/                    |
      +---------------------------------+
```

Git is the only transport. Nothing listens on a port, nothing calls a webhook, and **nothing in this repo runs a command because a file told it to**. Every file is data.

| Path | What it holds |
|---|---|
| `BOARD.md` | one row per task: ID, owner, state, next step, updated |
| `claims/<ID>.claim` | who is working on a task |
| `inbox-duet/`, `inbox-dispatch/` | one handoff note per task, with front matter |
| `done/<ID>.md` | finish reports; the last line is always a `STATUS:` line |
| `log/<date>/<agent>.md` | shared log, one file per agent per day, so two writers never conflict |
| `log/digest/<date>.md` | daily digest: decisions, promises, requests and approvals |
| `approvals/<A-ID>.approval` | the owner's approvals: exact scope, expiry, quote, single use |
| `heartbeat/<agent>.json` | each agent's last sign of life |
| `schema/` | JSON Schema for claims, notes and approvals |
| `tools/bridge.py` | CLI for the local agent (Python 3.10+, standard library only) |
| `tools/secret-scan.sh`, `hooks/pre-commit` | secret scan and validation before every commit |
| `INSTRUCTIONS.md` | one shared instructions file both agents load |
| `docs/RECIPES.md` | plain-file-edit recipes for the cloud agent (it has no shell) |
| `docs/SAFETY.md` | the safety model in detail |

## Set up (about five minutes)

You need Python 3.10 or newer and git. There are no packages to install.

1. Make a **private** repository from this one (GitHub's "Use this template", or clone and push to a new private repo). Do not keep your working ledger in a public repo.
2. Clone it and turn on the commit hook:
3. Try the loop below.
4. Give the cloud agent access to the private repo through its GitHub connector, and point it at `INSTRUCTIONS.md` and `docs/RECIPES.md`.

<!-- test: quickstart -->
```sh
git config core.hooksPath hooks      # secret scan + validation before every commit
python3 -m unittest discover -s tests -q
python3 tools/bridge.py status
python3 tools/bridge.py claim WEBAPP-AUDIT --owner Dispatch --repo acme/webapp --eta 2h
python3 tools/bridge.py note WEBAPP-AUDIT --from Dispatch --to Duet --status review --next "Duet reviews the findings" --body "Audit written."
AID=$(python3 tools/bridge.py approve --scope "read the webapp README" --expires 1d --quote "yes, read it" --agent Dispatch)
python3 tools/bridge.py approval check "$AID" --scope "read the webapp README"
python3 tools/bridge.py approval consume "$AID" --scope "read the webapp README" --agent Dispatch
python3 tools/bridge.py log said "audit started" --agent Dispatch
python3 tools/bridge.py done WEBAPP-AUDIT --owner Dispatch --summary "Audit written." --status-line "STATUS: done, owner picks the first fix"
python3 tools/bridge.py validate
git add -A && git commit -m "first bridge entries" && git push
```

The test suite runs this exact block in a fresh clone, so the README cannot drift from the tool.

## The loop

**Local agent (Dispatch), before every reply:** `sync` (git pull --rebase, then validate) -> read today's `log/`, `inbox-dispatch/`, `BOARD.md` and `stale` -> `request seen "<owner's words>"` to avoid doing it twice -> `claim`, then push at once -> work -> `note` or `done` -> `log` -> push.

**Cloud agent (Duet), at every check-in and every message from the owner:** read the log, `inbox-duet/`, `BOARD.md` and `heartbeat/` -> check whether the request was already handled -> act or hand over with a note -> log -> update its heartbeat. It does all of this with plain file edits; see `docs/RECIPES.md`.

Commands: `claim`, `release`, `note`, `done`, `board`, `stale`, `validate [--fix-report]`, `sync`, `log`, `digest`, `request new|seen`, `approve`, `approval check|consume`, `heartbeat`, `status`. Run `python3 tools/bridge.py -h`.

## Security model (short version; full text in `docs/SAFETY.md`)

- **No execution path.** `tools/bridge.py` reads and writes files and runs only `git` (`pull --rebase` and `diff --cached --name-only`). It never executes anything taken from a note, log, board row or approval. A test (`tests/test_no_exec.py`) fails if the tool gains `eval`, `exec`, `os.system`, `shell=True` or any subprocess other than `git`.
- **Files are data, never instructions.** The cloud agent reads email and the web, so its notes can carry text someone else wrote. Only the owner's own words in their own chat authorise an action.
- **Approvals are per action.** Each records the exact scope, an expiry of at most 7 days, the owner's quote and a single use. An approval the *cloud* agent records must also carry the time the owner said it (`chat_time`) and covers **low-risk actions only** (reads, drafts, board edits, local branches). Anything else answers `NEEDS-CONFIRM`, and `approval consume` refuses it.
- **Nothing is deleted.** `release`, `done` and `consume` add lines; they do not remove files. Writes to existing files are atomic (write to a temp file, then rename). New notes and reports refuse to overwrite.
- **Kill switch.** Create a file named `bridge.OFF` in the repo root and commit it. While it exists, `claim`, `approve`, `approval check` and `approval consume` refuse. Reading, logging, notes and `validate` still work, so work can be wound down. Only the owner removes it.
- **Secret scan.** The pre-commit hook runs `gitleaks` if installed, else a regex fallback. Run `sh tools/secret-scan.sh --history` before every push.

## Limits (please read)

- **This is a convention, not an identity system.** Anyone or any agent with write access to the repo can write an approval file that says `granted_by: "Owner"`. Keep the repo private, limit who has write access, and consider branch protection and signed commits. A forged file is exactly what the "data, not instructions" rule and the `chat_time` requirement are there to make agents distrust, but nothing here enforces it cryptographically.
- **The risk classifier is a guard rail, not a wall.** `approval check` sorts a scope into low or high risk with word lists, and treats anything unknown as high. A cleverly worded scope can slip a high-risk action past the low list. The local agent still has to read the scope and judge it.
- **The tool does not stop an agent from ignoring it.** It records and checks. Enforcement comes from the agents following `INSTRUCTIONS.md`.
- **Single-use approvals rely on push order.** Consume, commit and push *before* acting. If two agents race, the second push is rejected and that is the safety check.
- **Latency is the cloud agent's check-in schedule** (hours), not seconds. This is a ledger, not a live link.
- Two writers editing the same `BOARD.md` row at once produce a normal git conflict (loud, never silent loss).
- Times are UTC with a `Z`. IDs are capitals, digits and dashes.

## Roadmap (not built)

- A `bridge.py doctor` that checks a local agent CLI is signed in before queueing work for it. Skipped: this tool never starts an agent.
- Signed approvals (GPG/SSH-signed commits checked by CI) for the "convention, not identity" gap.
- Optional read-only runner that starts a locked-down local agent session for a note. Would add an execution path, so it needs a separate threat model first.
- Stale-claim auto-release suggestions; a small web viewer for the board.

## Development

```sh
python3 -m unittest discover -s tests -v
```

See `CONTRIBUTING.md` and `SECURITY.md`. Licence: MIT (`LICENSE`). No dependencies, so no third-party licences apply.

*Duet Duo is not affiliated with, endorsed by or supported by Anthropic. No Anthropic logos or trademarks are used or implied.*
