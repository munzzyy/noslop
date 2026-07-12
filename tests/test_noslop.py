import contextlib
import io
import json
import os
import re
import sys
import tempfile

import noslop


def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = noslop.main(argv)
    return code, buf.getvalue()


def run_cli_err(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = noslop.main(argv)
    return code, out.getvalue(), err.getvalue()


def test_ai_sample_flags_high():
    ai = ("In today's world, it's important to note that our robust, cutting-edge "
          "solution seamlessly leverages a comprehensive approach. This isn't just a "
          "tool, it's a testament to innovation. Let's dive into the myriad ways it "
          "can elevate your workflow and unlock a rich tapestry of possibilities.")
    r = noslop.analyze(ai)
    assert r["score_per_1k"] >= 25
    assert "AI" in r["verdict"]


def test_clean_prose_reads_human():
    clean = ("The buffer gets swapped twice, so the saved file ends up backwards. I "
             "moved the swap onto a copy. On-screen output doesn't change, and the "
             "file is correct now. I tested it against a full dump and it round-trips.")
    r = noslop.analyze(clean)
    assert r["score_per_1k"] < 10
    assert r["verdict"] == "looks human"


def test_check_marks_are_not_emoji():
    # check/cross marks belong in tables and must not be flagged as emoji
    r = noslop.analyze("Result: pass ✓ or fail ✗, marked in the column.")
    assert r["emoji"] == 0


def test_emoji_variation_sequence_counts_once():
    # a heart written as base + U+FE0F is one emoji, not two
    r = noslop.analyze("I ❤️ this")
    assert r["emoji"] == 1


def test_flag_counts_once():
    # a flag is a pair of regional indicators; one flag, one emoji
    r = noslop.analyze("Go team \U0001f1fa\U0001f1f8")
    assert r["emoji"] == 1


def test_vs16_forces_emoji_presentation():
    # bare warning sign is a plain glyph; with U+FE0F it's an emoji
    assert noslop.analyze("⚠ careful here")["emoji"] == 0
    assert noslop.analyze("⚠️ careful here")["emoji"] == 1


def test_not_just_but_is_flagged():
    r = noslop.analyze("This is not just fast, but also cheap and simple to run.")
    labels = [p[0] for p in r["patterns"]]
    assert any("not just" in label for label in labels)


def test_overlapping_hits_count_once():
    # "let's dive into" is one act of diving, and "rich tapestry"
    # shouldn't also count as "tapestry"
    r = noslop.analyze("Let's dive into the rich tapestry of options.")
    assert sum(n for _, n, _ in r["phrases"]) == 1
    assert sum(n for _, n, _ in r["buzzwords"]) == 1


def test_bold_label_bullets_are_flagged():
    # both forms of the "**Term:** explanation" list tell
    inside = "- **Speed:** fast\n- **Safety:** safe\n- **Scale:** grows\n- **Cost:** cheap\n"
    after = "- **Speed**: fast\n- **Safety**: safe\n- **Scale**: grows\n"
    assert noslop.analyze(inside)["bold_label_bullets"] == 4
    assert noslop.analyze(after)["bold_label_bullets"] == 3


def test_plain_bold_bullets_are_not_flagged():
    # a bullet that just bolds a word (no colon) is fine, not the label tell
    r = noslop.analyze("- **Note** the thing runs fast\n- another normal bullet here\n")
    assert r["bold_label_bullets"] == 0


def test_empty_input_is_safe():
    r = noslop.analyze("")
    assert r["words"] == 1
    assert r["verdict"] == "looks human"


def test_strip_markdown_code_blanks_fences_and_inline():
    text = "intro line\n```\ndelve into the robust tapestry\n```\nuse `leverage` here\n"
    stripped = noslop.strip_markdown_code(text)
    # same number of lines, code content gone
    assert stripped.count("\n") == text.count("\n")
    r = noslop.analyze(stripped)
    assert r["buzzwords"] == []
    assert r["phrases"] == []


def test_strip_markdown_code_keeps_line_numbers():
    text = "```\ncode\ncode\n```\nwe delve here\n"
    r = noslop.analyze(noslop.strip_markdown_code(text))
    assert r["buzzwords"][0][2] == [5]


def test_unclosed_fence_blanks_to_end():
    stripped = noslop.strip_markdown_code("ok\n```\ndelve\nrobust\n")
    assert noslop.analyze(stripped)["buzzwords"] == []


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
    r = noslop.analyze("He served as an aide to the senator for six years.")
    assert r["phrases"] == []
    assert r["verdict"] == "looks human"
    r = noslop.analyze("A deep diver explores caves most people never see.")
    assert r["buzzwords"] == []


def test_wrapped_phrase_is_still_caught():
    # git wraps commit bodies around 72 cols, so a phrase can be split
    # across a hard-wrapped line and should still be flagged
    r = noslop.analyze("It is important to\nnote that this changes the default.")
    assert any(p == "it is important to note" for p, _, _ in r["phrases"])


def test_isnt_flip_does_not_match_possessive_its():
    # "is not stored in its own file" is ordinary prose, not the
    # "it isn't X, it's Y" contrast flip
    r = noslop.analyze("The config is not stored in its own file anymore, it "
                        "moved to environment variables during setup.")
    assert r["patterns"] == []
    assert r["verdict"] == "looks human"


def test_isnt_flip_still_fires_on_real_contrast():
    r = noslop.analyze("This isn't a gimmick, it's the core feature of the release.")
    labels = [p[0] for p in r["patterns"]]
    assert any("it isn't X" in label for label in labels)
    r = noslop.analyze("This isn't a gimmick, it is the core feature of the release.")
    labels = [p[0] for p in r["patterns"]]
    assert any("it isn't X" in label for label in labels)


def test_numbered_bold_label_bullets_are_flagged():
    # the numbered "1. **Term:** ..." list is the same formatting tell as
    # the dash-bulleted one and should be caught the same way
    text = "1. **Speed:** fast\n2. **Safety:** safe\n3. **Scale:** grows\n4. **Cost:** cheap\n"
    r = noslop.analyze(text)
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
        text = noslop.load_text("-")
    finally:
        sys.stdin = old_stdin
    r = noslop.analyze(text)
    assert r["em_dashes"] == 1
    assert r["emoji"] == 1


def test_stdin_without_buffer_falls_back_to_text_read():
    # a plain io.StringIO (as used in some test harnesses) has no .buffer
    old_stdin = sys.stdin
    sys.stdin = io.StringIO("plain text with no special encoding needs")
    try:
        text = noslop.load_text("-")
    finally:
        sys.stdin = old_stdin
    assert text == "plain text with no special encoding needs"


def test_bare_run_on_a_tty_says_it_is_waiting_on_stdin():
    # `noslop` with no arguments on an interactive terminal blocks on stdin,
    # which looks like a hang without a hint - so one goes to stderr.
    class FakeTty(io.StringIO):
        def isatty(self):
            return True

    old_stdin = sys.stdin
    sys.stdin = FakeTty("short and plain enough to read fine")
    try:
        code, out, err = run_cli_err([])
    finally:
        sys.stdin = old_stdin
    assert code == 0
    assert "reading from stdin" in err
    assert "reading from stdin" not in out


def test_piped_stdin_gets_no_tty_hint():
    # the hint is for interactive runs only; a pipe stays quiet on stderr
    old_stdin = sys.stdin
    sys.stdin = io.StringIO("short and plain enough to read fine")
    try:
        code, out, err = run_cli_err([])
    finally:
        sys.stdin = old_stdin
    assert code == 0
    assert err == ""


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
    # PowerShell and cmd.exe never expand wildcards, so "noslop docs/*.md"
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
    # analyze()'s return dict is noslop's only machine-readable contract;
    # a future rename of a key should fail this test as a reminder to bump
    # the version and note it, not slip out silently
    r = noslop.analyze("Plain sentence with nothing notable in it at all.")
    assert set(r.keys()) == noslop.JSON_SCHEMA_KEYS


def test_config_file_ignores_words_and_phrases():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, ".noslop.json"), "w", encoding="utf-8") as fh:
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
        with open(os.path.join(d, ".noslop.json"), "w", encoding="utf-8") as fh:
            json.dump({"extra_words": ["frobnicate"]}, fh)
        p = os.path.join(d, "a.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("Please frobnicate the widget before shipping it.")
        code, out = run_cli_in(d, ["a.md"])
        assert "frobnicate" in out


def test_no_config_flag_bypasses_config_file():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, ".noslop.json"), "w", encoding="utf-8") as fh:
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
        with open(os.path.join(d, ".noslop.json"), "w", encoding="utf-8") as fh:
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


