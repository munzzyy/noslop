#!/usr/bin/env python3
"""unslop - flag the AI tells in a piece of writing.

Reads text from file arguments or stdin and prints the patterns that make prose
read as LLM-generated: filler phrases, overused buzzwords, the "not just X, but Y"
frame, em-dash spray, emoji, and suspiciously even sentence rhythm. It does NOT
rewrite anything - that's your job. It just shows you where to look.

Standard library only. No network, no dependencies.

Usage:
  unslop draft.md
  unslop docs/*.md
  echo "some text here" | unslop
  unslop --json draft.md       # machine-readable
  unslop --quiet draft.md      # verdict line only

Exit code is 0 when every input reads human enough, 1 when something needs
a pass, and 2 if a path couldn't be read at all - so a crash and a lint
finding never look the same to a script.
"""
import sys
import re
import json
import glob
import argparse

__version__ = "0.2.0"

# Words that show up far more in LLM prose than in how people actually write.
BUZZWORDS = [
    "delve", "delved", "delves", "delving", "tapestry", "testament", "realm", "realms",
    "landscape", "navigate", "navigating", "robust", "seamless", "seamlessly",
    "leverage", "leveraging", "leverages", "underscore", "underscores",
    "underscoring", "pivotal", "crucial", "comprehensive", "intricate",
    "intricacies", "myriad", "plethora", "foster", "fostering", "elevate",
    "elevates", "elevating", "embark", "unlock", "unlocks", "unlocking",
    "harness", "harnessing", "cutting-edge", "game-changer", "game-changing",
    "boasts", "boasting", "nestled", "bustling", "vibrant", "showcase",
    "showcasing", "spearhead", "meticulous", "meticulously", "ever-evolving",
    "ever-changing", "holistic", "synergy", "paradigm", "profound", "nuanced",
    "multifaceted", "beacon", "treasure trove", "delve into", "rich tapestry",
    "supercharge", "turbocharge", "effortless", "effortlessly", "unleash",
    "empower", "empowering", "transformative", "reimagine", "reimagined",
    "streamline", "streamlined", "peace of mind", "dive deep", "deep dive",
]

# Whole-phrase tics. Matched case-insensitively as substrings.
PHRASES = [
    "it's important to note", "it is important to note", "it's worth noting",
    "it is worth noting", "in conclusion", "in summary", "to sum up",
    "that said", "rest assured", "needless to say", "at the end of the day",
    "in today's world", "in today's fast-paced", "let's dive", "dive into",
    "let's break it down", "here's the thing", "i hope this helps",
    "feel free to", "happy to help", "great question", "as an ai",
    "as a language model", "this is where", "look no further",
    "without further ado", "the key takeaway", "let's explore",
    "let's take a look", "buckle up", "when it comes to", "at its core",
    "the world of", "in the realm of", "plays a vital role",
    "plays a crucial role", "a wide range of", "more than just",
    "not just a", "whether you're a", "gone are the days",
]

# (label, regex, weight, hint)
PATTERNS = [
    ("'not just X but Y' construction",
     r"\bnot (?:just|only)\b[^.?!\n]{1,70}?\bbut\b", 3,
     "state it plainly instead of the contrast frame"),
    ("'it isn't X, it's Y' flip",
     r"\bis(?:n't| not)\b[^.?!\n]{1,45}?\bit(?:'s| is)\b", 2,
     "just say what it is"),
    ("rhetorical question opener",
     r"(?im)^\s*(?:ever wondered|have you ever|what if|imagine (?:a|if|that)|picture this)\b", 2,
     "open with the point, not a hook"),
    ("hedge stack (may/can/often/typically)",
     r"\b(?:may|might|can|could|often|typically|generally|usually|arguably)\b", 0,
     "too many hedges reads evasive - commit or cut"),
]

# Real emoji + the decorative dingbats used as slop. Plain glyphs that belong
# in technical prose - check/cross marks (U+2713 U+2717), bare arrows, bullets,
# box-drawing - are not matched unless a variation selector (U+FE0F) forces
# them into emoji presentation. A base + U+FE0F sequence counts once, not
# twice, and a flag (two regional indicators) counts once.
_BMP_EMOJI = "✅❌✨⭐⭕❗⚡❤⬆\U0001f004"
EMOJI = re.compile(
    "[\U0001f1e6-\U0001f1ff]{2}"
    "|[\U0001f300-\U0001faff" + _BMP_EMOJI + "]\\ufe0f?"
    "|[\\u2190-\\u2bff]\\ufe0f"
)


