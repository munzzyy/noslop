---
name: noslop
description: Flag AI-sounding prose (buzzwords, filler phrases, the not-just-X-but-Y frame, em-dash spray, flat sentence rhythm) before it ships, and AI-looking code (narrated comments, chat residue, stock error handling) in source files. Use before finalizing any writing a user will publish or send - PR descriptions, commit messages, issue comments, READMEs, docs, emails - and to check whether a source file reads AI-written.
---

# noslop

Run this before you finalize any prose a user is about to publish or send. It won't rewrite
anything for you - that's still your job - but it'll tell you exactly what to fix and where.

## When to use it

Before finalizing:
- a PR description or commit message
- an issue or PR comment
- a README, changelog, or any doc
- a blog post or newsletter draft
- an email you're drafting on someone's behalf

Source code gets its own mode instead of being skipped: pass a file with a code
extension (or `--code` on stdin) and noslop scores the *code* for AI tells -
narrated step comments, explainer voice, chat residue, stock error handling -
with line numbers. Use that before shipping code a user asked you to review for
AI authorship, or to check that code you edited doesn't read machine-written.
Skip prose mode for terminal output and anything that isn't meant to read as prose.

## How to run it

```bash
python noslop.py --json path/to/draft.md
```

No file yet? Pipe the text in instead:

```bash
echo "some text here" | python noslop.py --json
```

Markdown gets its fenced/inline code blocks skipped automatically by extension; pass
`--markdown` to get the same treatment on stdin or a non-`.md` file. Drop `--json` for a
human-readable report with line numbers instead of the machine-readable one.

Non-English prose works too: sixteen languages ship with their own researched tell
lists (es, fr, de, pt-BR, it, nl, ru, uk, pl, cs, tr, sv, ro, hu, fi alongside en), and
the input language is detected per file. Check the `language` and `language_source`
fields in the JSON - `"fallback"` means no pack matched and only the structural checks
plus the English lists ran, so treat a clean score on such text as weak evidence. Force
a pack with `--lang de` when you know what the text is.

## Reading the result

The important field is `score_per_1k`, a weighted count of AI tells per 1,000 words:

- **under 10** - reads clean, ship it
- **10 to 25** - worth a second pass; check the `patterns`, `buzzwords`, and `phrases` keys
  for what tripped it and where
- **25 and up** - needs a real rewrite, not word swaps

`verdict` gives you the same read as a string. The rest of the JSON (`buzzwords`, `phrases`,
`patterns`, `em_dashes`, `emoji`, `bold_label_bullets`, `sentence_uniformity_cv`) tells you
exactly which lines to fix and why: overused LLM vocabulary, boilerplate phrases, the
`not just X, but Y` contrast frame, em-dash overuse, emoji in prose, repeated bold-label
bullet lists, and suspiciously uniform sentence lengths.

## Reading a code-mode result

Code results carry `"mode": "code"` and score per 100 code lines in
`score_per_100`, same verdict bands (under 10 clean, 10-25 worth a look, 25+
reads AI-written). The finding keys tell you why: `ai_artifacts` is direct chat
residue (a paste fence, a tool trailer, a truncation marker - one hit already
pins the hard verdict), `comment_phrases` and `narration_comments` are the
explainer voice, `redundant_comments` restate the code they sit on, and
`error_boilerplate`/`swallowed_errors` are the stock catch-and-print shape.
Two things a clean score does not mean: that a human wrote it (terse agent
output scores clean by design), and two things that never score: comment
density and docstring coverage, which are reported as diagnostics only.

## The rule

noslop flags patterns, it doesn't rewrite sentences. When something scores high, rewrite it
yourself in plain, direct language - don't just swap out the flagged words and call it done,
and don't argue with the score. A flag you're tempted to explain away is usually a flag that's
right.

No network access, no dependencies, nothing leaves the machine.