def test_noslopignore_file_skips_matching_files():
    with tempfile.TemporaryDirectory() as d:
        slop = os.path.join(d, "slop.md")
        clean = os.path.join(d, "clean.md")
        with open(slop, "w", encoding="utf-8") as fh:
            fh.write("This is robust, comprehensive, and cutting-edge.")
        with open(clean, "w", encoding="utf-8") as fh:
            fh.write("Plain text with nothing notable going on here.")
        with open(os.path.join(d, ".noslopignore"), "w", encoding="utf-8") as fh:
            fh.write("slop.md\n")
        code, out = run_cli_in(d, ["--no-config", "slop.md", "clean.md"])
        assert code == 0
        assert "robust" not in out


def test_rdjson_emits_one_json_object_per_line():
    r = noslop.analyze("This is robust and comprehensive stuff here today.")
    lines = noslop.to_rdjsonl("a.md", r)
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
    r = noslop.analyze(
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
    r = noslop.analyze(
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
    r = noslop.analyze(
        "Ayer se me rompió la cadena de la bici camino al trabajo. La arreglé "
        "con la herramienta que llevo años cargando sin usar. Tardé veinte "
        "minutos y llegué con las manos llenas de grasa, pero llegué a tiempo "
        "y nadie se dio cuenta de nada en la oficina."
    )
    assert r["language"] == "es"
    assert r["verdict"] == "looks human"


def test_unknown_language_falls_back_honestly():
    # Greek has no pack (see the drop rationale next to LANGUAGES) so it's a
    # clean stand-in for "a real language this tool has never heard of" -
    # disjoint script from every pack here, ordinary space-separated words.
    r = noslop.analyze(
        "Χθες το βράδυ έσπασε η αλυσίδα του ποδηλάτου στον δρόμο για τη "
        "δουλειά. Το επισκεύασα με το εργαλείο που κουβαλάω εδώ και χρόνια "
        "αλλά δεν είχα ποτέ χρησιμοποιήσει. Μου πήρε είκοσι λεπτά και "
        "έφτασα με τα χέρια μαύρα από το λάδι, αλλά στην ώρα μου."
    )
    assert r["language"] == "en"
    assert r["language_source"] == "fallback"
    # the Unicode tokenizer still counts these words, so per-1k math stays sane
    assert r["words"] > 15


def test_forced_lang_overrides_detection():
    r = noslop.analyze(
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
    r = noslop.analyze(dialogue)
    assert r["language"] == "es"
    # five dialogue dashes: over the English allowance, inside the Spanish one
    assert r["em_dashes"] == 5
    assert r["em_dash_excess"] == 0
    forced_en = noslop.analyze(dialogue, lang="en")
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
    r = noslop.analyze("It’s important to note that we should move on quickly.")
    assert any(p == "it's important to note" for p, _, _ in r["phrases"])


# ---- nine more language packs: ru, uk, pl, cs, tr, sv, ro, hu, fi ----

def test_russian_slop_is_detected_and_flagged():
    r = noslop.analyze(
        "В современном мире важно отметить, что наша комплексная платформа "
        "использует передовые технологии, чтобы обеспечить поистине "
        "бесшовный опыт. Давайте погрузимся в мир безграничных "
        "возможностей, которые помогут раскрыть потенциал каждой команды. "
        "Это не только инструмент, но и полноценная экосистема, которая "
        "играет ключевую роль в трансформации бизнеса."
    )
    assert r["language"] == "ru"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "бесшовный" for w, _, _ in r["buzzwords"])
    assert any(p == "важно отметить" for p, _, _ in r["phrases"])
    assert any("не только" in label for label, _, _, _, _ in r["patterns"])


def test_clean_russian_reads_human():
    r = noslop.analyze(
        "Вчера вечером сломался холодильник на кухне. Компрессор гудел все "
        "громче, а потом затих совсем. Вызвал мастера, он приехал через два "
        "часа и сказал, что дело в реле. Заменили деталь, обошлось в "
        "полторы тысячи рублей."
    )
    assert r["language"] == "ru"
    assert r["verdict"] == "looks human"


def test_dialogue_dashes_not_flagged_in_russian():
    # Cyrillic literary convention opens a line of dialogue with the dash -
    # and also uses it as a zero-copula substitute - far more than English
    # prose does, so Russian gets the same wide allowance as Spanish.
    dialogue = (
        "— Ты придёшь завтра на стройку? — спросила Анна от двери.\n"
        "— Не знаю — сказал Пётр. — Поезд отправляется рано, а встреча с "
        "банком в девять, но если закончу пораньше, заскочу посмотреть, как "
        "там идут дела.\n"
        "Она кивнула, ничего не сказала и медленно закрыла дверь."
    )
    r = noslop.analyze(dialogue)
    assert r["language"] == "ru"
    assert r["em_dashes"] == 5
    assert r["em_dash_excess"] == 0
    forced_en = noslop.analyze(dialogue, lang="en")
    assert forced_en["em_dash_excess"] > 0


def test_ukrainian_slop_is_detected_and_flagged():
    r = noslop.analyze(
        "У сучасному світі важливо зазначити, що наша комплексна платформа "
        "використовує передові технології, щоб забезпечити по-справжньому "
        "безшовний досвід. Давайте зануримося у світ, де на команди "
        "чекають безмежні можливості, які допоможуть розкрити потенціал "
        "кожного співробітника. Це не тільки інструмент, а й повноцінна "
        "екосистема, яка відіграє ключову роль у трансформації бізнесу."
    )
    assert r["language"] == "uk"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "безмежні можливості" for w, _, _ in r["buzzwords"])
    assert any(p == "важливо зазначити" for p, _, _ in r["phrases"])
    assert any("не тільки" in label for label, _, _, _, _ in r["patterns"])


def test_polish_slop_is_detected_and_flagged():
    r = noslop.analyze(
        "W dzisiejszym dynamicznie zmieniającym się świecie warto "
        "zauważyć, że nasza platforma jest kompleksowa, solidna i "
        "przełomowa. Zanurzmy się w świat możliwości i pomóżmy odblokować "
        "potencjał każdego zespołu. To nie tylko narzędzie, ale i "
        "prawdziwy kamień węgielny naszej strategii cyfrowej."
    )
    assert r["language"] == "pl"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "kamień węgielny" for w, _, _ in r["buzzwords"])
    assert any(p == "warto zauważyć" for p, _, _ in r["phrases"])
    assert any("nie tylko" in label for label, _, _, _, _ in r["patterns"])


