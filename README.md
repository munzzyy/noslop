# unslop

A small command-line tool that flags the parts of your writing that sound like a chatbot, so you can fix them before you hit send.

It doesn't rewrite anything. It marks the spots — stock phrases, filler words, tired contrast frames, em-dash pileups, emoji, sentences that all run the same length — and gives you a score. The rewrite is yours.

No dependencies. No network. Nothing phones home. One Python file.

## Why

AI writing has a sound. Once you can hear it, you hear it everywhere. It leans on the same few words. Everything gets hedged. The rhythm never changes.

Readers pick up on it too, even when they can't name it. In a pull request, a cover letter, an email to someone who matters, that sound gets your writing skimmed or trusted a little less. This is a gut-check before that happens.

It's a smell test, not a grade. A clean score doesn't mean the writing is good, and a flagged word isn't always wrong. Read what it says and use your judgment. Keep the em-dash if you meant it.

## Install

```bash
pipx install unslop        # once it's on PyPI
```

Or skip that. It's one file with nothing to install:

```bash
python unslop.py --help
```

## Use

```bash
unslop draft.md                  # scan a file
git show HEAD:MESSAGE | unslop    # scan a commit message
echo "Let's dive into it" | unslop
unslop --quiet draft.md           # just the verdict
unslop --json draft.md            # machine-readable
```

The exit code is 0 when the writing reads human and 1 when it doesn't, so you can drop it into a git hook or CI:

```bash
# .git/hooks/commit-msg
unslop --quiet "$1" || echo "heads up, that message reads a bit AI ^"
```

Or wire it in through [pre-commit](https://pre-commit.com), where it runs on your markdown and text files:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/munzzyy/unslop
    rev: v0.1.0
    hooks:
      - id: unslop
```

## What it flags

- Buzzwords: delve, tapestry, robust, seamless, leverage, pivotal, myriad, harness, and the rest of the usual crowd.
- Filler phrases: "it's important to note," "at the end of the day," "when it comes to," "I hope this helps."
- The "not just X, but Y" frame, and its cousin "it isn't X, it's Y."
- Em-dash pileups. One is fine. Five in a paragraph is a tell.
- Emoji in prose.
- Flat rhythm, where every sentence is the same length.

Under 10 per 1,000 words reads clean. 10 to 25 wants a pass. Past 25 needs real work. Move the cutoff with `--threshold`.

## Yes, running it on this README lights up

Point unslop at this file and it flags plenty, because the section above quotes the exact words and phrases it hunts for, and one example pipes in "let's dive into it." It can't tell a quote from the real thing. This is the one file where the false alarms are the point.

## Not a language cop

The word lists are opinions, not law. If your field really does use "robust" or "comprehensive" as terms of art, lean on `--threshold` or just your own eyes. The point is to catch the reflex version of these words, the ones you reached for without thinking, not to ban them.

## License

MIT. Do what you want with it.
