#!/usr/bin/env python3
"""Measure noslop's detection quality against the labeled corpus in eval/corpus/.

Runs the real analyze() over every sample and reports how well the scores
separate AI text from human text: detection rate at each verdict threshold,
false-positive rate on the human half, and AUC (the probability a random AI
sample outscores a random human one - 1.0 is perfect, 0.5 is a coin flip).

This is the calibration loop: change the engine, run this, and the numbers
say whether detection actually got better or just louder. CI runs it with
--check so a change that trades false positives for recall can't land quietly.

Usage (from the repo root):
  py eval/run_eval.py            # human-readable table
  py eval/run_eval.py --json     # machine-readable
  py eval/run_eval.py --check    # exit 1 if any CI floor is broken
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from noslop import analyze, analyze_code, strip_markdown_code  # noqa: E402

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus")

# CI floors. Deliberately below the measured numbers so ordinary drift passes
# and only a real regression fails; see eval/README.md for the measured state.
FLOORS = {
    # Raised in 0.9.0 after the new detectors + 4 new corpus samples (see
    # eval/README.md) moved AUC to 0.9752 and detection@10 to 89.5% without
    # moving either false-positive ceiling. Still sits below the measured
    # numbers so routine drift passes and only a real regression trips.
    "auc_min": 0.95,
    "detect_at_10_min": 0.85,   # share of AI samples scoring >= 10
    "human_fp_at_10_max": 0.10, # share of human samples scoring >= 10
    "human_fp_at_25_max": 0.0,  # no human sample may cross the hard verdict
}

# Code-mode floors, same contract as FLOORS but over code-ai/code-human.
# detect floor sits lower than prose on purpose: the corpus includes a
# terse agentic-style sample the literature says surface tells can't
# reliably catch (see eval/README.md), and pretending otherwise would just
# mean gaming the corpus.
FLOORS_CODE = {
    "auc_min": 0.95,
    "detect_at_10_min": 0.80,
    "human_fp_at_10_max": 0.10,
    "human_fp_at_25_max": 0.0,
}


def load_samples(kind):
    root = os.path.join(CORPUS, kind)
    rows = []
    for name in sorted(os.listdir(root)):
        if not name.endswith(".txt"):
            continue
        path = os.path.join(root, name)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        r = analyze(strip_markdown_code(text))
        rows.append({"file": name, "score": r["score_per_1k"], "words": r["words"],
                     "language": r["language"]})
    return rows


def load_code_samples(kind):
    root = os.path.join(CORPUS, kind)
    rows = []
    for name in sorted(os.listdir(root)):
        if name.endswith(".md"):
            continue
        path = os.path.join(root, name)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        ext = os.path.splitext(name)[1]
        r = analyze_code(text, ext=ext)
        rows.append({"file": name, "score": r["score_per_100"],
                     "sloc": r["sloc"], "language": r["code_language"]})
    return rows


def auc(ai_scores, human_scores):
    if not ai_scores or not human_scores:
        return None
    wins = 0.0
    for a in ai_scores:
        for h in human_scores:
            if a > h:
                wins += 1.0
            elif a == h:
                wins += 0.5
    return wins / (len(ai_scores) * len(human_scores))


def rate(scores, threshold):
    return sum(1 for s in scores if s >= threshold) / len(scores)


def summarize(ai, human, floors):
    ai_s = [r["score"] for r in ai]
    hu_s = [r["score"] for r in human]
    summary = {
        "ai_samples": len(ai), "human_samples": len(human),
        "auc": round(auc(ai_s, hu_s), 4),
        "ai_mean": round(sum(ai_s) / len(ai_s), 1),
        "ai_median": sorted(ai_s)[len(ai_s) // 2],
        "human_mean": round(sum(hu_s) / len(hu_s), 1),
        "human_max": max(hu_s),
        "detect_at_10": round(rate(ai_s, 10), 4),
        "detect_at_25": round(rate(ai_s, 25), 4),
        "human_fp_at_10": round(rate(hu_s, 10), 4),
        "human_fp_at_25": round(rate(hu_s, 25), 4),
    }
    failures = []
    if summary["auc"] < floors["auc_min"]:
        failures.append("AUC %.4f under floor %.2f" % (summary["auc"], floors["auc_min"]))
    if summary["detect_at_10"] < floors["detect_at_10_min"]:
        failures.append("detection@10 %.2f under floor %.2f"
                        % (summary["detect_at_10"], floors["detect_at_10_min"]))
    if summary["human_fp_at_10"] > floors["human_fp_at_10_max"]:
        failures.append("human FP@10 %.2f over ceiling %.2f"
                        % (summary["human_fp_at_10"], floors["human_fp_at_10_max"]))
    if summary["human_fp_at_25"] > floors["human_fp_at_25_max"]:
        failures.append("human FP@25 %.2f over ceiling %.2f"
                        % (summary["human_fp_at_25"], floors["human_fp_at_25_max"]))
    summary["floor_failures"] = failures
    return summary


def print_block(title, ai, human, summary, size_key, size_unit):
    print("%s - %d AI / %d human samples" % (title, len(ai), len(human)))
    print()
    for label, rows in (("AI", ai), ("HUMAN", human)):
        print("%s samples:" % label)
        for r in sorted(rows, key=lambda x: -x["score"]):
            print("  %6.1f  %-36s (%d %s, %s)"
                  % (r["score"], r["file"], r[size_key], size_unit, r["language"]))
        print()
    print("AUC (AI ranked above human): %.4f" % summary["auc"])
    print("AI    mean %.1f  median %.1f" % (summary["ai_mean"], summary["ai_median"]))
    print("human mean %.1f  max %.1f" % (summary["human_mean"], summary["human_max"]))
    print("detection  @10: %5.1f%%   @25: %5.1f%%"
          % (summary["detect_at_10"] * 100, summary["detect_at_25"] * 100))
    print("human FPs  @10: %5.1f%%   @25: %5.1f%%"
          % (summary["human_fp_at_10"] * 100, summary["human_fp_at_25"] * 100))
    for f in summary["floor_failures"]:
        print("FLOOR BROKEN: " + f)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if a CI floor is broken")
    args = ap.parse_args(argv)

    ai = load_samples("ai")
    human = load_samples("human")
    summary = summarize(ai, human, FLOORS)

    code_ai = load_code_samples("code-ai")
    code_human = load_code_samples("code-human")
    code_summary = summarize(code_ai, code_human, FLOORS_CODE)

    failures = summary["floor_failures"] + code_summary["floor_failures"]

    if args.json:
        print(json.dumps({"summary": summary, "ai": ai, "human": human,
                          "code_summary": code_summary,
                          "code_ai": code_ai, "code_human": code_human},
                         indent=2))
    else:
        print_block("noslop eval (prose)", ai, human, summary, "words", "words")
        print()
        print_block("noslop eval (code)", code_ai, code_human, code_summary,
                    "sloc", "sloc")

    if args.check and failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
