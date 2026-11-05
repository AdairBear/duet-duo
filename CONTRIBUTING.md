# Contributing

Thanks for helping. This is a small, dependency-free tool and we want to keep it that way.

## Ground rules

- **Python 3.10+, standard library only.** No new dependencies without a strong reason.
- **No execution path.** Do not add code that runs a command taken from a file. `tests/test_no_exec.py` will fail.
- **No deletion.** Commands add or stamp; they do not remove files.
- **Tests with the change.** Each non-trivial behaviour gets a test. Do not weaken, skip or delete an existing test
  to make a change pass; if a test looks wrong, say why in the pull request.
- **Docs with the change.** If you add a hand-written file format, add a template to `docs/RECIPES.md`; the tests
  check that every template passes `validate`.
- Keep functions short and comments about *why*.

## Workflow

```sh
git clone <your fork> && cd duet-duo
git config core.hooksPath hooks
python3 -m unittest discover -s tests -v
```

Open a pull request against the default branch. CI runs the tests on Python 3.10, 3.12 and 3.13 and a secret scan.

## Good first issues

See the Roadmap in `README.md`. Please open an issue before starting anything that adds an execution path or a
network call: those need a threat model first.

## Not affiliated

This project is not affiliated with Anthropic. Do not add Anthropic logos or imply endorsement.

## Licence

By contributing you agree your contribution is licensed under the MIT licence in `LICENSE`.