def test_clean_polish_reads_human():
    r = noslop.analyze(
        "Sąsiad w końcu naprawił płot, który krzywił się od tamtej burzy w "
        "lutym. Zajęło mu to trzy soboty i musiał dwa razy kupować nowe "
        "deski, bo źle zmierzył za pierwszym razem. Wczoraj płot stał już "
        "prosto, a dziś rano na górze siedział kot."
    )
    assert r["language"] == "pl"
    assert r["verdict"] == "looks human"


def test_czech_slop_is_detected_and_flagged():
    r = noslop.analyze(
        "V dnešním uspěchaném světě je důležité poznamenat, že naše "
        "platforma je komplexní, robustní a průlomová. Pojďme prozkoumat, "
        "co digitální krajina plná možností nabízí, a pomozme odemknout "
        "potenciál každého týmu. Nejen že šetří čas, ale i otevírá nové "
        "možnosti pro celou firmu."
    )
    assert r["language"] == "cs"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "digitální krajina" for w, _, _ in r["buzzwords"])
    assert any(p == "je důležité poznamenat" for p, _, _ in r["phrases"])
    assert any("nejen" in label for label, _, _, _, _ in r["patterns"])


def test_turkish_slop_is_detected_and_flagged():
    r = noslop.analyze(
        "Günümüzün hızlı dünyasında önemle belirtmek gerekir ki "
        "platformumuz kapsamlı, sorunsuz ve bütünsel bir deneyim sunuyor. "
        "Hadi dalalım ve potansiyelinizi ortaya çıkarın! Bu sadece bir "
        "araç değil, aynı zamanda güçlü bir araç."
    )
    assert r["language"] == "tr"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "sorunsuz" for w, _, _ in r["buzzwords"])
    assert any(p == "günümüzün hızlı dünyasında" for p, _, _ in r["phrases"])
    assert any("sadece" in label for label, _, _, _, _ in r["patterns"])


def test_turkish_suffix_hedge_is_caught():
    # Turkish's "can/may" is the -ebilir/-abilir suffix, not a standalone
    # word like English "may" - the hedge pattern matches the suffix itself
    # rather than pretending Turkish has a separate modal word for it.
    # lang="tr" is forced because this one short sentence isn't enough
    # Turkish stop-word coverage to auto-detect on its own; the detection
    # side is already covered by test_turkish_slop_is_detected_and_flagged.
    r = noslop.analyze(
        "Bu çözüm hızlıca uygulanabilir ve işe yarayabilir.", lang="tr"
    )
    labels = [p[0] for p in r["patterns"]]
    assert any("ebilir" in label for label in labels)


def test_swedish_slop_is_detected_and_flagged():
    # "Det är viktigt att notera" opens the clause on purpose: fronting an
    # adverbial like "i dagens värld" first would trigger Swedish V2 word
    # order ("värld ÄR DET viktigt", subject-verb inverted) and the listed
    # phrase - written in normal, non-inverted order - would silently miss.
    r = noslop.analyze(
        "Det är viktigt att notera att vår plattform, i dagens "
        "snabbrörliga värld, är omfattande, robust och banbrytande. Dyk "
        "djupare och frigör din potential! Detta är inte bara ett verktyg "
        "utan också en hörnsten i er digitala strategi."
    )
    assert r["language"] == "sv"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "hörnsten" for w, _, _ in r["buzzwords"])
    assert any(p == "det är viktigt att notera" for p, _, _ in r["phrases"])
    assert any("inte bara" in label for label, _, _, _, _ in r["patterns"])


def test_romanian_slop_is_detected_and_flagged():
    r = noslop.analyze(
        "În lumea de azi în ritm alert, este important de menționat că "
        "platforma noastră este cuprinzătoare și revoluționară. "
        "Scufundă-te în oceanul de posibilități nelimitate și "
        "deblochează-ți potențialul! Nu doar că economisești timp, ci și "
        "deschizi noi orizonturi pentru echipa ta."
    )
    assert r["language"] == "ro"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "posibilități nelimitate" for w, _, _ in r["buzzwords"])
    assert any(p == "este important de menționat" for p, _, _ in r["phrases"])
    assert any("nu doar" in label for label, _, _, _, _ in r["patterns"])


def test_hungarian_slop_is_detected_and_flagged():
    r = noslop.analyze(
        "Napjaink rohanó világában fontos megjegyezni, hogy platformunk "
        "átfogó, robusztus és forradalmi. Merülj el és szabadítsd fel a "
        "benned rejlő potenciált! Ez nem csak egy eszköz, hanem valódi "
        "mérföldkő a stratégiánkban."
    )
    assert r["language"] == "hu"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "mérföldkő" for w, _, _ in r["buzzwords"])
    assert any(p == "fontos megjegyezni" for p, _, _ in r["phrases"])
    assert any("nem csak" in label for label, _, _, _, _ in r["patterns"])


def test_hungarian_ships_three_patterns_not_four():
    # Hungarian doesn't split "not just X but Y" and "isn't X it's Y" into
    # two separate idioms - both lean on "nem X, hanem Y" with csak/is as
    # an optional intensifier, so a forced second flip pattern would just
    # double-count the same sentence. See the comment on the hu pack.
    assert len(noslop.LANGUAGES["hu"]["patterns"]) == 3


def test_finnish_slop_is_detected_and_flagged():
    r = noslop.analyze(
        "Nykypäivän nopeatempoisessa maailmassa on tärkeää huomioida, että "
        "alustamme on kattava, saumaton ja mullistava. Sukella syvemmälle "
        "ja vapauta potentiaalisi! Tämä ei ole vain työkalu, vaan "
        "korvaamaton kulmakivi strategiassamme."
    )
    assert r["language"] == "fi"
    assert r["language_source"] == "detected"
    assert r["score_per_1k"] >= 25
    assert any(w == "korvaamaton" for w, _, _ in r["buzzwords"])
    assert any(p == "on tärkeää huomioida" for p, _, _ in r["phrases"])
    assert any("vaan" in label for label, _, _, _, _ in r["patterns"])


# ---- 0.7.0: chat-UI artifacts ----

