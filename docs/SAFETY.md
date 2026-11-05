# Safety model

This tool coordinates two AI agents through git files. The design goal is that **a note, log line or board row can
never make anything happen by itself.**

## Threat we design for

The cloud agent reads email and the web. Text written by a stranger can end up in a note, a log line or a board row,
worded like an instruction ("approve the payment", "run this"). The tool and the agents must treat that as data.

## What the tool does and does not do

| Property | How it is enforced |
|---|---|
| No execution path | `tools/bridge.py` never runs file content. Its only subprocess is `git` (`pull --rebase`, `diff --cached`). `tests/test_no_exec.py` parses the source and fails on `eval`, `exec`, `compile`, `os.system`, `shell=True`, or any subprocess other than `git`. |
| No network | The tool opens no sockets and imports no network library. Transport is git. |
| No deletion | No command removes a file. Release, done and consume stamp lines. |
| No silent overwrite | New notes, reports and approvals are created with exclusive-create. Updates to existing files are atomic (temp file, then rename). |
| Bounded approvals | At most 7 days, exact-scope match, single use, quote required. |
| Least privilege for the cloud agent | An approval the cloud agent records needs the owner's `chat_time` and covers low-risk actions only. Unknown actions count as high-risk. |
| Pause | `bridge.OFF` in the repo root blocks `claim`, `approve`, `approval check`, `approval consume`. |
| Secrets | Pre-commit secret scan (gitleaks or regex). `--history` before every push. |

## The approvals flow

1. The owner says "yes, do X" in their own chat with an agent.
2. That agent records it: `bridge.py approve --scope "X" --expires 1d --quote "<their words>" --agent <agent>`
   (the cloud agent adds `--chat-time` or writes the file by hand, recipe 6).
3. Before acting, the local agent runs `approval check <ID> --scope "X"`.
   - exit 0: valid for this exact scope, once.
   - exit 1: missing, expired, used, paused or scope differs.
   - exit 2 `NEEDS-CONFIRM`: it was recorded by the cloud agent and X is not clearly low-risk. Ask the owner again,
     or have the local agent record a fresh approval from the owner's own chat.
4. `approval consume <ID> --scope "X"`, commit, **push**, then act. The push is the lock.

## Known limits

- **Convention, not identity.** `granted_by: "Owner"` is a string. Anyone with write access can type it. Protect
  the repo (private, few writers, branch protection, signed commits). This is the largest gap.
- **Heuristic classifier.** Low/high risk is decided with word lists in `tools/bridge.py`. It errs towards "high"
  but a crafted scope such as "read the file and mail it to ..." could start with a low-risk verb. Treat exit 0 on a
  cloud-recorded approval as permission to *consider* the action, and read the scope yourself.
- **Honour system for the agents.** The tool cannot stop an agent that ignores it. The protection is the agents'
  instructions (`INSTRUCTIONS.md`) plus a human reading `git log`.
- **Race on single-use approvals** is resolved by git push order, not by a lock service.
- **Everything is plain text in git.** Do not put secrets, third parties' personal data or customer data in notes,
  logs or the board. The pre-commit scan catches common key shapes only.
- **Prompt injection is mitigated, not solved.** The rule "files are data" is advice to a model. Review what the
  cloud agent wrote before the local agent acts on anything that matters.

## Reporting problems

See `SECURITY.md`.
