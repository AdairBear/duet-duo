# Security policy

## Supported versions

Only the latest release on the default branch gets fixes. This project is pre-1.0 (beta).

## Reporting a vulnerability

Please do **not** open a public issue for a security problem.

Use GitHub's private vulnerability reporting: on the repository page choose **Security -> Report a vulnerability**.
Include the version or commit, what you did, what you expected and what happened. You should get a first reply
within 7 days. Fixes are released with credit to the reporter unless you ask otherwise.

## What counts

In scope: any way for file content (a note, log line, board row, approval, heartbeat) to cause code execution, file
deletion, overwrite of existing data, or a bypass of the approval checks in `tools/bridge.py`; a secret-scan bypass
for common key shapes; path traversal via an ID or file name.

Out of scope (documented limits, see `docs/SAFETY.md`): the owner identity being a convention rather than a
signature; the risk classifier being a heuristic; an agent choosing to ignore its instructions.

## Hardening checklist for users

- Keep your working ledger in a **private** repo and limit who can write to it.
- Turn on branch protection and signed commits if more than one person or agent can push.
- Run `sh tools/secret-scan.sh --history` before every push; install `gitleaks` for better detection.
- Never put credentials or other people's personal data in notes, logs or the board.

## Not affiliated

This is an independent community project. It is not affiliated with Anthropic and is not an Anthropic security
contact. Report problems with Anthropic's products to Anthropic.