def load_text(path, force_markdown=False):
    if path and path != "-":
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
        is_markdown = path.lower().endswith((".md", ".markdown"))
    else:
        # sys.stdin decodes with the console's locale encoding (cp1252 on a
        # default Windows setup), which mangles UTF-8 em dashes, emoji, and
        # curly quotes into bytes no detector matches. Read the raw bytes
        # and decode as UTF-8 ourselves, same as the file path above. Fall
        # back to sys.stdin.read() for stand-ins like io.StringIO in tests
        # that have no underlying .buffer.
        buf = getattr(sys.stdin, "buffer", None)
        if buf is not None:
            text = buf.read().decode("utf-8-sig", errors="replace")
        else:
            text = sys.stdin.read()
        is_markdown = False
    if text.startswith("﻿"):
        text = text[1:]
    if force_markdown or is_markdown:
        text = strip_markdown_code(text)
    return text


def strip_markdown_code(text):
    """Blank out fenced code blocks and inline code so quoted code isn't
    scored as prose. Line numbers are preserved: every input line maps to an
    output line, code lines just come back empty."""
    out, fence = [], None
    for line in text.split("\n"):
        stripped = line.lstrip()
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            out.append("")
            continue
        opener = re.match(r"(`{3,}|~{3,})", stripped)
        if opener:
            fence = opener.group(1)
            out.append("")
            continue
        out.append(re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group()), line))
    return "\n".join(out)