def test_oaicite_artifact_forces_hard_verdict():
    text = (
        "Quarterly numbers were fine. Revenue grew four percent on stable "
        "costs, and the board approved the plan without much debate "
        ":contentReference[oaicite:0]{index=0}. Everything else about this "
        "paragraph is deliberately plain so nothing but the artifact fires. "
    ) * 8  # long text: per-1k dilution would otherwise bury the artifact
    r = noslop.analyze(text)
    assert r["ai_artifacts"]
    assert r["score_per_1k"] >= 25
    assert "AI" in r["verdict"]


def test_contentreference_block_counts_once_not_twice():
    r = noslop.analyze("Sales rose :contentReference[oaicite:3]{index=3} again.")
    assert sum(n for _, n, _ in r["ai_artifacts"]) == 1


def test_chatgpt_tracking_param_is_an_artifact():
    r = noslop.analyze("See https://example.com/a?utm_source=chatgpt.com for more.")
    assert r["ai_artifacts"]
    assert "AI" in r["verdict"]


def test_plain_urls_are_not_artifacts():
    r = noslop.analyze("See https://example.com/a?utm_source=newsletter for more. "
                       "The site tracks campaigns like most marketing sites do.")
    assert r["ai_artifacts"] == []


def test_artifact_at_offset_zero_still_counts():
    # Regression: the merge sentinel used to swallow a span at offset 0.
    r = noslop.analyze("oaicite residue opens this very text and the rest "
                       "of the passage is deliberately plain filler prose.")
    assert sum(n for _, n, _ in r["ai_artifacts"]) == 1
    assert "AI" in r["verdict"]


def test_template_placeholders_are_not_artifacts():
    # Humans write mail-merge placeholders on purpose.
    r = noslop.analyze("Dear [Insert Name], thank you for applying. Reply "
                       "to [insert your email] with two references, please.")
    assert r["ai_artifacts"] == []


def test_curly_apostrophe_split_flip_is_caught():
    r = noslop.analyze("The problem isn’t the tooling. It’s the culture "
                       "around the tooling that nobody wants to name.")
    assert any("split flip" in label for label, _, _, _, _ in r["patterns"])


def test_single_split_flip_reports_but_does_not_score():
    r = noslop.analyze("The county says it is a staffing problem. It isn't "
                       "a staffing problem. It's a software problem that "
                       "nobody budgeted for, and everyone in the building "
                       "knows it by now.")
    assert any("split flip" in label for label, _, _, _, _ in r["patterns"])
    assert r["score_per_1k"] == 0.0


def test_single_ing_closer_reports_but_does_not_score():
    r = noslop.analyze("The bridge opened in 1932, reflecting the city's "
                       "ambitions at the time. Repairs began within a "
                       "decade and never really stopped after that.")
    assert any("closer" in label for label, _, _, _, _ in r["patterns"])
    assert r["score_per_1k"] == 0.0


def test_ing_closer_does_not_double_count_buzzword_verbs():
    # ", underscoring X." scores once as a buzzword, not again as a closer.
    r = noslop.analyze("Attendance doubled that year, underscoring the "
                       "festival's growing pull across the region.")
    assert any(w == "underscoring" for w, _, _ in r["buzzwords"])
    assert not any("closer" in label for label, _, _, _, _ in r["patterns"])


def test_connective_bump_is_capped():
    heavy = noslop.analyze("Moreover, results held. Furthermore, costs "
                           "fell. Additionally, the team grew. Notably, "
                           "retention improved. Ultimately, we shipped. "
                           "Overall, a fine quarter by any measure.")
    assert heavy["connective_excess"] > 0
    assert heavy["score_per_1k"] <= 8


# ---- 0.7.0: new construction patterns ----

def test_dangling_ing_closer_is_flagged():
    r = noslop.analyze("The bridge opened in 1932, highlighting the city's ambition.")
    assert any("closer" in label for label, _, _, _, _ in r["patterns"])


def test_ensuring_clause_is_not_flagged_as_closer():
    # ", ensuring ..." is ordinary technical prose, deliberately excluded.
    r = noslop.analyze("The lock is released in a finally block, ensuring the "
                       "file handle is closed even on error.")
    assert not any("closer" in label for label, _, _, _, _ in r["patterns"])


def test_split_sentence_flip_is_flagged():
    r = noslop.analyze("The problem isn't a lack of tools. It's that nobody "
                       "reads the documentation we already have.")
    assert any("split flip" in label for label, _, _, _, _ in r["patterns"])


def test_single_anaphora_triad_reports_but_does_not_score():
    r = noslop.analyze("It works where trust exists, where budgets allow, "
                       "where teams commit.")
    assert any("triad" in label for label, _, _, _, _ in r["patterns"])
    assert r["score_per_1k"] == 0.0


def test_repeated_anaphora_triads_do_score():
    r = noslop.analyze(
        "It works where trust exists, where budgets allow, where teams commit. "
        "We came for the food, for the music, and for the company.")
    assert r["score_per_1k"] > 0


def test_fragment_hook_is_flagged():
    r = noslop.analyze("We cut the budget in half. The result? Nothing broke.")
    assert any("fragment hook" in label for label, _, _, _, _ in r["patterns"])


def test_sycophantic_opener_only_fires_line_initial():
    hit = noslop.analyze("Great question! The answer is in the config.")
    miss = noslop.analyze("She said it was a great question, and moved on.")
    assert any("sycophantic" in label for label, _, _, _, _ in hit["patterns"])
    assert not any("sycophantic" in label for label, _, _, _, _ in miss["patterns"])


def test_tada_opener_only_fires_line_initial():
    hit = noslop.analyze("Here's why this matters. The pump was never the issue.")
    miss = noslop.analyze("I asked him twice, and here's what he said about it.")
    assert any("ta-da" in label for label, _, _, _, _ in hit["patterns"])
    assert not any("ta-da" in label for label, _, _, _, _ in miss["patterns"])


# ---- 0.7.0: structural rhythm checks ----

def test_single_staccato_run_reports_but_does_not_score():
    # Terse fragments are a legitimate human style once - the first run is
    # free and only repetition of the cadence scores.
    r = noslop.analyze("We tried it. It broke. We fixed it. It broke again. "
                       "Nobody panicked. The second attempt held through the "
                       "weekend and nobody had to think about it again.")
    assert r["staccato_runs"] == 1
    assert r["score_per_1k"] == 0.0


def test_repeated_staccato_runs_do_score():
    r = noslop.analyze("We tried it. It broke. We fixed it. Then the plan "
                       "changed for the better part of a week while we "
                       "watched. No fluff. No filler. Just results. That "
                       "was the whole pitch they gave us on the call.")
    assert r["staccato_runs"] == 2
    assert r["score_per_1k"] >= 4


def test_normal_prose_has_no_staccato_runs():
    r = noslop.analyze("The pump broke on Tuesday morning. I drove over after "
                       "lunch and pulled the housing apart. The seal had a "
                       "visible crack along the top edge. A new one cost nine "
                       "dollars at the counter. It has run fine since then.")
    assert r["staccato_runs"] == 0


def test_header_emoji_scores_extra():
    plain = noslop.analyze("Shipping went fine ✅ and everyone went home.")
    decorated = noslop.analyze("# ✅ Shipping Update\n\nEverything went "
                               "fine and everyone went home on time.")
    assert plain["header_emoji"] == 0
    assert decorated["header_emoji"] == 1


