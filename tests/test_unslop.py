import contextlib
import io
import json
import os
import tempfile

import unslop


def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = unslop.main(argv)
    return code, buf.getvalue()


def test_ai_sample_flags_high():
    ai = ("In today's world, it's important to note that our robust, cutting-edge "
          "solution seamlessly leverages a comprehensive approach. This isn't just a "
          "tool, it's a testament to innovation. Let's dive into the myriad ways it "
          "can elevate your workflow and unlock a rich tapestry of possibilities.")
    r = unslop.analyze(ai)
    assert r["score_per_1k"] >= 25
    assert "AI" in r["verdict"]


def test_clean_prose_reads_human():
    clean = ("The buffer gets swapped twice, so the saved file ends up backwards. I "
             "moved the swap onto a copy. On-screen output doesn't change, and the "
             "file is correct now. I tested it against a full dump and it round-trips.")
    r = unslop.analyze(clean)
    assert r["score_per_1k"] < 10
    assert r["verdict"] == "looks human"


def test_check_marks_are_not_emoji():
    # check/cross marks belong in tables and must not be flagged as emoji
    r = unslop.analyze("Result: pass ✓ or fail ✗, marked in the column.")
    assert r["emoji"] == 0


def test_emoji_variation_sequence_counts_once():
    # a heart written as base + U+FE0F is one emoji, not two
    r = unslop.analyze("I ❤️ this")
    assert r["emoji"] == 1


def test_flag_counts_once():
    # a flag is a pair of regional indicators; one flag, one emoji
    r = unslop.analyze("Go team \U0001f1fa\U0001f1f8")
    assert r["emoji"] == 1


def test_vs16_forces_emoji_presentation():
    # bare warning sign is a plain glyph; with U+FE0F it's an emoji
    assert unslop.analyze("⚠ careful here")["emoji"] == 0
    assert unslop.analyze("⚠️ careful here")["emoji"] == 1


def test_not_just_but_is_flagged():
    r = unslop.analyze("This is not just fast, but also cheap and simple to run.")
    labels = [p[0] for p in r["patterns"]]
    assert any("not just" in label for label in labels)


def test_overlapping_hits_count_once():
    # "let's dive into" is one act of diving, and "rich tapestry"
    # shouldn't also count as "tapestry"
    r = unslop.analyze("Let's dive into the rich tapestry of options.")
    assert sum(n for _, n, _ in r["phrases"]) == 1
    assert sum(n for _, n, _ in r["buzzwords"]) == 1


def test_bold_label_bullets_are_flagged():
    # both forms of the "**Term:** explanation" list tell
    inside = "- **Speed:** fast\n- **Safety:** safe\n- **Scale:** grows\n- **Cost:** cheap\n"
    after = "- **Speed**: fast\n- **Safety**: safe\n- **Scale**: grows\n"
    assert unslop.analyze(inside)["bold_label_bullets"] == 4
    assert unslop.analyze(after)["bold_label_bullets"] == 3


def test_plain_bold_bullets_are_not_flagged():
    # a bullet that just bolds a word (no colon) is fine, not the label tell
    r = unslop.analyze("- **Note** the thing runs fast\n- another normal bullet here\n")
    assert r["bold_label_bullets"] == 0


def test_empty_input_is_safe():
    r = unslop.analyze("")
    assert r["words"] == 1
    assert r["verdict"] == "looks human"


def test_strip_markdown_code_blanks_fences_and_inline():
    text = "intro line\n```\ndelve into the robust tapestry\n```\nuse `leverage` here\n"
    stripped = unslop.strip_markdown_code(text)
    # same number of lines, code content gone
    assert stripped.count("\n") == text.count("\n")
    r = unslop.analyze(stripped)
    assert r["buzzwords"] == []
    assert r["phrases"] == []


def test_strip_markdown_code_keeps_line_numbers():
    text = "```\ncode\ncode\n```\nwe delve here\n"
    r = unslop.analyze(unslop.strip_markdown_code(text))
    assert r["buzzwords"][0][2] == [5]


def test_unclosed_fence_blanks_to_end():
    stripped = unslop.strip_markdown_code("ok\n```\ndelve\nrobust\n")
    assert unslop.analyze(stripped)["buzzwords"] == []


def test_markdown_files_skip_code_automatically():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "doc.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("plain sentence here\n```\ndelve robust seamless leverage\n```\n")
        code, out = run_cli([p])
        assert code == 0
        assert "delve" not in out


def test_multiple_paths_and_exit_code():
    with tempfile.TemporaryDirectory() as d:
        clean = os.path.join(d, "clean.txt")
        slop = os.path.join(d, "slop.txt")
        with open(clean, "w", encoding="utf-8") as fh:
            fh.write("The parser broke on empty rows. I skip them now and log a count.")
        with open(slop, "w", encoding="utf-8") as fh:
            fh.write("Let's delve into this robust, seamless, cutting-edge tapestry of synergy.")
        code, out = run_cli([clean, slop])
        assert code == 1
        assert "clean.txt" in out and "slop.txt" in out
        code, _ = run_cli([clean])
        assert code == 0


def test_json_single_is_object_and_multi_is_array():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.txt")
        b = os.path.join(d, "b.txt")
        for p in (a, b):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("Short and plain. Nothing fancy going on in this one.")
        _, out = run_cli([a, "--json"])
        single = json.loads(out)
        assert isinstance(single, dict) and single["path"] == a
        _, out = run_cli([a, b, "--json"])
        both = json.loads(out)
        assert isinstance(both, list) and [r["path"] for r in both] == [a, b]


def test_threshold_flag():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "mild.txt")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("We delve into the details of the release schedule for the next "
                     "quarter and how the rollout is going to be sequenced across teams.")
        strict, _ = run_cli([p])
        lax, _ = run_cli([p, "--threshold", "200"])
        assert strict == 1
        assert lax == 0