def find_all(text_lower, needle):
    """Word-boundary match for a buzzword or phrase, tolerant of the line
    wraps git and editors put in the middle of a phrase. "as an ai" won't
    match inside "aide", "deep dive" won't match inside "deep diver", and
    a phrase split across a hard-wrapped line ("it's important to\\nnote")
    is still found. Returns (start, end) spans rather than just starts,
    since a wrapped match can be longer than the needle itself."""
    pattern = r"\b" + re.escape(needle).replace(r"\ ", r"\s+") + r"\b"
    return [(m.start(), m.end()) for m in re.finditer(pattern, text_lower)]


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def analyze(text):
    lower = text.lower()
    words = re.findall(r"[A-Za-z][A-Za-z'\-]+", text)
    wc = max(len(words), 1)
    per1k = lambda n: round(n * 1000.0 / wc, 1)

    # Collect buzzword and phrase hits as spans, then keep the longest
    # non-overlapping ones, so "let's dive into" is one hit rather than
    # "let's dive" plus "dive into", and "rich tapestry" doesn't also
    # count as "tapestry".
    spans = []
    for w in BUZZWORDS:
        spans += [(s, e, "buzz", w) for s, e in find_all(lower, w)]
    for p in PHRASES:
        spans += [(s, e, "phrase", p) for s, e in find_all(lower, p)]
    spans.sort(key=lambda h: (h[0], -h[1]))
    kept, last_end = [], -1
    for s, e, kind, key in spans:
        if s >= last_end:
            kept.append((s, kind, key))
            last_end = e

    def tally(which):
        counts = {}
        for s, kind, key in kept:
            if kind == which:
                counts.setdefault(key, []).append(s)
        rows = [(key, len(starts), [line_of(text, s) for s in starts[:5]])
                for key, starts in counts.items()]
        rows.sort(key=lambda x: -x[1])
        return rows

    buzz = tally("buzz")
    phr = tally("phrase")
    buzz_total = sum(n for _, n, _ in buzz)
    phr_total = sum(n for _, n, _ in phr)

    pat = []
    for label, rx, weight, hint in PATTERNS:
        matches = list(re.finditer(rx, text))
        if matches:
            pat.append((label, len(matches), weight, hint,
                        [line_of(text, m.start()) for m in matches[:5]]))

    emdash = len(re.findall(r"—", text))
    emoji = len(EMOJI.findall(text))

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    slens = [len(re.findall(r"[A-Za-z'\-]+", s)) for s in sentences if s.strip()]
    uniformity = None
    if len(slens) >= 5:
        mean = sum(slens) / len(slens)
        sd = (sum((x - mean) ** 2 for x in slens) / len(slens)) ** 0.5
        uniformity = round((sd / mean) if mean else 0, 2)

    raw = (buzz_total * 3) + (phr_total * 3)
    for _, n, weight, _, _ in pat:
        raw += n * weight
    emdash_excess = max(0, emdash - max(2, wc // 90))
    raw += emdash_excess
    raw += emoji * 2
    # repeated "**Term:** explanation" bullets - a formatting tell, whether
    # the list uses dash/star markers or is numbered ("1. **Term:** ...")
    bold_bullets = len(re.findall(
        r"(?m)^\s*(?:[-*+]|\d{1,3}[.)])\s+\*\*[^*\n]{1,45}?(?::\*\*|\*\*:)", text))
    if bold_bullets >= 3:
        raw += (bold_bullets - 2) * 2
    score = per1k(raw)
    if uniformity is not None and uniformity < 0.35:
        score += 8

    verdict = "looks human"
    if score >= 25:
        verdict = "reads as AI - needs a real rewrite"
    elif score >= 10:
        verdict = "some AI tells - worth a pass"

    return {
        "words": wc, "score_per_1k": score, "verdict": verdict,
        "buzzwords": buzz, "phrases": phr, "patterns": pat,
        "em_dashes": emdash, "em_dash_excess": emdash_excess, "emoji": emoji,
        "bold_label_bullets": bold_bullets, "sentence_uniformity_cv": uniformity,
    }


def report(r, quiet=False):
    out = [f"words: {r['words']}   AI-tell score: {r['score_per_1k']}/1k   -> {r['verdict']}"]
    if quiet:
        return "\n".join(out)
    if r["buzzwords"]:
        out.append("\nLLM buzzwords:")
        for w, n, lines in r["buzzwords"]:
            out.append(f"  {n:>2}x  {w:<18} (lines {', '.join(map(str, lines))})")
    if r["phrases"]:
        out.append("\nFiller phrases:")
        for p, n, lines in r["phrases"]:
            out.append(f'  {n:>2}x  "{p}" (lines {", ".join(map(str, lines))})')
    if r["patterns"]:
        out.append("\nConstructions:")
        for label, n, weight, hint, lines in r["patterns"]:
            tag = "" if weight else "  [style, not scored]"
            out.append(f"  {n:>2}x  {label}{tag} (lines {', '.join(map(str, lines))})")
            out.append(f"        -> {hint}")
    misc = []
    if r["em_dash_excess"]:
        misc.append(f"{r['em_dashes']} em dashes is dense for the length (vary the punctuation)")
    if r["emoji"]:
        misc.append(f"{r['emoji']} emoji (usually worth dropping in prose)")
    if r["sentence_uniformity_cv"] is not None and r["sentence_uniformity_cv"] < 0.35:
        misc.append(f"sentence lengths very even (cv={r['sentence_uniformity_cv']}) - vary the rhythm")
    if r.get("bold_label_bullets", 0) >= 3:
        misc.append(f"{r['bold_label_bullets']} '**Term:** ...' bullets - a formatting tell; write some as prose")
    if misc:
        out.append("\nRhythm & surface:")
        for m in misc:
            out.append(f"  - {m}")
    if not (r["buzzwords"] or r["phrases"] or r["patterns"] or misc):
        out.append("\nNothing flagged. Reads clean.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="unslop", description="Flag the AI tells in a piece of writing.")
    ap.add_argument("paths", nargs="*", default=["-"], metavar="path",
                    help="text files, or - for stdin (default: stdin)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="verdict line only")
    ap.add_argument("--markdown", action="store_true",
                    help="skip fenced/inline code when scoring (automatic for .md files)")
    ap.add_argument("--threshold", type=float, default=10.0,
                    help="score at/above which exit code is 1 (default 10)")
    ap.add_argument("--version", action="version", version=f"unslop {__version__}")
    args = ap.parse_args(argv)

    # Expand any glob argument ourselves. POSIX shells already do this
    # before we see argv, but PowerShell and cmd.exe never expand
    # wildcards, so "unslop docs/*.md" would otherwise reach open() as a
    # literal, nonexistent path on Windows.
    paths = []
    for p in (args.paths or ["-"]):
        if p != "-" and any(ch in p for ch in "*?["):
            matches = sorted(glob.glob(p))
            if not matches:
                print(f"unslop: {p}: no files match", file=sys.stderr)
                return 2
            paths.extend(matches)
        else:
            paths.append(p)

    results = []
    for p in paths:
        try:
            text = load_text(p, force_markdown=args.markdown)
        except OSError as exc:
            print(f"unslop: {p}: {exc.strerror or exc}", file=sys.stderr)
            return 2
        r = analyze(text)
        if p != "-":
            r["path"] = p
        results.append((p, r))

    if args.json:
        payload = results[0][1] if len(results) == 1 else [r for _, r in results]
        print(json.dumps(payload, indent=2))
    else:
        multi = len(results) > 1
        blocks = []
        for p, r in results:
            body = report(r, quiet=args.quiet)
            if multi and args.quiet:
                blocks.append(f"{p}: {body}")
            elif multi:
                blocks.append(f"== {p} ==\n{body}")
            else:
                blocks.append(body)
        print("\n".join(blocks) if (multi and args.quiet) else "\n\n".join(blocks))
    return 0 if all(r["score_per_1k"] < args.threshold for _, r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
