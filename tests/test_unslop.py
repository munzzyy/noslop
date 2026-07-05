import unslop


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
    r = unslop.analyze("Result: pass or fail, marked with a check or an x in the column.")
    assert r["emoji"] == 0


def test_not_just_but_is_flagged():
    r = unslop.analyze("This is not just fast, but also cheap and simple to run.")
    labels = [p[0] for p in r["patterns"]]
    assert any("not just" in label for label in labels)


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