def test_bold_inline_spray_has_an_allowance():
    two = noslop.analyze("The **first point** stands. The **second point** "
                         "does not, and the rest of the paragraph explains "
                         "why at a length that keeps the density plausible.")
    assert two["bold_inline_excess"] == 0


def test_bold_paragraph_leads_count_as_label_bullets():
    r = noslop.analyze("**Speed.** We go fast.\n\n**Quality.** We stay sharp."
                       "\n\n**Trust.** We deliver.\n\n**Scale.** We grow.")
    assert r["bold_label_bullets"] == 4
    assert r["score_per_1k"] > 0


def test_quote_mixing_flags_same_kind_paste_boundary():
    # Curly and straight apostrophes both used as apostrophes - the paste
    # boundary the check exists for.
    mixed = noslop.analyze("It’s the vendor’s call and they’ve made it. "
                           "But it's our contract, it's our data, and it's "
                           "our name on the front page when this breaks.")
    assert mixed["quote_mix"] == 1


def test_quoting_a_curly_source_does_not_flag():
    # A straight-apostrophe author quoting a curly-quoted excerpt is how
    # humans cite sources, not paste evidence.
    r = noslop.analyze('The report says “the committee’s decision is '
                       'final” in section two. That\'s the whole basis '
                       'for the town\'s appeal, and it isn\'t much.')
    assert r["quote_mix"] == 0


def test_consistent_quotes_do_not_flag():
    straight = noslop.analyze('He said "fine" and then "not fine" and then '
                              '"we will see" within a single minute.')
    assert straight["quote_mix"] == 0


def test_question_hooks_have_an_allowance_of_one():
    one = noslop.analyze("We doubled the cache. The gain? Four percent, "
                         "which nobody considered worth the added memory.")
    two = noslop.analyze("We doubled the cache. The gain? Four percent. We "
                         "tripled it after. The cost? Memory pressure.")
    assert one["question_hook_excess"] == 0
    assert two["question_hook_excess"] == 1


def test_connective_openers_score_on_density_only():
    light = noslop.analyze("Moreover, the results held. The rest of the "
                           "report was unremarkable in every direction. The "
                           "team moved on to other work within the week.")
    heavy = noslop.analyze("Moreover, results held. Furthermore, costs fell. "
                           "Additionally, the team grew. Notably, retention "
                           "improved. Ultimately, the quarter closed strong.")
    assert light["connective_excess"] == 0
    assert heavy["connective_excess"] > 0


def test_paragraph_uniformity_reported_when_five_paragraphs():
    text = "\n\n".join(
        "This paragraph runs to roughly twenty words when you count it all "
        "the way through to the very end okay." for _ in range(5))
    r = noslop.analyze(text)
    assert r["paragraph_uniformity_cv"] is not None
    assert r["paragraph_uniformity_cv"] < 0.25


def test_opener_share_is_reported_not_scored():
    text = ("The server restarted. The logs were clean. The disk held. "
            "The network stayed up. The backup ran. The monitors slept. "
            "The morning was quiet. The ticket was closed.")
    r = noslop.analyze(text)
    assert r["opener_top_share"] is not None
    assert r["opener_top_share"] >= 0.9


def test_new_buzzwords_are_word_bounded():
    r = noslop.analyze("The realignments were subtle.")  # not "aligns"
    assert not any(w == "aligns" for w, _, _ in r["buzzwords"])


def test_json_schema_keys_match_analyze_output():
    r = noslop.analyze("Plain text.")
    assert set(r) == noslop.JSON_SCHEMA_KEYS


# ---- 0.9.0: chatbot disclaimer artifacts ----

def test_as_an_ai_is_an_artifact_not_a_phrase():
    r = noslop.analyze("As an AI, I don't have personal opinions on this, "
                       "but here is what the data in the report suggests.")
    assert r["ai_artifacts"]
    assert not any(p == "as an ai" for p, _, _ in r["phrases"])
    assert r["score_per_1k"] >= 25


def test_knowledge_cutoff_disclaimer_is_an_artifact():
    r = noslop.analyze("As of my last update, the population figure was "
                       "around eight million, though that may have shifted "
                       "since then given how fast the city has grown.")
    assert r["ai_artifacts"]
    assert "AI" in r["verdict"]


def test_no_browsing_disclaimer_is_an_artifact():
    r = noslop.analyze("I don't have real-time access to the news, so I "
                       "can't confirm today's headline for you directly.")
    assert r["ai_artifacts"]


def test_spanish_ai_self_reference_is_an_artifact():
    r = noslop.analyze(
        "Ayer se me rompió la cadena de la bici a mitad del camino al "
        "trabajo. Como modelo de lenguaje, no puedo verificar esto, pero "
        "la arreglé con el tronchacadenas que llevo desde hace años.",
        lang="es")
    assert r["ai_artifacts"]


# ---- 0.9.0: punctuation-distribution entropy ----

def test_single_punctuation_class_is_low_entropy():
    text = "this, " * 35 + "and that is the end of it."
    r = noslop.analyze(text)
    assert r["punct_entropy"] is not None
    assert r["punct_entropy_low"] is True


def test_short_text_has_no_punct_entropy_reading():
    r = noslop.analyze("Short and plain, done.")
    assert r["punct_entropy"] is None
    assert r["punct_entropy_low"] is False


def test_ordinary_prose_is_not_low_entropy():
    r = noslop.analyze(open(__file__, encoding="utf-8").read()[:4000])
    # the test file's own docstrings/asserts mix enough punctuation classes
    # (commas, colons, parens, quotes) that this should read as varied, not
    # a smoke test of noslop's own source - just a sanity check the flag
    # isn't trivially always true.
    assert r["punct_entropy_low"] is False


# ---- 0.9.0: generic listicle headings ----

def test_single_generic_heading_does_not_score():
    r = noslop.analyze("# Conclusion\n\nOne last plain paragraph about "
                       "nothing in particular, long enough to read fine.")
    assert r["generic_headings"] == 1
    assert r["score_per_1k"] == 0.0


def test_repeated_generic_headings_score():
    text = ("# Introduction\n\nSome plain opening text about the topic.\n\n"
            "# Key Takeaways\n\nA few plain points about the topic.\n\n"
            "# Conclusion\n\nA plain closing paragraph about the topic.\n")
    r = noslop.analyze(text)
    assert r["generic_headings"] == 3
    assert r["score_per_1k"] > 0


def test_bold_and_colon_stripped_before_matching():
    r = noslop.analyze("## **Conclusion:**\n\nPlain text follows here.\n\n"
                       "## Overview\n\nMore plain text follows this line.")
    assert r["generic_headings"] == 2


def test_specific_heading_is_not_generic():
    r = noslop.analyze("# Shipping the v2 API\n\nPlain text about the "
                       "release, nothing templated about this heading.")
    assert r["generic_headings"] == 0


# ---- 0.9.0: bare bullet glyphs ----

def test_bare_bullet_glyphs_score():
    text = ("Here is the plan:\n"
            "• Ship the fix\n"
            "• Write the test\n"
            "• Tell the team\n")
    r = noslop.analyze(text)
    assert r["bare_bullets"] == 3
    assert r["score_per_1k"] > 0


