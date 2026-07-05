# Contributing to unslop

Thanks for looking at this. It's a small, single-maintainer project, so here's
what actually helps.

## What's wanted

- New buzzwords, phrases, or patterns that LLMs produce and people don't.
  The most useful submissions include a real example of the phrase showing
  up in actual AI output, plus a sentence where it shouldn't fire (so a
  false-positive risk is visible in review).
- False-positive reports: legitimate human prose that gets flagged. Include
  the exact text and what it triggered on.
- Bug fixes, especially anything Windows-specific (this tool is used from
  PowerShell as much as bash, and that's bitten it before).
- Small, focused features. Check open issues first, there may already be
  one scoped out.

Things like a full rewrite engine or an LLM-calling mode are out of scope.
unslop's whole point is that it's local, deterministic, and has zero
network access. A PR that adds a network call or an API key requirement
won't be merged, no matter how good the feature is.

## Dev setup

Clone it, no install needed:

```bash
git clone https://github.com/munzzyy/unslop
cd unslop
python -m pytest tests/ -q
```

That's it. Standard library only, so there's nothing to `pip install`
beyond `pytest` itself for running the test suite. Python 3.8+ (the CI
matrix covers 3.8, 3.11, and 3.14 on both Ubuntu and Windows, check
`.github/workflows/test.yml` for the exact matrix).

To try your change against a real file:

```bash
python unslop.py some-file.md
python unslop.py --json some-file.md
```

## Making a change

- `unslop.py` is the whole tool. The lists you'll touch most:
  - `BUZZWORDS` - single words and short fixed phrases
  - `PHRASES` - whole-phrase tics, matched case-insensitively
  - `PATTERNS` - regex-based constructions with a label, weight, and hint
- Add a test in `tests/test_unslop.py` for anything you change. Tests call
  `unslop.analyze()` directly on a text string in most cases, look at the
  existing tests for the pattern, it's usually a 3-4 line addition.
- If you're adding a new buzzword or phrase, a one-line test asserting it
  gets caught (and, if there's a plausible false-positive shape, one
  asserting it doesn't fire there) is enough.
- Run the full suite before opening the PR:

  ```bash
  python -m pytest tests/ -q
  ```

- Match the existing style: plain, direct comments, no type hints (the
  code doesn't use them anywhere), keep it stdlib-only. If a change needs
  a dependency, it's probably out of scope for this tool.

## Opening a PR

- Keep it focused. One buzzword list update and one bug fix in the same
  PR just makes it harder to review either.
- Explain what you tested it against, especially for pattern changes,
  since the risk is always false positives on legitimate prose.
- I'll review these as I have time. This is a side project I maintain
  solo, so response time varies, don't read silence as a no. If it's been
  a couple weeks with no response, a polite bump is fine.

## Reporting bugs / requesting features

Use the issue templates, they ask for the couple of details that make a
report actionable (exact input, exact output, what you expected).

## Security issues

Don't open a public issue for anything security-sensitive. See
[SECURITY.md](SECURITY.md).
