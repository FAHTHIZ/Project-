# Contributing

This repository contains the SPECIAL OPS game project built on the VICTUS engine. Read
[AGENTS.md](AGENTS.md) before making changes, and follow the game's build, verification,
licensing and evidence requirements.

## Local commit attribution hook

Enable the repository's commit-message filter in your checkout:

```sh
python3 scripts/install-git-hooks.py
```

The hook removes recognized AI-tool and bot credit trailers from new local commit messages while preserving
human co-authors, human sign-offs, the commit body and issue references. Run
`python3 scripts/test_commit_attribution.py` for its regression tests.

This is a local Git hook, not a history rewrite or GitHub-side filter. Existing commits, commits created through
GitHub's web interface and external automation that does not use this checkout's installed hook are unchanged.
Each clone must enable the hook separately.
