import contextlib
import io
import json
import os
import sys
import tempfile

import unslop


def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = unslop.main(argv)
    return code, buf.getvalue()


def run_cli_err(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = unslop.main(argv)
    return code, out.getvalue(), err.getvalue()


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


def test_word_boundary_avoids_substring_false_positives():
    # "as an ai" must not match inside "aide", "deep dive" must not match
    # inside "deep diver" - raw substring matching used to flag both
    r = unslop.analyze("He served as an aide to the senator for six years.")
    assert r["phrases"] == []
    assert r["verdict"] == "looks human"
    r = unslop.analyze("A deep diver explores caves most people never see.")
    assert r["buzzwords"] == []


def test_wrapped_phrase_is_still_caught():
    # git wraps commit bodies around 72 cols, so a phrase can be split
    # across a hard-wrapped line and should still be flagged
    r = unslop.analyze("It is important to\nnote that this changes the default.")
    assert any(p == "it is important to note" for p, _, _ in r["phrases"])


def test_isnt_flip_does_not_match_possessive_its():
    # "is not stored in its own file" is ordinary prose, not the
    # "it isn't X, it's Y" contrast flip
    r = unslop.analyze("The config is not stored in its own file anymore, it "
                        "moved to environment variables during setup.")
    assert r["patterns"] == []
    assert r["verdict"] == "looks human"


def test_isnt_flip_still_fires_on_real_contrast():
    r = unslop.analyze("This isn't a gimmick, it's the core feature of the release.")
    labels = [p[0] for p in r["patterns"]]
    assert any("it isn't X" in label for label in labels)
    r = unslop.analyze("This isn't a gimmick, it is the core feature of the release.")
    labels = [p[0] for p in r["patterns"]]
    assert any("it isn't X" in label for label in labels)


def test_numbered_bold_label_bullets_are_flagged():
    # the numbered "1. **Term:** ..." list is the same formatting tell as
    # the dash-bulleted one and should be caught the same way
    text = "1. **Speed:** fast\n2. **Safety:** safe\n3. **Scale:** grows\n4. **Cost:** cheap\n"
    r = unslop.analyze(text)
    assert r["bold_label_bullets"] == 4
    assert r["score_per_1k"] > 0


def test_stdin_decodes_as_utf8_regardless_of_console_encoding():
    # on a default Windows console sys.stdin decodes as cp1252, which
    # mangles UTF-8 em dashes and emoji into bytes nothing matches
    utf8_bytes = "an em dash — right here and a party \U0001f389 too".encode("utf-8")
    fake_stdin = io.TextIOWrapper(io.BytesIO(utf8_bytes), encoding="cp1252")
    old_stdin = sys.stdin
    sys.stdin = fake_stdin
    try:
        text = unslop.load_text("-")
    finally:
        sys.stdin = old_stdin
    r = unslop.analyze(text)
    assert r["em_dashes"] == 1
    assert r["emoji"] == 1


def test_stdin_without_buffer_falls_back_to_text_read():
    # a plain io.StringIO (as used in some test harnesses) has no .buffer
    old_stdin = sys.stdin
    sys.stdin = io.StringIO("plain text with no special encoding needs")
    try:
        text = unslop.load_text("-")
    finally:
        sys.stdin = old_stdin
    assert text == "plain text with no special encoding needs"


def test_utf8_bom_file_does_not_break_fence_detection():
    # a UTF-8 BOM glued to the opening fence used to stop the fence regex
    # from matching, so the whole code block got scored as prose
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "doc.md")
        with open(p, "wb") as fh:
            fh.write(b"\xef\xbb\xbf```\nwe delve into the robust tapestry\n```\n")
        code, out = run_cli([p])
        assert code == 0
        assert "delve" not in out


def test_missing_file_exits_cleanly_with_no_traceback():
    code, out, err = run_cli_err(["does-not-exist-at-all.txt"])
    assert code == 2
    assert out == ""
    assert "does-not-exist-at-all.txt" in err


def test_glob_argument_is_expanded():
    # PowerShell and cmd.exe never expand wildcards, so "unslop docs/*.md"
    # needs to work even when the shell hands us the literal glob
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.md")
        b = os.path.join(d, "b.md")
        for p in (a, b):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("Short and plain. Nothing fancy going on in this one.")
        code, out = run_cli([os.path.join(d, "*.md")])
        assert code == 0
        assert "a.md" in out and "b.md" in out


