# unslop

A command-line linter for prose. It flags the patterns that make writing sound like a chatbot: stock phrases, overused buzzwords, the `not just X, but Y` frame, em-dash pileups, emoji, sentences that all run the same length. You get a list of what it found, where it is, and a score. Fixing the text is up to you.

One Python file, standard library only, no network access.

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
```

The exit code is 0 when every input scores under the threshold and 1 otherwise, so it slots into hooks and CI. The default threshold is 10; change it with `--threshold`.

In markdown files, fenced code blocks and inline code are not scored, since code samples aren't prose. Pass `--markdown` to get the same treatment for stdin or other file extensions.

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
    rev: v0.2.0
    hooks:
      - id: unslop
```

That runs on the markdown, text, and rst files in each commit.

## What it checks

The word and phrase lists live at the top of [unslop.py](unslop.py), so that's the place to edit when you disagree with them. Roughly:

- words LLMs lean on far more than people do (`delve`, `robust`, `leverage`, `tapestry`)
- boilerplate phrases (`it's important to note`, `let's dive into`, `I hope this helps`)
- the `not just X, but Y` contrast frame and the `it isn't X, it's Y` flip
- rhetorical-question openers
- em dashes well past normal density
- emoji in prose
- runs of `**Term:** explanation` bullets
- sentence lengths with almost no variation

Each hit has a weight, the weights are summed, and the total is scaled per 1,000 words. Under 10 usually reads fine. From 10 to 25 the text deserves a second pass, and past 25 it needs rewriting rather than word swaps. The cutoffs are judgment calls, not measurements; if they fight your material, move `--threshold`.

## Limitations

- It matches surface patterns, not intent. A document that quotes slop in running prose gets flagged for it, quotation marks or not. Code formatting is the only escape hatch it understands.
- The lists are one person's opinion about English tech writing, and they only cover English. If `robust` is a term of art in your field, edit the list or raise the threshold.
- A clean score doesn't mean the writing is good, and it doesn't prove a human wrote it. It means none of these particular tells showed up. A careful writer can trip it, and lazy slop can slip past it.

## License

MIT.
