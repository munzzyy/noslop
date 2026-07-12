# Changelog

Newest first. Anyone pinning a tag in pre-commit or the Action can read here what a
bump gets them. Versions before this file existed are reconstructed from the tags.

## v0.10.0 - 2026-07-11

- **Code mode.** `noslop file.py` now asks whether the *code* reads AI-written,
  with the same contract as prose mode: deterministic, local, every point a
  line-numbered finding. A string-aware scanner splits source into comments,
  docstrings, strings, and code across ~60 extensions (ten comment-syntax
  families, shell heredocs included - a heredoc body is payload, not
  comments), then scores chat residue (tool trailers, share links, pasted
  fences, truncation markers - artifact tier), explainer-voice comments,
  narrated walkthroughs (corroboration-gated), comments that restate the code,
  docstrings that restate the function name, stock error/success messages,
  swallowed exception handlers, chat-render typography, emoji, and invisible
  Unicode. The 16-language prose lists run over comment text. Comment density,
  banners, docstring coverage, line-length uniformity, and generic naming are
  report-only diagnostics, on purpose. New flags: `--code`, `--prose`; `--json`
  results carry `mode` in both modes; `--rdjson` emits code findings too.
- A labeled code corpus (14 AI samples across nine languages, one of them a
  deliberately-missed terse agentic case, plus 15 adversarially picked
  pre-2021 human excerpts) with CI floors: AUC 0.9643, detection 92.9% at the
  soft threshold and 85.7% at the hard one, zero human false positives. See
  `eval/README.md` for methods, numbers, and the honest limits.
- noslop.py and web/detector.js score 0.0/100 in code mode on themselves, held
  there by the test suite (mention-vs-use: quoted tells in comments are
  excused, string literals are data).
- Prose mode gains the coding-tool signature artifacts: `Co-Authored-By:`
  trailers from Claude Code/Cursor/Devin, the Claude Code PR footer, and AI
  chat share links (claude.ai, ChatGPT, Gemini) - all artifact tier, in the
  web app too.
- The README's pre-commit and Action examples pin the current release again (they
  sat at v0.6.0 through three releases), and the plugin manifest reports 0.9.0
  instead of 0.4.0. Two new tests lock every pinned version to `__version__`, so a
  future bump that misses one now fails CI.
- The README's PyPI note said the tool was git-only. It hasn't been since v0.8.0;
  the note now points at the `noslop-lint` package name.
- The browser-app section claimed you could save the page for offline use. The
  page does keep working with the network cut once it's loaded, and that's what
  the README says now.
- `.noslopignore` docs match the code: the file is read from the directory you
  run noslop in, not found next to the target files, and there's no parent-directory
  search like `.noslop.json` gets.
- A bare `noslop` on an interactive terminal prints a hint on stderr that it's
  waiting on stdin, instead of sitting there looking hung.
- Mirror workflow points at the old unslop GitLab path until the rename lands
  there.

## v0.9.0 - 2026-07-09

- Ten new checks, each calibrated against the eval corpus before shipping:
  chatbot self-reference and knowledge-cutoff/no-browsing disclaimers score as
  hard artifacts (with researched es/de/ru equivalents), generic listicle
  headings and bare bullet glyphs, copula-avoidance and scope-inflation phrase
  families, punctuation-distribution entropy, and cross-paragraph opener
  repetition.
- Heading-level skips, windowed type-token ratio, and function-word ratio ship
  as report-only diagnostics. They carry the same ESL false-positive risk as
  the sentence-rhythm check, so they never touch the score.
- A Russian research pass: bureaucratic determiner/nominalization buzzwords,
  the opener cliché, and a density check on formal-register crutch verbs,
  calibrated against a real legal text so ordinary formal Russian doesn't trip.
- README and web hero lead with the deterministic, 16-language claim.
- The eval doc separates engine gains from corpus growth in its numbers.

## v0.8.0 - 2026-07-08

- Renamed from unslop to noslop.
- Published to PyPI as `noslop-lint` (PyPI rejected `noslop` as too similar to
  the existing `unslop` package). The module and command are still `noslop`.
- Releases publish through PyPI trusted publishing, so no long-lived token.

## v0.7.0 - 2026-07-08

- The 2025 tell set, each item traced to a source: chat-UI paste residue
  (`oaicite`, `utm_source=chatgpt.com` - one hit scores the hard verdict
  alone), the measured excess vocabulary from two 2025 word-frequency studies,
  significance inflation, the dangling `-ing` closer, the split-sentence
  `It isn't X. It's Y.` flip, anaphora triads, fragment hooks, sycophantic
  openers, staccato runs, paragraph-length uniformity, heading emoji, inline
  bold spray, quote mixing, and connective-opener density.
- A labeled eval corpus with detection rate, false-positive rate, and AUC,
  plus CI floors so a change that regresses either side fails the build.
- The web app surfaces the new findings, and marks are tappable on touch.
- CI actions moved off deprecated Node 20 runners.

## v0.6.0 - 2026-07-07

- Sixteen languages, up from seven: ru, uk, pl, cs, tr, sv, ro, hu, and fi
  join, each researched in that language rather than translated from English.
- An honest fallback line when the detector can't place the language, instead
  of silently scoring with the English lists.
- The browser app gets a UI language picker (32 languages) and a per-paste
  text-language override.
- Workflow actions pinned to commit SHAs; Action inputs routed through
  environment variables.

## v0.5.0 - 2026-07-07

- Nine themes in the browser app, applied before first paint so there's no
  flash of the wrong one.
- The README leads with what the tool does and grew its badges.

## v0.4.0 - 2026-07-07

- Agent-skill packaging, so it installs into Claude Code and anything else
  that reads the Agent Skills layout.

## v0.3.0 - 2026-07-06

- The browser version: the same scorer as one static page, no build step.
- A composite GitHub Action and rdjsonl output for reviewdog.
- Project config (`.noslop.json`), `.noslopignore`, and `--exclude`.
- Relicensed to the Prosperity Public License 3.0.0.
- GitLab mirror of main and tags.

## v0.2.1 - 2026-07-05

- Word-boundary matching replaces raw substring matching, which killed a
  class of false positives.
- stdin decodes as UTF-8 on Windows consoles instead of mangling em dashes
  and emoji through cp1252.
- Exit codes documented (0 clean, 1 flagged, 2 unreadable input) and globs
  expand on shells that don't do it themselves.

## v0.2.0 - 2026-07-04

- Multiple files per run; fenced and inline code in markdown is not scored.
- Fixed double counting between the word and phrase lists.
- Rewrote the README, which read like the thing it lints.

## v0.1.0 - 2026-07-04

- First release, as unslop: the buzzword, phrase, and construction lists,
  the rhythm checks, and a pre-commit hook.
