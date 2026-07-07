# unslop

**See what makes your writing sound like a robot, then fix it before you hit send.** unslop flags the patterns that read as chatbot prose, shows you what it found and where, and gives you a score. Fixing the words is your job.

[![CI](https://github.com/munzzyy/unslop/actions/workflows/test.yml/badge.svg)](https://github.com/munzzyy/unslop/actions/workflows/test.yml)
[![License: Prosperity 3.0.0](https://img.shields.io/badge/license-Prosperity--3.0.0-blue.svg)](LICENSE)
![zero dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)

Three ways to run it: paste into the [browser demo](https://munzzyy.github.io/unslop/), drop the CLI into a pre-commit hook or CI, or install it as a skill so your AI coding agent checks its own prose before handing it back to you.

**[Try it in your browser](https://munzzyy.github.io/unslop/).** Paste a draft and watch the tells light up. It all runs client-side, so nothing you paste is uploaded, stored, or sent anywhere.

[![unslop analyzing a slop-heavy paragraph, every AI tell underlined in place](docs/media/app-dark.png)](https://munzzyy.github.io/unslop/)

Prefer the terminal? It's also one Python file with no dependencies that drops into a pre-commit hook or CI. Same scoring engine either way, and either way it runs locally and deterministically with no network access.

## As an agent skill

Point your coding agent at unslop and it'll lint its own writing before handing a PR description, commit message, or doc back to you. Two install paths, pick whichever your agent supports:

```bash
# Claude Code
/plugin marketplace add munzzyy/unslop
/plugin install unslop@unslop

# any agent using the open Agent Skills standard (Codex, Cursor, and others)
npx skills add munzzyy/unslop
```

Either way, the agent gets [SKILL.md](skills/unslop/SKILL.md): what to run, how to read the score, and the rule that it flags but never rewrites - the rewrite stays the agent's job, same as it's always been yours. Ask the agent something like "check this PR description for AI tells before you post it" and it'll run `unslop.py --json` on the draft and act on what comes back.

## In your browser

[munzzyy.github.io/unslop](https://munzzyy.github.io/unslop/) is the whole tool as a single page. Paste or type, and every buzzword, filler phrase, construction, stray em dash, and emoji gets underlined in place, with a live score and a breakdown of exactly what tripped it. No build step, no account, no server: the page loads the same scorer the CLI uses and runs it on your machine. You can save the page and use it offline.

Nine themes from the header - Paper and Ink, plus Terminal, Sepia, Newsprint, Midnight, both Solarized variants, and a high-contrast mode. Auto follows your system by default; your pick is remembered and applied before the page paints.

[![the light theme, showing the score and the per-finding breakdown](docs/media/app-full-light.png)](https://munzzyy.github.io/unslop/)

> Looking for a package literally named `unslop` on PyPI or npm? Those are different projects - an LLM-based rewriter and an old code-quality tool. This one's git-only for now; see [Install](#install).

## Example

```
$ unslop pr.txt
words: 41   AI-tell score: 658.5/1k   -> reads as AI - needs a real rewrite

LLM buzzwords:
   1x  delves             (lines 1)
   1x  seamlessly         (lines 1)
   1x  streamline         (lines 1)
   1x  robust             (lines 2)
   1x  comprehensive      (lines 3)

Filler phrases:
   1x  "it's important to note" (lines 2)
   1x  "not just a" (lines 2)
   1x  "i hope this helps" (lines 3)

Constructions:
   1x  'not just X but Y' construction (lines 2)
        -> state it plainly instead of the contrast frame
$ echo $?
1
```

## Install

```bash
pipx install git+https://github.com/munzzyy/unslop
```

Or skip the install entirely, since it's a single file with no dependencies:

```bash
curl -LO https://raw.githubusercontent.com/munzzyy/unslop/main/unslop.py
python unslop.py --help
```

## Usage

```bash
unslop draft.md                     # one file
unslop docs/*.md                    # several files
git log -1 --format=%B | unslop     # or stdin
unslop --quiet draft.md             # verdict line only
unslop --json draft.md              # results as JSON
unslop --exclude CHANGELOG.md docs/*.md   # skip a file in a glob run
```

The exit code is 0 when every input scores under the threshold, 1 when something scores over it, and 2 if a path couldn't be read at all - so a crash and a lint finding never look the same to a script. The default threshold is 10; change it with `--threshold`. `docs/*.md` works even on Windows shells that don't expand the glob themselves.

In markdown files, fenced code blocks and inline code are not scored, since code samples aren't prose. Pass `--markdown` to get the same treatment for stdin or other file extensions.

To skip files in a glob or directory run without listing them all on the command line, drop a `.unslopignore` next to them (one glob per line, `#` comments allowed) or repeat `--exclude PATTERN`.

## Config

Editing `unslop.py` directly to change the word lists works, but it doesn't survive a `pipx` upgrade. For anything that needs to persist, drop a `.unslop.json` in your repo root (unslop walks up from the current directory looking for one, stopping at the first `.git` it finds):

```json
{
  "ignore_words": ["robust", "leverage"],
  "ignore_phrases": ["at the end of the day"],
  "extra_words": ["synergize"],
  "extra_phrases": ["circle back"]
}
```

`ignore_words` / `ignore_phrases` remove entries from the built-in lists, `extra_words` / `extra_phrases` add your own on top. All four keys are optional. Use `--config PATH` to point at a specific file instead of relying on the directory walk, or `--no-config` to ignore any config file for one run.

## Hooks

As a plain git hook:

```bash
# .git/hooks/commit-msg
unslop --quiet "$1" || echo "that commit message reads a bit AI"
```

Written like that it only warns. Drop the `|| echo` part if you want it to actually reject the commit.

With [pre-commit](https://pre-commit.com):

```yaml
repos:
  - repo: https://github.com/munzzyy/unslop
    rev: v0.5.0
    hooks:
      - id: unslop
```

That runs on the markdown, text, and rst files in each commit.

As a GitHub Action, no pre-commit framework required:

```yaml
- uses: munzzyy/unslop@v0.5.0
  with:
    paths: "docs/*.md README.md"
```

For inline PR review comments instead of a plain CI log, pipe `--rdjson` output into [reviewdog](https://github.com/reviewdog/reviewdog):

```bash
python unslop.py --rdjson docs/*.md | reviewdog -f=rdjsonl -name=unslop -reporter=github-pr-review
```

`--rdjson` prints one JSON object per finding (message, file, line, severity) instead of the normal report, and pairs with `--exclude`/`.unslopignore` the same way `--json` does.

## What it checks

The word and phrase lists live at the top of [unslop.py](unslop.py); edit them directly if you're hacking on unslop itself, or use a [config file](#config) if you just want to adjust the lists for your own project. Roughly:

- words LLMs lean on far more than people do (`delve`, `robust`, `leverage`, `tapestry`)
- boilerplate phrases (`it's important to note`, `let's dive into`, `I hope this helps`)
- the `not just X, but Y` contrast frame and the `it isn't X, it's Y` flip
- rhetorical-question openers
- em dashes well past normal density
- emoji in prose
- runs of `**Term:** explanation` bullets
- sentence lengths with almost no variation

Each hit has a weight, the weights are summed, and the total is scaled per 1,000 words. Under 10 usually reads fine. From 10 to 25 the text deserves a second pass, and past 25 it needs rewriting rather than word swaps. The cutoffs are judgment calls, not measurements; if they fight your material, move `--threshold`.

The `--json` field names (`words`, `score_per_1k`, `verdict`, `buzzwords`, `phrases`, `patterns`, and the rest) are treated as a stable interface once something depends on them - a pinned test in the suite locks the key set, so a rename shows up as a broken test rather than a silent break in whatever's parsing the output.

## vs. Vale / vale-ai-tells

If you're already running [Vale](https://vale.sh), [vale-ai-tells](https://github.com/tbhb/vale-ai-tells) covers a lot of the same ground with Vale's own style-rule format. The gap it names in its own docs is sentence-length uniformity and paragraph rhythm - it checks vocabulary and phrasing, not cadence. unslop's `sentence_uniformity_cv` check is exactly that: a coefficient-of-variation measure that catches the suspiciously even sentence lengths LLMs tend to produce even when the vocabulary itself passes. And unslop doesn't need a Vale install or a `.vale.ini` to get there - it's one file, stdlib only.

## Limitations

- It matches surface patterns, not intent. A document that quotes slop in running prose gets flagged for it, quotation marks or not. Code formatting is the only escape hatch it understands.
- The lists are one person's opinion about English tech writing, and they only cover English. If `robust` is a term of art in your field, edit the list or raise the threshold.
- A clean score doesn't mean the writing is good, and it doesn't prove a human wrote it. It means none of these particular tells showed up. A careful writer can trip it, and lazy slop can slip past it.

## Contributing

Bug reports, false positives, and new buzzwords/phrases are all welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup and what makes a good PR.

## License

[Prosperity Public License 3.0.0](LICENSE). Free for noncommercial use: personal projects, hobby work, research, education, nonprofits, and government all qualify. Commercial use gets a thirty-day trial, and past that it needs a paid license. To sort one out, open an issue or email Munzzyy5@proton.me.