def test_dash_bullets_are_not_bare_bullets():
    r = noslop.analyze("Here is the plan:\n- Ship the fix\n- Write the "
                       "test\n- Tell the team\n")
    assert r["bare_bullets"] == 0


# ---- 0.9.0: copula-avoidance and scope-inflation ----

def test_copula_avoidance_needs_density_to_score():
    r = noslop.analyze("The bridge serves as a crossing for the rail line, "
                       "and it has done that job well for almost a century "
                       "now without a single major structural repair.")
    assert r["copula_avoidance"]
    assert r["copula_avoidance_scored"] is False
    assert r["score_per_1k"] == 0.0


def test_copula_avoidance_scores_past_density_gate():
    text = ("The report serves as a summary of the quarter. The chart "
            "stands as a record of the trend. The footnote functions as a "
            "caveat for the reader, and the appendix acts as a testament "
            "to how much detail was cut from the main draft.")
    r = noslop.analyze(text)
    assert r["copula_avoidance_scored"] is True
    assert r["score_per_1k"] > 0


def test_stands_as_a_testament_is_not_double_counted():
    # The longer PHRASES entry should win the overlap, not stack with the
    # shorter copula-avoidance fragment it contains.
    r = noslop.analyze("The building stands as a testament to a century of "
                       "the city's civic ambition and careful upkeep.")
    assert sum(n for _, n, _ in r["phrases"]) == 1
    assert r["copula_avoidance"] == []


def test_scope_inflation_scores_every_hit():
    r = noslop.analyze("Her contribution to the launch cannot be "
                       "overstated, and the team felt it from the moment "
                       "she joined the project full time.")
    assert r["scope_inflation"]
    assert r["score_per_1k"] > 0


# ---- 0.9.0: heading-level skip (report-only) ----

def test_heading_skip_is_reported_not_scored():
    text = "# Title\n\n## Section\n\n#### Deep subsection\n\nPlain text."
    r = noslop.analyze(text)
    assert r["heading_level_skips"] == 1
    assert r["score_per_1k"] == 0.0


def test_no_heading_skip_when_levels_are_sequential():
    text = "# Title\n\n## Section\n\n### Subsection\n\nPlain text follows."
    r = noslop.analyze(text)
    assert r["heading_level_skips"] == 0


# ---- 0.9.0: cross-paragraph opener repetition ----

def test_repeated_paragraph_openers_score():
    text = "\n\n".join([
        "Best for people who want speed above everything else in a tool.",
        "Best for people who want a simple setup with no configuration.",
        "Best for people who want to run this entirely offline and local.",
        "A closing paragraph that opens differently from the three above.",
        "One more paragraph included just to clear the five-paragraph floor.",
    ])
    r = noslop.analyze(text)
    assert r["paragraph_opener_repeat"] == 3
    assert r["paragraph_opener_repeat_text"] == "best for people who want"
    assert r["score_per_1k"] > 0


def test_varied_paragraph_openers_do_not_score():
    text = "\n\n".join([
        "The first paragraph opens with its own distinct sentence here.",
        "A second paragraph starts on a completely different note today.",
        "Then a third one takes yet another angle on the same subject.",
        "The fourth continues without repeating any earlier opening words.",
        "And the fifth wraps up without echoing the others at all here.",
    ])
    r = noslop.analyze(text)
    assert r["paragraph_opener_repeat"] == 0


# ---- 0.9.0: windowed TTR / function-word ratio (report-only diagnostics) ----

def test_windowed_ttr_needs_200_words():
    r = noslop.analyze("Not nearly enough words here to fill a window.")
    assert r["windowed_ttr"] is None


def test_windowed_ttr_and_function_word_ratio_never_score():
    # A 200+ word block that repeats one word constantly (near-zero TTR)
    # still must not move score_per_1k - these are report-only by design.
    text = ("word " * 220).strip() + "."
    r = noslop.analyze(text)
    assert r["windowed_ttr"] is not None
    assert r["windowed_ttr"] < 0.05
    assert r["score_per_1k"] == 0.0


def test_function_word_ratio_is_always_reported():
    r = noslop.analyze("The cat sat on the mat and then it left the room.")
    assert 0.0 <= r["function_word_ratio"] <= 1.0


# ---- 0.9.0: Russian pack upgrades ----

def test_russian_bureaucratic_determiner_is_a_buzzword():
    r = noslop.analyze("Данный отчёт содержит краткое изложение результатов "
                       "работы команды за прошедший квартал целиком.",
                       lang="ru")
    assert any(w == "данный" for w, _, _ in r["buzzwords"])


def test_russian_opener_cliche_is_a_phrase():
    r = noslop.analyze("В эпоху цифровизации компании пересматривают свои "
                       "процессы, чтобы оставаться конкурентоспособными.",
                       lang="ru")
    assert any("в эпоху цифровизации" in p for p, _, _ in r["phrases"])


def test_yavlyaetsya_has_an_allowance():
    # A couple of ordinary uses of "является" in otherwise plain formal
    # Russian shouldn't score - it's a normal copula verb.
    r = noslop.analyze("Совет является главным органом управления. Устав "
                       "является основным документом организации.",
                       lang="ru")
    assert r["density_crutch_excess"] == 0
    assert r["score_per_1k"] == 0.0


def test_yavlyaetsya_excess_scores_past_the_allowance():
    clause = "Это является важным фактом, который является ключевым. "
    r = noslop.analyze(clause * 6, lang="ru")
    assert r["density_crutch"] > 0
    assert r["density_crutch_excess"] > 0
    assert r["score_per_1k"] > 0


def test_yavlyayutsya_plural_is_not_matched_as_the_singular_crutch():
    # Word-boundary matching on the bare stem "является" deliberately
    # doesn't reach into its own inflected forms - documented as a real
    # limitation in eval/README.md, not a bug.
    r = noslop.analyze("Участниками этих отношений являются граждане и "
                       "юридические лица, если иное не предусмотрено "
                       "законом или уставом организации в целом.",
                       lang="ru")
    assert r["density_crutch"] == 0


def test_russian_ai_self_reference_is_an_artifact():
    r = noslop.analyze("Как языковая модель, я не могу дать точный прогноз, "
                       "но вот что показывают доступные данные по теме.",
                       lang="ru")
    assert r["ai_artifacts"]


def _repo_file(*parts):
    return os.path.join(os.path.dirname(__file__), os.pardir, *parts)


def test_readme_version_pins_match_the_shipped_version():
    # The pre-commit and Action snippets in the README pin a release tag.
    # Those pins once sat at v0.6.0 across three releases; this keeps every
    # pinned example on the version this module says it is.
    with open(_repo_file("README.md"), encoding="utf-8") as fh:
        readme = fh.read()
    pins = re.findall(r"(?:rev:\s*|munzzyy/noslop@)v(\d+\.\d+\.\d+)", readme)
    assert pins, "the README should pin the pre-commit and Action examples"
    assert set(pins) == {noslop.__version__}