def test_glob_argument_matching_nothing_errors_cleanly():
    with tempfile.TemporaryDirectory() as d:
        code, out, err = run_cli_err([os.path.join(d, "*.md")])
        assert code == 2
        assert out == ""
        assert "no files match" in err


def run_cli_in(d, argv):
    old_cwd = os.getcwd()
    os.chdir(d)
    try:
        return run_cli(argv)
    finally:
        os.chdir(old_cwd)


def run_cli_err_in(d, argv):
    old_cwd = os.getcwd()
    os.chdir(d)
    try:
        return run_cli_err(argv)
    finally:
        os.chdir(old_cwd)


def test_json_output_has_stable_key_set():
    # analyze()'s return dict is unslop's only machine-readable contract;
    # a future rename of a key should fail this test as a reminder to bump
    # the version and note it, not slip out silently
    r = unslop.analyze("Plain sentence with nothing notable in it at all.")
    assert set(r.keys()) == unslop.JSON_SCHEMA_KEYS


def test_config_file_ignores_words_and_phrases():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, ".unslop.json"), "w", encoding="utf-8") as fh:
            json.dump({"ignore_words": ["robust"], "ignore_phrases": ["dive into"]}, fh)
        p = os.path.join(d, "a.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("This is robust. Let's dive into it. It's also comprehensive.")
        code, out = run_cli_in(d, ["a.md"])
        assert "robust" not in out
        assert "dive into" not in out
        assert "comprehensive" in out


def test_config_file_adds_extra_words():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, ".unslop.json"), "w", encoding="utf-8") as fh:
            json.dump({"extra_words": ["frobnicate"]}, fh)
        p = os.path.join(d, "a.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("Please frobnicate the widget before shipping it.")
        code, out = run_cli_in(d, ["a.md"])
        assert "frobnicate" in out


def test_no_config_flag_bypasses_config_file():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, ".unslop.json"), "w", encoding="utf-8") as fh:
            json.dump({"ignore_words": ["robust"]}, fh)
        p = os.path.join(d, "a.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("This is robust and nothing else.")
        code, out = run_cli_in(d, ["--no-config", "a.md"])
        assert "robust" in out


def test_explicit_config_path_missing_errors_cleanly():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("Plain text here.")
        code, out, err = run_cli_err(["--config", os.path.join(d, "nope.json"), p])
        assert code == 2
        assert "no such file" in err


def test_invalid_config_json_errors_cleanly():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, ".unslop.json"), "w", encoding="utf-8") as fh:
            fh.write("not json")
        p = os.path.join(d, "a.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("Plain text here.")
        code, out, err = run_cli_err_in(d, ["a.md"])
        assert code == 2
        assert "invalid JSON" in err


def test_exclude_flag_skips_matching_files():
    with tempfile.TemporaryDirectory() as d:
        slop = os.path.join(d, "slop.md")
        clean = os.path.join(d, "clean.md")
        with open(slop, "w", encoding="utf-8") as fh:
            fh.write("This is robust, comprehensive, and cutting-edge.")
        with open(clean, "w", encoding="utf-8") as fh:
            fh.write("Plain text with nothing notable going on here.")
        code, out = run_cli_in(d, ["--no-config", "--exclude", "slop.md", "slop.md", "clean.md"])
        assert code == 0
        assert "robust" not in out


def test_unslopignore_file_skips_matching_files():
    with tempfile.TemporaryDirectory() as d:
        slop = os.path.join(d, "slop.md")
        clean = os.path.join(d, "clean.md")
        with open(slop, "w", encoding="utf-8") as fh:
            fh.write("This is robust, comprehensive, and cutting-edge.")
        with open(clean, "w", encoding="utf-8") as fh:
            fh.write("Plain text with nothing notable going on here.")
        with open(os.path.join(d, ".unslopignore"), "w", encoding="utf-8") as fh:
            fh.write("slop.md\n")
        code, out = run_cli_in(d, ["--no-config", "slop.md", "clean.md"])
        assert code == 0
        assert "robust" not in out


def test_rdjson_emits_one_json_object_per_line():
    r = unslop.analyze("This is robust and comprehensive stuff here today.")
    lines = unslop.to_rdjsonl("a.md", r)
    assert len(lines) >= 2
    for line in lines:
        obj = json.loads(line)
        assert obj["location"]["path"] == "a.md"
        assert obj["severity"] in ("WARNING", "INFO")
        assert "message" in obj


def test_rdjson_cli_flag_outputs_valid_jsonlines():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("This is robust and comprehensive stuff here today.")
        code, out = run_cli_in(d, ["--no-config", "--rdjson", "a.md"])
        lines = [l for l in out.splitlines() if l.strip()]
        assert len(lines) >= 1
        for line in lines:
            json.loads(line)


# ---- language packs ----

def test_spanish_slop_is_detected_and_flagged():
    r = unslop.analyze(
        "En el vasto mundo del desarrollo, es importante destacar que nuestra "
        "plataforma integral ofrece una experiencia fluida y sin fisuras. "
        "Sumérgete en un rico tapiz de posibilidades que te permitirá "
        "desbloquear todo tu potencial en el panorama digital actual."
    )
    assert r["language"] == "es"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "tapiz" for w, _, _ in r["buzzwords"])
    assert any(p == "es importante destacar" for p, _, _ in r["phrases"])


def test_german_slop_is_detected_and_flagged():
    r = unslop.analyze(
        "In der heutigen schnelllebigen Welt ist es wichtig zu beachten, dass "
        "unsere nahtlose Plattform bahnbrechende Synergien nutzt, um ein "
        "ganzheitliches Erlebnis zu bieten und Ihr volles Potenzial zu "
        "entfesseln. Das ist nicht nur ein Werkzeug, sondern ein echter "
        "Paradigmenwechsel für die Arbeit von morgen."
    )
    assert r["language"] == "de"
    assert r["score_per_1k"] >= 25
    assert any(w == "nahtlose" for w, _, _ in r["buzzwords"])
    assert any("sondern" in label for label, _, _, _, _ in r["patterns"])


def test_clean_spanish_reads_human():
    r = unslop.analyze(
        "Ayer se me rompió la cadena de la bici camino al trabajo. La arreglé "
        "con la herramienta que llevo años cargando sin usar. Tardé veinte "
        "minutos y llegué con las manos llenas de grasa, pero llegué a tiempo "
        "y nadie se dio cuenta de nada en la oficina."
    )
    assert r["language"] == "es"
    assert r["verdict"] == "looks human"


def test_unknown_language_falls_back_honestly():
    r = unslop.analyze(
        "Вчера сломалась цепь на велосипеде по дороге на работу. Починил её "
        "выжимкой, которую вожу с собой уже много лет и ни разу не использовал. "
        "Потратил двадцать минут и приехал с чёрными от смазки руками."
    )
    assert r["language"] == "en"
    assert r["language_source"] == "fallback"
    # the Unicode tokenizer still counts these words, so per-1k math stays sane
    assert r["words"] > 15


def test_forced_lang_overrides_detection():
    r = unslop.analyze(
        "The quick brown fox jumps over the lazy dog again and again today.",
        lang="es",
    )
    assert r["language"] == "es"
    assert r["language_source"] == "forced"


def test_dialogue_dashes_not_flagged_in_spanish():
    dialogue = (
        "—¿Vienes mañana a la obra? —preguntó Ana desde la puerta.\n"
        "—No lo sé —dijo Pedro—. El tren sale temprano y la reunión con los "
        "del banco es a las nueve, pero si termino antes me paso un rato por "
        "allí para ver cómo va todo aquello.\n"
        "Ella asintió sin decir nada y cerró la puerta despacio."
    )
    r = unslop.analyze(dialogue)
    assert r["language"] == "es"
    # five dialogue dashes: over the English allowance, inside the Spanish one
    assert r["em_dashes"] == 5
    assert r["em_dash_excess"] == 0
    forced_en = unslop.analyze(dialogue, lang="en")
    assert forced_en["em_dash_excess"] > 0


def test_lang_flag_forces_pack_via_cli():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.txt")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("Plain English words that mention nothing special at all.")
        code, out = run_cli_in(d, ["--no-config", "--json", "--lang", "de", "a.txt"])
        r = json.loads(out)
        assert r["language"] == "de"
        assert r["language_source"] == "forced"


def test_curly_apostrophe_phrases_are_caught():
    r = unslop.analyze("It’s important to note that we should move on quickly.")
    assert any(p == "it's important to note" for p, _, _ in r["phrases"])