def test_packaging_versions_match_the_module():
    # pyproject.toml and the Claude Code plugin manifest each carry their
    # own copy of the version; both have drifted before
    with open(_repo_file("pyproject.toml"), encoding="utf-8") as fh:
        assert 'version = "%s"' % noslop.__version__ in fh.read()
    with open(_repo_file(".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
        assert json.load(fh)["version"] == noslop.__version__


# ---------------------------------------------------------------------------
# Code mode


def test_extractor_url_in_string_is_not_a_comment():
    p = noslop.extract_code_parts('const u = "https://x.com/a"; // real\n', "c")
    assert [c[1] for c in p["comments"]] == ["real"]
    assert any("https://x.com/a" in s for _, s in p["strings"])


def test_extractor_hash_in_python_string_is_not_a_comment():
    p = noslop.extract_code_parts('x = "#nope"\n# yes\n', "hash")
    assert [c[1] for c in p["comments"]] == ["yes"]


def test_extractor_docstring_vs_assigned_triple_string():
    src = '"""Mod."""\n\ndef f():\n    """Doc."""\n    x = """data"""\n'
    p = noslop.extract_code_parts(src, "hash")
    assert [d[1] for d in p["docstrings"]] == ["Mod.", "Doc."]
    assert any("data" in s for _, s in p["strings"])


def test_extractor_block_comment_line_numbers():
    p = noslop.extract_code_parts("int x;\n/* a\nb\nc */\nint y; // t\n", "c")
    assert p["comments"][0][0] == 2 and p["comments"][1] == (5, "t")
    assert p["loc"] == 2


def test_extractor_rust_lifetime_does_not_swallow_file():
    src = "fn f<'a>(x: &'a str) -> &'a str { x } // c1\n// c2\n"
    p = noslop.extract_code_parts(src, "rust")
    assert [c[1] for c in p["comments"]] == ["c1", "c2"]


def test_extractor_rust_nested_block_comments():
    p = noslop.extract_code_parts("/* o /* i */ still */ fn main() {}\n", "rust")
    assert "still" in p["comments"][0][1] and "fn main" in p["code"]


def test_extractor_js_template_literal_swallows_fake_comment():
    p = noslop.extract_code_parts("const t = `x // no\n${y}`;\n// real\n", "c")
    assert [c[1] for c in p["comments"]] == ["real"]


def test_extractor_c_preprocessor_is_code():
    p = noslop.extract_code_parts("#include <stdio.h>\nint m; // ok\n", "c")
    assert [c[1] for c in p["comments"]] == ["ok"]
    assert "#include" in p["code"]


def test_extractor_unterminated_block_comment_does_not_crash():
    p = noslop.extract_code_parts("/* open\nmore", "c")
    assert "open" in p["comments"][0][1]


def test_extractor_body_comments_exclude_column_zero_and_trailing():
    src = "# top\ndef f():\n    # body\n    x = 1  # trailing\n"
    p = noslop.extract_code_parts(src, "hash")
    assert [c[1] for c in p["body_line_comments"]] == ["body"]


def test_sniff_prefers_c_family_over_preprocessor_hashes():
    assert noslop.sniff_code_family("#include <a>\n// x\n// y\n")[0] == "c"
    assert noslop.sniff_code_family("# a\n# b\nx = 1\n")[0] == "hash"


def test_code_schema_keys_are_pinned():
    r = noslop.analyze_code("x = 1\n", ext=".py")
    assert set(r) == noslop.JSON_SCHEMA_KEYS_CODE


def test_code_truncation_marker_pins_hard_verdict():
    src = "def f():\n    pass\n\n# ... rest of the code remains the same\n"
    r = noslop.analyze_code(src, ext=".py")
    assert r["score_per_100"] >= 25 and r["ai_artifacts"]


def test_bare_rest_of_the_file_is_not_an_artifact():
    src = "# The parser ignores the rest of the file after a null byte.\nx = 1\n"
    r = noslop.analyze_code(src, ext=".py")
    assert not r["ai_artifacts"]


def test_markdown_fence_in_comment_is_paste_evidence():
    src = "# ```python\nx = 1\n"
    r = noslop.analyze_code(src, ext=".py")
    assert r["score_per_100"] >= 25


def test_fence_in_docstring_is_fine():
    src = 'def f():\n    """Use it:\n\n    ```python\n    f()\n    ```\n    """\n'
    r = noslop.analyze_code(src, ext=".py")
    assert not r["ai_artifacts"]


def test_claude_trailer_in_code_comment_is_paste_evidence():
    src = "// Co-Authored-By: Claude <noreply@anthropic.com>\nint x;\n"
    r = noslop.analyze_code(src, ext=".c")
    assert r["score_per_100"] >= 25


def test_chat_share_link_in_comment_is_paste_evidence():
    src = "# see https://claude.ai/share/abc123\nx = 1\n"
    r = noslop.analyze_code(src, ext=".py")
    assert r["score_per_100"] >= 25


def test_artifact_in_string_literal_is_excused():
    # A detector (like this one) has to name the markers in string literals.
    src = 'MARKERS = ["noreply@anthropic.com", "claude.ai/share"]\n'
    r = noslop.analyze_code(src, ext=".py")
    assert not r["ai_artifacts"]


def test_quoted_mention_in_comment_is_excused():
    src = '# The phrase "as an AI language model" pins the verdict.\nx = 1\n'
    r = noslop.analyze_code(src, ext=".py")
    assert not r["ai_artifacts"]


def test_unquoted_disclaimer_in_comment_scores():
    src = "# As an AI language model I cannot run this directly.\nx = 1\n"
    r = noslop.analyze_code(src, ext=".py")
    assert r["score_per_100"] >= 25


def test_error_boilerplate_and_swallowed_handler():
    src = ('try:\n    go()\nexcept Exception as e:\n'
           '    print(f"An error occurred: {e}")\n')
    r = noslop.analyze_code(src, ext=".py")
    assert r["error_boilerplate"] and r["swallowed_errors"]


def test_success_boilerplate_first_hit_free():
    one = 'print("saved successfully")\n'
    r = noslop.analyze_code(one, ext=".py")
    assert len(r["success_boilerplate"]) == 1 and r["score_per_100"] == 0


def test_redundant_comment_restating_next_line():
    src = ("# increment the retry counter\nretry_counter += 1\n"
           "# append the name to the results\nresults.append(name)\n")
    r = noslop.analyze_code(src, ext=".py")
    assert len(r["redundant_comments"]) >= 2


def test_why_comment_is_not_redundant():
    src = "# utf-8-sig: the export tool prepends a BOM on Windows\ndata = read(path)\n"
    r = noslop.analyze_code(src, ext=".py")
    assert not r["redundant_comments"]


def test_todo_tagged_comments_are_exempt_from_redundancy():
    src = "# TODO: retry counter reset\nretry_counter = 0\n"
    r = noslop.analyze_code(src, ext=".py")
    assert not r["redundant_comments"]


def test_narration_needs_corroboration():
    # Imperative body comments alone (2012-jQuery style) must not score.
    lines = []
    for i in range(6):
        lines.append("def f%d():" % i)
        lines.append("    # Create the widget for slot %d" % i)
        lines.append("    build(%d)" % i)
    r = noslop.analyze_code("\n".join(lines) + "\n", ext=".py")
    assert r["narration_comment_count"] >= 4
    assert not r["narration_scored"]
    assert r["score_per_100"] < 10


def test_narration_scores_once_corroborated():
    lines = ['import os\n\ndef go():\n    """Go."""']
    for i in range(6):
        lines.append("    # Create the widget for slot %d" % i)
        lines.append("    build(%d)" % i)
    lines.append('    print(f"An error occurred: oops")')
    r = noslop.analyze_code("\n".join(lines) + "\n", ext=".py")
    assert r["narration_scored"]


def test_docstring_name_echo():
    src = 'def get_user_name(u):\n    """Get the user name."""\n    return u.name\n'
    r = noslop.analyze_code(src, ext=".py")
    assert len(r["docstring_name_echoes"]) == 1


def test_informative_docstring_is_not_an_echo():
    src = ('def get_user_name(u):\n'
           '    """Prefers the display name; falls back to the login."""\n'
           '    return u.display or u.login\n')
    r = noslop.analyze_code(src, ext=".py")
    assert not r["docstring_name_echoes"]


def test_em_dash_and_curly_quotes_in_comments_score():
    src = "# The parser — unlike the lexer — uses “smart” buffering\nx = 1\n"
    r = noslop.analyze_code(src, ext=".py")
    assert r["typography"]


def test_emoji_in_log_string_counts_but_pure_emoji_data_does_not():
    data_only = 'EMOJI = "✅❌"\n'
    assert noslop.analyze_code(data_only, ext=".py")["emoji"] == 0
    log = 'print("done ✅")\n'
    assert noslop.analyze_code(log, ext=".py")["emoji"] == 1


def test_invisible_char_outside_strings_is_an_artifact():
    src = "x = 1  # tot" + chr(0x200B) + "al\n"
    r = noslop.analyze_code(src, ext=".py")
    assert any("invisible" in label for label, _, _ in r["ai_artifacts"])


def test_invisible_char_inside_string_is_excused():
    src = 's = "a' + chr(0x200B) + 'b"\n'
    r = noslop.analyze_code(src, ext=".py")
    assert not r["ai_artifacts"]


def test_short_snippet_denominator_floor():
    # One weight-2 hit in a 2-line snippet must not cross the soft verdict.
    src = "# increment the counter\ncounter += 1\n"
    r = noslop.analyze_code(src, ext=".py")
    assert r["score_per_100"] < 10


def test_report_code_smoke():
    r = noslop.analyze_code("# Example usage\nx = 1\n", ext=".py")
    out = noslop.report_code(r)
    assert "AI-tell score" in out and "example usage" in out.lower()


def test_cli_auto_code_mode_by_extension(tmp_path=None):
    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        p = os.path.join(d, "s.py")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")
        code, out = run_cli(["--no-config", "--json", p])
        assert code == 0
        assert json.loads(out)["mode"] == "code"


def test_cli_prose_flag_overrides_code_extension():
    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        p = os.path.join(d, "s.py")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("plain text here\n")
        code, out = run_cli(["--no-config", "--prose", "--json", p])
        assert json.loads(out)["mode"] == "prose"


def test_cli_code_flag_for_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("// Example usage\nint x;\n"))
    code, out = run_cli(["--no-config", "--code", "--json"])
    assert json.loads(out)["mode"] == "code"


def test_cli_mixed_prose_and_code_run():
    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        py = os.path.join(d, "s.py")
        md = os.path.join(d, "n.md")
        with open(py, "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")
        with open(md, "w", encoding="utf-8") as fh:
            fh.write("Plain human note.\n")
        code, out = run_cli(["--no-config", "--json", py, md])
        modes = [r["mode"] for r in json.loads(out)]
        assert modes == ["code", "prose"]


def test_cli_rdjson_for_code_findings():
    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        p = os.path.join(d, "s.py")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("# ```python\nx = 1\n")
        code, out = run_cli(["--no-config", "--rdjson", p])
        rows = [json.loads(l) for l in out.strip().splitlines()]
        assert rows and rows[0]["severity"] == "ERROR"
        assert rows[0]["location"]["path"] == p


def test_prose_mode_flags_coding_tool_trailers():
    msg = ("Fix the flaky retry test\n\n"
           "Co-Authored-By: Claude Opus <noreply@anthropic.com>\n")
    r = noslop.analyze(msg)
    assert r["score_per_1k"] >= 25
    assert any("Claude Code" in label for label, _, _ in r["ai_artifacts"])


def test_prose_mode_flags_chat_share_links():
    r = noslop.analyze("Discussed at https://chatgpt.com/share/abc, see notes.")
    assert r["score_per_1k"] >= 25


def test_code_self_scan_stays_clean():
    # The proof is the product: noslop.py in code mode scores itself under
    # the soft threshold, and CI runs this same check.
    with open(_repo_file("noslop.py"), encoding="utf-8") as fh:
        r = noslop.analyze_code(fh.read(), ext=".py")
    assert r["score_per_100"] < 10
    with open(_repo_file("web", "detector.js"), encoding="utf-8") as fh:
        r = noslop.analyze_code(fh.read(), ext=".js")
    assert r["score_per_100"] < 10


def test_shell_heredoc_body_is_not_comments():
    # Payload lines inside a heredoc are text being written elsewhere, not
    # shell comments - found by the cold verifier before 0.10.0 shipped.
    src = ("#!/bin/bash\n"
           "cat > cfg.sh << 'EOF'\n"
           "# Step 1: build the image\n"
           "# Step 2: push to registry\n"
           "# Step 3: restart the service\n"
           "EOF\n"
           "echo done\n")
    p = noslop.extract_code_parts(src, "shell")
    assert not any("Step" in c for _, c in p["comments"])
    r = noslop.analyze_code(src, ext=".sh")
    assert not r["comment_patterns"]
    assert r["score_per_100"] == 0


def test_shell_comments_resume_after_heredoc_terminator():
    src = ("cat <<EOF\nbody text\nEOF\n# real comment\n")
    p = noslop.extract_code_parts(src, "shell")
    assert [c[1] for c in p["comments"]] == ["real comment"]
    assert any("body text" in s for _, s in p["strings"])


def test_shell_tab_indented_heredoc_terminator():
    src = "cat <<-EOF\n\tbody\n\tEOF\n# after\n"
    p = noslop.extract_code_parts(src, "shell")
    assert [c[1] for c in p["comments"]] == ["after"]


def test_shell_arithmetic_shift_is_not_a_heredoc():
    src = "x=$((1 << 20))\n# real comment\n"
    p = noslop.extract_code_parts(src, "shell")
    assert [c[1] for c in p["comments"]] == ["real comment"]


def test_shell_unterminated_heredoc_does_not_crash():
    p = noslop.extract_code_parts("cat <<EOF\n# never closed\n", "shell")
    assert not p["comments"]


def test_sniff_shell_shebang_picks_shell_family():
    assert noslop.sniff_code_family("#!/bin/bash\ncat <<EOF\nx\nEOF\n")[0] == "shell"
    assert noslop.sniff_code_family("#!/usr/bin/env bash\n")[0] == "shell"
