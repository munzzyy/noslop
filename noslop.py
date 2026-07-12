#!/usr/bin/env python3
"""noslop - flag the AI tells in a piece of writing.

Reads text from file arguments or stdin and prints the patterns that make prose
read as LLM-generated: filler phrases, overused buzzwords, the "not just X, but Y"
frame, em-dash spray, emoji, suspiciously even sentence and paragraph rhythm,
staccato fragment runs, bold-emphasis spray, mixed quote styles, and - the
smoking gun - literal chat-UI residue like leftover citation markup or
"utm_source=chatgpt.com" links. It does NOT rewrite anything - that's your
job. It just shows you where to look.

Speaks more than English: each language in LANGUAGES carries its own researched
tell lists (an LLM's crutch words in Spanish are Spanish, not translations of
the English list). Input language is sniffed per file, or forced with --lang;
text that can't be confidently identified falls back to the English pack plus
the structural checks, and the output says so.

Standard library only. No network, no dependencies.

Usage:
  noslop draft.md
  noslop docs/*.md
  echo "some text here" | noslop
  noslop --json draft.md       # machine-readable
  noslop --quiet draft.md      # verdict line only

Exit code is 0 when every input reads human enough, 1 when something needs
a pass, and 2 if a path couldn't be read at all - so a crash and a lint
finding never look the same to a script.
"""
import sys
import re
import json
import glob
import os
import math
import fnmatch
import argparse

__version__ = "0.10.0"

# analyze()'s return dict is noslop's only machine-readable contract. If you
# add, rename, or remove a top-level key, update this set and bump the
# version - anything parsing --json is relying on these names staying put.
JSON_SCHEMA_KEYS = {
    # "mode" was added in 0.10.0 alongside code mode, so anything consuming
    # mixed prose/code --json output can tell the two result shapes apart.
    "mode",
    "words", "score_per_1k", "verdict", "language", "language_source",
    "buzzwords", "phrases", "patterns", "ai_artifacts",
    "em_dashes", "em_dash_excess", "emoji", "header_emoji",
    "bold_label_bullets", "bold_inline", "bold_inline_excess", "quote_mix",
    "staccato_runs", "question_hooks", "question_hook_excess",
    "connective_openers", "connective_excess",
    "sentence_uniformity_cv", "paragraph_uniformity_cv",
    "opener_top_share",
    # 0.9.0 additions - see the annotated blocks below for what each one is.
    "copula_avoidance", "copula_avoidance_scored", "scope_inflation",
    "generic_headings", "bare_bullets", "punct_entropy", "punct_entropy_low",
    "heading_level_skips", "paragraph_opener_repeat",
    "paragraph_opener_repeat_text", "windowed_ttr", "function_word_ratio",
    "density_crutch", "density_crutch_excess",
}

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
    # Post-2024 additions with measured excess over the pre-LLM baseline
    # (Juzek & Ward 2025, COLING; Kobak et al. 2025, Science Advances) plus
    # the safest picks from Wikipedia's signs-of-AI-writing catalog. Words
    # those same sources warn have too high a human base rate to score on a
    # single hit (within, across, additionally, potential, findings) are
    # deliberately absent.
    # "advancements", "valuable insights", and "garnered" were measured
    # too, but their base rate in ordinary human registers (non-native
    # academic prose, wire-service journalism) is high enough that a
    # single hit shouldn't score - left out on purpose.
    "groundbreaking", "aligns", "surpassing", "surpasses",
    "emphasizing", "comprehending",
    "showcases", "trailblazing", "bolstered", "resonate", "resonates",
    "solidify", "solidifies", "solidifying", "diverse array", "focal point",
    "indelible mark", "deeply rooted",
    "enduring legacy", "lasting legacy",
]

# Whole-phrase tics. Matched case-insensitively as substrings.
PHRASES = [
    "it's important to note", "it is important to note", "it's worth noting",
    "it is worth noting", "in conclusion", "in summary", "to sum up",
    "that said", "rest assured", "needless to say", "at the end of the day",
    "in today's world", "in today's fast-paced", "let's dive", "dive into",
    "let's break it down", "here's the thing", "i hope this helps",
    "feel free to", "happy to help", "great question",
    # "as an ai" / "as a language model" moved to AI_ARTIFACT_PHRASES in
    # 0.9.0 - a person describing their own writing never says either one,
    # so it's paste evidence (floor-at-25), not a vocabulary tell.
    "this is where", "look no further",
    "without further ado", "the key takeaway", "let's explore",
    "let's take a look", "buckle up", "when it comes to", "at its core",
    "the world of", "in the realm of", "plays a vital role",
    "plays a crucial role", "a wide range of", "more than just",
    "not just a", "whether you're a", "gone are the days",
    # Significance inflation and chat-native framing, from the Wikipedia
    # signs-of-AI-writing catalog and the 2025 pattern write-ups.
    "stands as a testament", "a testament to", "marks a pivotal",
    "a pivotal moment", "continues to captivate", "continues to thrive",
    "cements its legacy", "solidifies its position", "leaves a lasting",
    "setting the stage for", "represents a significant shift",
    # Chat closers like "let me know if" and "hope that helps" are NOT
    # here: they're the standard sign-off of ordinary human work email,
    # and a per-hit score would brand every reply-all in the building.
    # "Paving the way" stays out too - local news writes it unprompted.
    "industry experts note", "experts agree that",
    "observers have noted", "in a world where",
]

# (label, regex, weight, hint)
PATTERNS = [
    ("'not just X but Y' construction",
     r"\bnot (?:just|only)\b[^.?!\n]{1,70}?\bbut\b", 3,
     "state it plainly instead of the contrast frame"),
    ("'it isn't X, it's Y' flip",
     r"\bis(?:n['’]t| not)\b[^.?!\n]{1,45}?\bit(?:['’]s| is)\b", 2,
     "just say what it is"),
    ("rhetorical question opener",
     r"(?im)^\s*(?:ever wondered|have you ever|what if|imagine (?:a|if|that)|picture this)\b", 2,
     "open with the point, not a hook"),
    ("hedge stack (may/can/often/typically)",
     r"\b(?:may|might|can|could|often|typically|generally|usually|arguably)\b", 0,
     "too many hedges reads evasive - commit or cut"),
    # The 2025 wave: structural habits documented by Wikipedia's
    # signs-of-AI-writing catalog and corroborated in at least one
    # independent pattern study each. Verbs with a real human base rate in
    # technical prose (ensuring, demonstrating, signaling) are left out of
    # the closer list, and so are the ones already scored as buzzwords
    # ("underscoring", "emphasizing", "fostering", "solidifying",
    # "showcasing") - one clause shouldn't pay twice. Apostrophes match straight or curly forms
    # because patterns run on the raw text, not the normalized copy. The
    # 5th field, where present, is free hits: a single use of a device
    # that's legitimate rhetoric once (a lone triad, one wire-service
    # closer, one op-ed flip) reports but doesn't score.
    ("dangling '-ing' significance closer",
     r"(?i),\s+(?:highlighting|reflecting|symbolizing|cementing|"
     r"reinforcing|cultivating|encompassing)\b[^.?!\n]{0,80}[.?!]", 3,
     "end at the fact - the tacked-on significance clause adds nothing", 1),
    ("'It's not X. It's Y.' split flip",
     r"(?i)\b(?:is(?:n['’]t| not)|are(?:n['’]t| not)|does(?:n['’]t| not)|"
     r"was(?:n['’]t| not))\b[^.?!\n]{1,60}[.!]\s+it(?:['’]s| is)\b", 3,
     "merge the flip into one plain statement of what it is", 1),
    # The repeated token is ASCII-only ([a-z]) and the JS mirror wraps it
    # in Unicode-letter lookarounds, so an accented continuation ("café")
    # doesn't count as the token in either engine. Coordinators and
    # articles are excluded as the token: "A, or B, or C" is ordinary
    # enumeration, not rhetorical anaphora.
    ("anaphora triad (where X, where Y, where Z)",
     r"(?i)\b(?!(?:and|or|nor|the|an?)\b)([a-z]{2,12})\b[^,.?!\n]{2,40},\s+"
     r"\1\b[^,.?!\n]{2,40},\s+(?:and\s+)?\1\b", 2,
     "one of the three carries the point - keep that one", 1),
    ("ta-da opener ('Here's why...')",
     r"(?im)^\s*#*\s*here['’]s (?:why|how|what)\b", 2,
     "skip the reveal frame - state the thing itself"),
    ("fragment hook ('The result?')",
     r"(?im)(?:^\s*|(?<=[.!?])\s+)(?:the result|the best part|the catch|"
     r"the takeaway|the kicker|the bottom line|translation)\?", 2,
     "answer in the same sentence, or cut the hook"),
    ("sycophantic opener",
     r"(?im)^\s*(?:great question|certainly|absolutely|of course|sure thing)!", 3,
     "drop the chat-style opener - prose isn't answering anyone"),
    ("'despite challenges ... continues to' arc",
     r"(?i)\bdespite\b[^.?!\n]{0,80}?\b(?:challenges|obstacles|setbacks|"
     r"hurdles)\b[^.?!\n]{0,120}?\bcontinues? to\b", 2,
     "name the specific challenge and the specific response"),
]

# Chat-UI residue: literal strings a chatbot interface leaves behind in
# copied text. Nobody types these by hand, so this is direct paste evidence,
# not a probabilistic tell - a single hit pins the score at the hard-verdict
# floor. Matched case-insensitively as plain substrings; overlapping or
# adjacent hits merge so one pasted artifact reports once. Language-neutral:
# every language pack gets this check.
AI_ARTIFACTS = [
    ("chatbot citation residue (oaicite)", "oaicite"),
    ("chatbot citation residue (oai_citation)", "oai_citation"),
    ("chatbot citation residue (grok_card)", "grok_card"),
    ("chatgpt.com link-tracking parameter", "utm_source=chatgpt.com"),
    ("openai link-tracking parameter", "utm_source=openai"),
    # Coding-tool signatures. Each one is a literal string the tool writes
    # into commit messages and PR bodies by default, so presence is proof.
    # Absence proves nothing - these are the first thing people strip.
    # The Claude trailer is matched on the noreply address, not the name:
    # "Co-Authored-By: Claude <...>" varies its display name by model, and
    # a human co-author actually named Claude shouldn't trip it.
    ("Claude Code commit trailer", "noreply@anthropic.com"),
    ("Claude Code PR footer", "generated with [claude code]"),
    ("Cursor agent commit trailer", "cursoragent@cursor.com"),
    ("Devin commit trailer", "devin-ai-integration"),
    ("AI chat share link", "claude.ai/share"),
    ("AI chat share link", "chatgpt.com/share"),
    ("AI chat share link", "chat.openai.com/share"),
    ("AI chat share link", "gemini.google.com/share"),
    # "[Insert name]"-style placeholders are NOT in this list: humans write
    # those on purpose in mail-merge and resume templates, so they fail the
    # "nobody types these by hand" bar this class requires.
]

# Chatbot disclaimer sentences: things a chat assistant says about itself
# that nobody drafting their own prose writes unprompted. Same floor-at-25
# tier as AI_ARTIFACTS above, but these are natural-language phrases (with
# spaces that can wrap across an edited line), not markup tokens that can
# sit inside a URL - so they're matched with find_all()'s word-boundary
# search instead of find_all_plain()'s bare substring search. Matching
# "as an ai" as a raw substring would also fire inside "was an air leak";
# the word-boundary search doesn't.
#
# "as an AI" / "as a language model" used to be phrase-tier (weight 3, like
# any other filler phrase) - promoted to this tier because, like the
# citation residue above, a person drafting their own writing does not
# refer to themselves this way. It's paste evidence, not a vocabulary tell.
AI_ARTIFACT_PHRASES = [
    ("chatbot self-reference (\"as an AI\")", "as an ai"),
    ("chatbot self-reference (\"as a language model\")", "as a language model"),
    ("chatbot knowledge-cutoff disclaimer (\"as of my last update\")", "as of my last update"),
    ("chatbot knowledge-cutoff disclaimer (\"as of my knowledge cutoff\")", "as of my knowledge cutoff"),
    ("chatbot no-browsing disclaimer (\"I don't have real-time access\")", "i don't have real-time access"),
    ("chatbot no-browsing disclaimer (\"I cannot browse the internet\")", "i cannot browse the internet"),
]

# Copula-avoidance filler ("X serves as a Y" instead of "X is a Y") -
# legitimate technical writing uses these occasionally, so this is scored on
# density (2+ per 1,000 words), not on the first hit, the same guard as the
# hedge-stack and connective-opener checks. English only for now.
COPULA_AVOIDANCE = [
    "serves as a", "stands as a", "functions as a", "acts as a testament",
]
COPULA_AVOIDANCE_MIN_PER_1K = 2.0

# Per-language "density crutch" words: an ordinary verb/word in that
# language that LLM prose leans on as a formal-register filler well past
# normal usage - only the count past a calibrated per-1,000-word allowance
# scores, the same density-allowance shape as em dashes. A pack opts in
# with a "density_crutch" tuple; packs without one skip the check. (Russian
# "является" is the only entry so far - see the ru pack's note.)
DENSITY_CRUTCH_ALLOWANCE_DIVISOR = 150

# Scope-inflation phrases - significance-language that's a normal idiom once
# and a tell in a cluster. Lower weight than a buzzword/phrase hit (2, not
# 3) because each one has legitimate everyday use. English only for now.
SCOPE_INFLATION = [
    "cannot be overstated", "cannot be understated", "in every sense of the word",
    "from the moment",
]

# Generic listicle headings an LLM reaches for by default (Introduction,
# Key Takeaways, Final Thoughts...). One "Conclusion" is an ordinary essay
# structure - it's the *pattern* of several of these in one document that
# reads templated, so this only scores at 2+ hits. English only for now;
# see the language notes near LANGUAGES for why a translated set isn't
# shipped yet.
GENERIC_HEADINGS = frozenset((
    "introduction", "conclusion", "overview", "key takeaways",
    "final thoughts", "in summary", "background", "the bottom line",
    "why it matters", "getting started",
))

# Bare bullet glyphs opening a line - chat-UI copy/paste residue. Nobody
# hand-types a U+2022 BULLET, U+25AA BLACK SMALL SQUARE, or U+2023
# TRIANGULAR BULLET into a markdown file; the native way to write a list
# item is "-" or "*". Phrase-tier weight, not the artifact floor, because a
# note-taking app's export can legitimately carry these.
BARE_BULLET_RE = re.compile(r"(?m)^[ \t]*[•▪‣]")

# Sentence-punctuation classes for the entropy check below. Deliberately
# excludes characters that mean something other than sentence punctuation in
# code-adjacent prose (slashes, brackets, at-signs).
PUNCT_CLASS = ".,;:!?…()'\"’“”—-"
PUNCT_ENTROPY_MIN_CHARS = 30
PUNCT_ENTROPY_LOW = 0.55


def punct_entropy(text):
    """Shannon entropy over the sentence-punctuation characters in text,
    normalized by log2(distinct classes used) so the result is 0..1
    regardless of how many of the PUNCT_CLASS characters appear at all.
    Low normalized entropy means the writer leans on very few punctuation
    marks - a comma-only or dash-only style - which reads flatter than
    ordinary prose, where writers reach for a wider mix. Returns None when
    there isn't enough punctuation in the sample to measure honestly (under
    PUNCT_ENTROPY_MIN_CHARS marks - a short document can look artificially
    "even" by chance alone)."""
    counts = {}
    total = 0
    for ch in text:
        if ch in PUNCT_CLASS:
            counts[ch] = counts.get(ch, 0) + 1
            total += 1
    if total < PUNCT_ENTROPY_MIN_CHARS:
        return None
    classes = len(counts)
    if classes <= 1:
        return 0.0
    ent = -sum((c / total) * math.log2(c / total) for c in counts.values())
    return round(ent / math.log2(classes), 3)

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

# ---------------------------------------------------------------------------
# Language packs.
#
# An LLM over-writing in Spanish doesn't overuse translations of the English
# buzzword list - it has its own crutches (sumérgete, sin fisuras, cabe
# destacar). So every language here carries its own researched lists, written
# from how LLM prose actually reads in that language, never machine-translated
# from English. If you add a pack, add the same pack to web/detector.js and a
# fixture pair to web/parity.js, or CI goes red.
#
# Pack fields:
#   name          native display name
#   buzzwords     per-language BUZZWORDS equivalent
#   phrases       per-language PHRASES equivalent
#   patterns      per-language PATTERNS equivalent (labels/hints localized)
#   stopwords     high-frequency function words, used only by detect_language()
#   marks         characters distinctive of the language, a detection tiebreak
#   em_dash_factor  multiplier on the em-dash allowance. Spanish, French,
#                 Italian, and Portuguese use long dashes for dialogue, so an
#                 allowance tuned for English prose would flag ordinary
#                 dialogue punctuation. 1.0 keeps the English behavior.
#                 Russian, Ukrainian, Polish, Turkish, and Romanian join that
#                 dialogue-dash tier (2.5) for the same reason - each opens a
#                 line of dialogue with the dash by literary convention, and
#                 Russian/Ukrainian also use it as a zero-copula substitute
#                 ("Это - хорошо"). Hungarian's gondolatjel sees real but
#                 less totalizing dialogue use, so it gets German's partial
#                 1.5 rather than the full allowance. Czech, Swedish, and
#                 Finnish dialogue is conventionally quotation-mark-based, so
#                 they keep the English 1.0.
#
# The weights (3 per buzzword/phrase hit, pattern weights, +8 uniformity) are
# the same in every pack, so a 25+/1k verdict means the same thing in every
# language. The structural checks that don't depend on wording - chat-UI
# artifacts, staccato runs, paragraph uniformity, heading emoji, bold spray,
# quote mixing, opener concentration - run identically for every language,
# so packs only need to localize vocabulary, phrases, and patterns.
LANGUAGES = {
    "en": {
        "name": "English",
        "buzzwords": BUZZWORDS,
        "phrases": PHRASES,
        "patterns": PATTERNS,
        "stopwords": frozenset((
            "the", "and", "of", "to", "is", "that", "it", "with", "for",
            "this", "was", "are", "have", "but", "they", "from", "not",
            "what", "you", "all",
        )),
        # Sentence-initial connective adverbs (Moreover, Furthermore...).
        # Scored on density, never per hit - academic prose uses these
        # legitimately; it's the every-other-sentence spray that reads AI.
        # Packs without this field skip the check rather than borrowing
        # translations that were never researched for their language.
        "connectives": (
            "moreover", "furthermore", "additionally", "notably",
            "ultimately", "importantly", "crucially", "significantly",
            "in essence", "overall",
        ),
        # Density-gated filler families - see COPULA_AVOIDANCE and
        # SCOPE_INFLATION above for the rationale. English only for now;
        # packs without these fields just skip the checks.
        "copula_avoidance": COPULA_AVOIDANCE,
        "scope_inflation": SCOPE_INFLATION,
        "marks": "",
        "em_dash_factor": 1.0,
    },
    "es": {
        "name": "Español",
        "buzzwords": [
            "sumérgete", "sumergirse", "adentrarse", "adentrémonos", "tapiz",
            "crisol", "vasto", "vasta", "panorama", "vanguardia",
            "vanguardista", "revolucionario", "revolucionaria", "disruptivo",
            "disruptiva", "transformador", "transformadora", "holístico",
            "holística", "sinergia", "sinergias", "paradigma", "integral",
            "robusto", "robusta", "sin fisuras", "sin esfuerzo",
            "desbloquear", "desbloquea", "potenciar", "potencia", "impulsar",
            "impulsa", "fomentar", "fomenta", "empoderar", "empodera",
            "dar rienda suelta", "primordial", "crucial", "meticuloso",
            "meticulosa", "piedra angular", "cautivador", "cautivadora",
            "en constante evolución", "abanico de posibilidades",
            "amplia gama", "sinfín de", "innovador", "innovadora",
            "experiencia fluida", "llevar al siguiente nivel",
            "un mundo de posibilidades", "cambio de paradigma",
        ],
        "phrases": [
            "es importante destacar", "es importante señalar",
            "es importante tener en cuenta", "cabe destacar", "cabe señalar",
            "cabe mencionar", "vale la pena destacar",
            "vale la pena mencionar", "en resumen", "en conclusión",
            "para concluir", "en definitiva", "al fin y al cabo",
            "en la era digital", "en el mundo actual",
            "en el vertiginoso mundo", "sumérgete en", "exploremos",
            "profundicemos en", "espero que esto ayude",
            "espero que esto te ayude", "no dudes en", "siéntete libre de",
            "gran pregunta", "excelente pregunta",
            # "como modelo de lenguaje" / "como inteligencia artificial"
            # moved to artifact_phrases below in 0.9.0 - see the note on
            # AI_ARTIFACT_PHRASES.
            "desbloquea todo tu potencial",
            "libera todo tu potencial", "ya seas", "tanto si eres",
            "atrás quedaron los días", "más que un simple",
            "juega un papel crucial", "juega un papel fundamental",
            "desempeña un papel", "una amplia variedad de",
            "cuando se trata de",
        ],
        "patterns": [
            ("construcción 'no solo X, sino Y'",
             r"(?i)\bno (?:solo|sólo|solamente)\b[^.?!\n]{1,70}?\bsino\b", 3,
             "dilo directamente, sin el marco de contraste"),
            ("giro 'no es X, es Y'",
             r"(?i)\bno es\b[^.?!\n]{1,45}?\bes\b", 2,
             "di lo que es, sin el rodeo"),
            ("pregunta retórica de apertura",
             r"(?im)^\s*(?:¿alguna vez te has preguntado|¿te has preguntado"
             r"|¿alguna vez has|imagina (?:un|una|que)|imagínate"
             r"|¿qué pasaría si)", 2,
             "abre con la idea, no con el gancho"),
            ("acumulación de matizadores (puede/podría/a menudo)",
             r"(?i)\b(?:puede|podría|podrían|a menudo|generalmente"
             r"|típicamente|usualmente|posiblemente|quizás|tal vez)\b", 0,
             "tantos matices suenan evasivos - afirma o corta"),
        ],
        # Chatbot self-reference/disclaimer phrases, promoted out of
        # "phrases" above - see AI_ARTIFACT_PHRASES for why. The knowledge-
        # cutoff and no-browsing variants are researched additions for
        # 0.9.0 (es was one of the three packs that got them this pass).
        "artifact_phrases": [
            ("autorreferencia de chatbot (modelo de lenguaje)", "como modelo de lenguaje"),
            ("autorreferencia de chatbot (ia)", "como inteligencia artificial"),
            ("aviso de chatbot (sin acceso en tiempo real)", "no tengo acceso a internet en tiempo real"),
            ("aviso de chatbot (fecha de corte de conocimiento)", "mi conocimiento tiene fecha de corte"),
        ],
        "stopwords": frozenset((
            "el", "la", "los", "las", "de", "que", "y", "en", "un", "una",
            "es", "por", "para", "con", "como", "pero", "más", "muy", "sin",
            "sobre", "esto", "hay",
        )),
        "marks": "ñ¿¡",
        "em_dash_factor": 2.5,
    },
    "fr": {
        "name": "Français",
        "buzzwords": [
            "plongez", "plongeons", "tapisserie", "vaste",
            "paysage numérique", "de pointe", "à la pointe",
            "révolutionnaire", "disruptif", "disruptive", "transformateur",
            "transformatrice", "holistique", "synergie", "synergies",
            "paradigme", "changement de paradigme", "robuste", "fluide",
            "sans effort", "sans faille", "sans couture", "débloquer",
            "débloquez", "libérez", "exploitez", "favoriser", "favorise",
            "stimulez", "autonomiser", "donner les moyens", "primordial",
            "crucial", "méticuleux", "méticuleuse", "pierre angulaire",
            "captivant", "captivante", "en constante évolution",
            "un monde de possibilités", "une multitude de", "un éventail de",
            "une vaste gamme", "innovant", "innovante", "incontournable",
            "passer au niveau supérieur", "révolutionner",
        ],
        "phrases": [
            "il est important de noter", "il est important de souligner",
            "il convient de noter", "il convient de souligner",
            "il est essentiel de", "notez que", "en conclusion", "en résumé",
            "pour résumer", "en fin de compte", "au bout du compte",
            "dans le monde d'aujourd'hui", "à l'ère du numérique",
            "dans un monde en constante évolution", "plongeons dans",
            "explorons", "penchons-nous sur", "j'espère que cela vous aide",
            "j'espère que cela aide", "n'hésitez pas à",
            "excellente question", "très bonne question",
            # "en tant que modèle de langage" / "...intelligence
            # artificielle" moved to artifact_phrases below in 0.9.0.
            "libérez tout votre potentiel", "que vous soyez",
            "joue un rôle crucial", "joue un rôle essentiel",
            "une large gamme de", "lorsqu'il s'agit de",
            "bien plus qu'un simple", "l'époque où",
        ],
        "patterns": [
            ("construction 'pas seulement X, c'est Y'",
             r"(?i)\bce n[’']est pas (?:seulement|juste|simplement)\b"
             r"[^.?!\n]{1,70}?\bc[’']est\b", 3,
             "dites-le directement, sans le cadre de contraste"),
            ("bascule 'n'est pas X, c'est Y'",
             r"(?i)\bn[’']est pas\b[^.?!\n]{1,45}?\bc[’']est\b", 2,
             "dites simplement ce que c'est"),
            ("question rhétorique d'ouverture",
             r"(?im)^\s*(?:vous êtes-vous déjà demandé|avez-vous déjà"
             r"|et si|imaginez|qu[’']en serait-il si)\b", 2,
             "ouvrez sur l'idée, pas sur l'accroche"),
            ("empilement de précautions (peut/pourrait/souvent)",
             r"(?i)\b(?:peut|pourrait|pourraient|souvent|généralement"
             r"|typiquement|habituellement|sans doute|peut-être)\b", 0,
             "trop de précautions sonne évasif - affirmez ou coupez"),
        ],
        "artifact_phrases": [
            ("auto-référence de chatbot (modèle de langage)", "en tant que modèle de langage"),
            ("auto-référence de chatbot (ia)", "en tant qu'intelligence artificielle"),
        ],
        "stopwords": frozenset((
            "le", "la", "les", "des", "de", "et", "est", "une", "un", "dans",
            "que", "pour", "avec", "sur", "pas", "qui", "nous", "vous",
            "plus", "mais", "ce", "aux",
        )),
        "marks": "êœâ",
        "em_dash_factor": 2.5,
    },
    "de": {
        "name": "Deutsch",
        "buzzwords": [
            "nahtlos", "nahtlose", "nahtloser", "nahtloses", "ganzheitlich",
            "ganzheitliche", "ganzheitlichen", "synergie", "synergien",
            "paradigmenwechsel", "revolutionär", "revolutionäre",
            "bahnbrechend", "bahnbrechende", "wegweisend", "wegweisende",
            "transformativ", "transformative", "disruptiv", "disruptive",
            "entfesseln", "entfesselt", "freischalten", "maßgeschneidert",
            "maßgeschneiderte", "facettenreich", "facettenreiche",
            "akribisch", "akribische", "fesselnd", "fesselnde",
            "leistungsstark", "leistungsstarke", "zukunftsweisend",
            "zukunftsweisende", "revolutionieren", "eine fülle von",
            "eine vielzahl von", "robust", "robuste", "reiches geflecht",
            "auf die nächste stufe", "auf ein neues level",
            "von entscheidender bedeutung",
        ],
        "phrases": [
            # both orders: German V2 inverts the frame after a fronted
            # adverbial ("In der heutigen Welt ist es wichtig zu beachten")
            "es ist wichtig zu beachten", "ist es wichtig zu beachten",
            "es ist wichtig zu betonen", "ist es wichtig zu betonen",
            "es sei darauf hingewiesen", "es ist erwähnenswert",
            "zusammenfassend lässt sich sagen",
            "abschließend lässt sich sagen", "am ende des tages",
            "in der heutigen schnelllebigen welt", "im digitalen zeitalter",
            "in der heutigen zeit", "tauchen wir ein", "tauchen sie ein",
            "lassen sie uns eintauchen", "ich hoffe, das hilft",
            "zögern sie nicht", "gute frage", "ausgezeichnete frage",
            # "als ki-modell" / "als sprachmodell" moved to
            # artifact_phrases below in 0.9.0.
            "entfesseln sie ihr volles potenzial",
            "schöpfen sie ihr volles potenzial aus", "egal, ob sie",
            "ganz gleich, ob sie", "spielt eine entscheidende rolle",
            "spielt eine wichtige rolle", "eine breite palette",
            "eine große auswahl an", "wenn es darum geht",
            "mehr als nur ein", "die zeiten, in denen",
        ],
        "patterns": [
            ("'nicht nur X, sondern Y'-Konstruktion",
             r"(?i)\bnicht nur\b[^.?!\n]{1,70}?\bsondern\b", 3,
             "sag es direkt, ohne den Kontrastrahmen"),
            ("'ist nicht X, es ist Y'-Wendung",
             r"(?i)\bist (?:kein|keine|nicht)\b[^.?!\n]{1,45}?\bes ist\b", 2,
             "sag einfach, was es ist"),
            ("rhetorische Eröffnungsfrage",
             r"(?im)^\s*(?:haben sie sich jemals gefragt"
             r"|hast du dich jemals gefragt|stellen sie sich vor"
             r"|stell dir vor|was wäre, wenn|was wäre wenn)\b", 2,
             "beginn mit dem Punkt, nicht mit dem Köder"),
            ("Absicherungs-Stapel (kann/könnte/oft)",
             r"(?i)\b(?:kann|könnte|könnten|oft|typischerweise"
             r"|in der regel|üblicherweise|möglicherweise|vielleicht)\b", 0,
             "so viel Absicherung wirkt ausweichend - behaupten oder"
             " streichen"),
        ],
        # de was one of the three packs that got researched knowledge-
        # cutoff / no-browsing variants this pass (see AI_ARTIFACT_PHRASES).
        "artifact_phrases": [
            ("Chatbot-Selbstbezug (als KI-Modell)", "als ki-modell"),
            ("Chatbot-Selbstbezug (als Sprachmodell)", "als sprachmodell"),
            ("Chatbot-Hinweis (kein Echtzeitzugriff)", "ich habe keinen zugriff auf das internet in echtzeit"),
            ("Chatbot-Hinweis (Wissensstand-Stichtag)", "mein wissensstand reicht bis"),
        ],
        "stopwords": frozenset((
            "der", "die", "das", "und", "ist", "nicht", "mit", "für", "auf",
            "ein", "eine", "den", "von", "zu", "sich", "auch", "sind",
            "wird", "dass", "wie", "im", "es",
        )),
        "marks": "ßäö",
        "em_dash_factor": 1.5,
    },
    "pt-BR": {
        "name": "Português (Brasil)",
        "buzzwords": [
            "mergulhe", "mergulhemos", "tapeçaria", "vasto", "vasta",
            "panorama digital", "cenário digital", "vanguarda", "de ponta",
            "revolucionário", "revolucionária", "disruptivo", "disruptiva",
            "transformador", "transformadora", "holístico", "holística",
            "sinergia", "sinergias", "paradigma", "mudança de paradigma",
            "robusto", "robusta", "sem esforço", "sem atritos",
            "sem complicações", "desbloquear", "desbloqueie",
            "potencializar", "potencialize", "impulsionar", "impulsione",
            "alavancar", "alavanque", "fomentar", "fomenta", "capacitar",
            "capacite", "empoderar", "empodere", "primordial", "crucial",
            "meticuloso", "meticulosa", "pedra angular", "cativante",
            "envolvente", "em constante evolução", "um leque de",
            "uma ampla gama", "um mundo de possibilidades", "inovador",
            "inovadora", "experiência fluida", "próximo nível",
            "divisor de águas",
        ],
        "phrases": [
            "é importante ressaltar", "é importante destacar",
            "é importante notar", "vale ressaltar", "vale destacar",
            "vale a pena destacar", "cabe destacar", "em resumo",
            "em conclusão", "para concluir", "em suma",
            "no final das contas", "no mundo atual", "na era digital",
            "no cenário atual", "no acelerado mundo", "mergulhe em",
            "vamos mergulhar", "vamos explorar", "espero que isso ajude",
            "espero ter ajudado", "não hesite em",
            "sinta-se à vontade para", "fique à vontade para",
            "ótima pergunta", "excelente pergunta",
            # "como modelo de linguagem" / "como inteligência artificial"
            # moved to artifact_phrases below in 0.9.0.
            "desbloqueie todo o seu potencial",
            "libere todo o seu potencial", "seja você", "quer você seja",
            "desempenha um papel crucial",
            "desempenha um papel fundamental", "uma ampla variedade de",
            "quando se trata de", "mais do que um simples",
            "ficaram para trás os dias", "longe vão os dias",
        ],
        "patterns": [
            ("construção 'não é apenas X, mas Y'",
             r"(?i)\bnão (?:é|se trata) (?:apenas|só|somente)\b"
             r"[^.?!\n]{1,70}?\b(?:mas|é)\b", 3,
             "diga diretamente, sem o quadro de contraste"),
            ("virada 'não é X, é Y'",
             r"(?i)\bnão é\b[^.?!\n]{1,45}?\bé\b", 2,
             "diga o que é, sem o rodeio"),
            ("pergunta retórica de abertura",
             r"(?im)^\s*(?:você já se perguntou|já se perguntou"
             r"|já imaginou|imagine (?:um|uma|que)|e se)\b", 2,
             "abra com o ponto, não com a isca"),
            ("pilha de ressalvas (pode/poderia/frequentemente)",
             r"(?i)\b(?:pode|poderia|poderiam|frequentemente|geralmente"
             r"|tipicamente|normalmente|possivelmente|talvez)\b", 0,
             "tanta ressalva soa evasivo - afirme ou corte"),
        ],
        "artifact_phrases": [
            ("autorreferência de chatbot (modelo de linguagem)", "como modelo de linguagem"),
            ("autorreferência de chatbot (ia)", "como inteligência artificial"),
        ],
        "stopwords": frozenset((
            "o", "os", "as", "de", "que", "e", "em", "um", "uma", "é",
            "não", "para", "com", "mais", "você", "são", "como", "mas",
            "isso", "foi", "tem", "muito",
        )),
        "marks": "ãõ",
        "em_dash_factor": 2.5,
    },
    "it": {
        "name": "Italiano",
        "buzzwords": [
            "immergiti", "immergersi", "immergiamoci", "arazzo", "vasto",
            "vasta", "panorama digitale", "avanguardia", "all'avanguardia",
            "rivoluzionario", "rivoluzionaria", "dirompente", "trasformativo",
            "trasformativa", "olistico", "olistica", "sinergia", "sinergie",
            "paradigma", "cambio di paradigma", "robusto", "robusta",
            "senza sforzo", "senza soluzione di continuità", "senza intoppi",
            "sbloccare", "sblocca", "sfruttare", "sfrutta", "potenziare",
            "potenzia", "cruciale", "meticoloso", "meticolosa",
            "pietra miliare", "pietra angolare", "accattivante",
            "coinvolgente", "in continua evoluzione", "una vasta gamma",
            "un ventaglio di", "una miriade di", "innovativo", "innovativa",
            "esperienza fluida", "livello successivo", "punto di svolta",
        ],
        "phrases": [
            "è importante sottolineare", "è importante notare",
            "è importante evidenziare", "vale la pena sottolineare",
            "vale la pena notare", "va sottolineato", "va notato",
            "in conclusione", "in sintesi", "per riassumere",
            "in definitiva", "alla fine della giornata",
            "nel mondo di oggi", "nell'era digitale",
            "nel panorama attuale", "nel frenetico mondo",
            "immergiamoci in", "esploriamo", "approfondiamo",
            "spero che questo aiuti", "spero che questo ti sia utile",
            "non esitare a", "sentiti libero di", "ottima domanda",
            # "come modello linguistico" / "come intelligenza artificiale"
            # moved to artifact_phrases below in 0.9.0.
            "sblocca tutto il tuo potenziale",
            "libera tutto il tuo potenziale", "che tu sia",
            "svolge un ruolo cruciale", "svolge un ruolo fondamentale",
            "gioca un ruolo cruciale", "un'ampia gamma di",
            "quando si tratta di", "molto più di un semplice",
            "sono lontani i tempi",
        ],
        "patterns": [
            ("costruzione 'non solo X, ma Y'",
             r"(?i)\bnon (?:è|si tratta) (?:solo|soltanto|semplicemente)\b"
             r"[^.?!\n]{1,70}?\b(?:ma|è)\b", 3,
             "dillo direttamente, senza la cornice di contrasto"),
            ("svolta 'non è X, è Y'",
             r"(?i)\bnon è\b[^.?!\n]{1,45}?\bè\b", 2,
             "di' semplicemente cos'è"),
            ("domanda retorica di apertura",
             r"(?im)^\s*(?:ti sei mai chiesto|vi siete mai chiesti|hai mai"
             r"|immagina (?:un|una|che)|e se)\b", 2,
             "apri con il punto, non con l'esca"),
            ("pila di cautele (può/potrebbe/spesso)",
             r"(?i)\b(?:può|potrebbe|potrebbero|spesso|generalmente"
             r"|tipicamente|solitamente|possibilmente|forse)\b", 0,
             "troppe cautele suonano evasive - afferma o taglia"),
        ],
        "artifact_phrases": [
            ("autoreferenza del chatbot (modello linguistico)", "come modello linguistico"),
            ("autoreferenza del chatbot (ia)", "come intelligenza artificiale"),
        ],
        "stopwords": frozenset((
            "il", "la", "le", "gli", "di", "che", "e", "è", "per", "con",
            "non", "un", "una", "sono", "del", "della", "più", "anche",
            "come", "ma", "questo", "si",
        )),
        "marks": "òì",
        "em_dash_factor": 2.5,
    },
    "nl": {
        "name": "Nederlands",
        "buzzwords": [
            "rijk tapijt", "baanbrekend", "baanbrekende", "revolutionair",
            "revolutionaire", "disruptief", "disruptieve", "transformatief",
            "transformatieve", "holistisch", "holistische", "synergie",
            "paradigma", "paradigmaverschuiving", "robuust", "robuuste",
            "naadloos", "naadloze", "moeiteloos", "moeiteloze",
            "ontgrendel", "ontgrendelen", "ontketen", "ontketenen",
            "benutten", "bevorderen", "bevordert",
            "naar een hoger niveau", "cruciaal", "cruciale", "nauwgezet",
            "nauwgezette", "boeiend", "boeiende", "meeslepend",
            "meeslepende", "voortdurend evoluerende", "steeds veranderende",
            "een breed scala", "een schat aan",
            "een wereld van mogelijkheden", "innovatief", "innovatieve",
            "toekomstbestendig", "toekomstbestendige", "game-changer",
        ],
        "phrases": [
            "het is belangrijk om op te merken",
            "het is belangrijk te vermelden", "het is vermeldenswaard",
            "het is de moeite waard om", "merk op dat", "kortom",
            "samenvattend", "tot slot", "in conclusie",
            "aan het eind van de dag",
            "in de snel veranderende wereld van vandaag",
            "in het digitale tijdperk", "in de wereld van vandaag",
            "laten we duiken in", "laten we eens kijken naar",
            "duik in de wereld van", "ik hoop dat dit helpt",
            "aarzel niet om", "voel je vrij om", "goede vraag",
            "uitstekende vraag",
            # "als taalmodel" / "als ai-model" moved to artifact_phrases
            # below in 0.9.0.
            "ontgrendel je volledige potentieel",
            "ontketen je volledige potentieel", "of je nu",
            "speelt een cruciale rol", "speelt een belangrijke rol",
            "een breed scala aan", "als het gaat om",
            "het is niet zomaar", "meer dan alleen een",
            "voorbij zijn de dagen",
        ],
        "patterns": [
            ("'niet alleen X, maar Y'-constructie",
             r"(?i)\bniet (?:alleen|enkel|slechts)\b[^.?!\n]{1,70}?"
             r"\bmaar\b", 3,
             "zeg het gewoon, zonder het contrastframe"),
            ("'is geen X, het is Y'-wending",
             r"(?i)\bis (?:geen|niet)\b[^.?!\n]{1,45}?\bhet is\b", 2,
             "zeg gewoon wat het is"),
            ("retorische openingsvraag",
             r"(?im)^\s*(?:heb je je ooit afgevraagd"
             r"|heeft u zich ooit afgevraagd|stel je voor"
             r"|stelt u zich voor|wat als)\b", 2,
             "open met het punt, niet met de lokker"),
            ("stapel voorbehouden (kan/zou kunnen/vaak)",
             r"(?i)\b(?:kan|kunnen|zou kunnen|vaak|meestal|doorgaans"
             r"|over het algemeen|mogelijk|misschien)\b", 0,
             "zoveel voorbehoud leest ontwijkend - beweer of schrap"),
        ],
        "artifact_phrases": [
            ("chatbot-zelfverwijzing (taalmodel)", "als taalmodel"),
            ("chatbot-zelfverwijzing (ai-model)", "als ai-model"),
        ],
        "stopwords": frozenset((
            "de", "het", "een", "en", "van", "is", "dat", "niet", "met",
            "voor", "op", "zijn", "aan", "ook", "maar", "naar", "deze",
            "wordt", "uit", "bij", "dan", "te",
        )),
        "marks": "",
        "em_dash_factor": 1.0,
    },
    "ru": {
        "name": "Русский",
        "buzzwords": [
            "погрузиться", "погрузитесь", "погружение", "многогранный",
            "многогранная", "бесшовный", "бесшовная", "бесшовно",
            "целостный", "целостная", "синергия", "парадигма",
            "смена парадигмы", "революционный", "революционная",
            "инновационный", "инновационная", "преобразующий",
            "преобразующая", "трансформационный", "раскрыть потенциал",
            "раскройте свой потенциал", "экосистема", "ландшафт",
            "передовой", "передовые", "ключевую роль", "широкий спектр",
            "неотъемлемая часть", "мощный инструмент",
            "гармонично сочетает", "безграничные возможности",
            "на переднем крае", "краеугольный камень",
            "по-настоящему уникальный",
            # Bureaucratic determiners and nominalizations (канцелярит) -
            # 0.9.0 research pass. Genuinely common in formal/official
            # Russian registers too, which is why these are calibrated
            # against a formal-Russian human sample in eval/corpus/human
            # rather than shipped on faith - see eval/README.md.
            "данный", "указанный", "вышеупомянутый",
            "осуществление", "проведение", "обеспечение",
        ],
        "phrases": [
            "важно отметить", "стоит отметить", "следует отметить",
            "нельзя не отметить", "в современном мире",
            "в быстро меняющемся мире", "давайте погрузимся",
            "давайте разберемся", "в заключение", "подводя итог",
            "в двух словах",
            # "как языковая модель" / "как искусственный интеллект" moved
            # to artifact_phrases below in 0.9.0.
            "надеюсь, это поможет",
            "не стесняйтесь", "отличный вопрос", "когда речь заходит о",
            "широкий спектр возможностей", "открывает новые горизонты",
            "играет ключевую роль", "играет важную роль",
            "хочу подчеркнуть",
            # 0.9.0 opener cliché.
            "в эпоху цифровизации",
        ],
        "patterns": [
            ("конструкция 'не только X, но и Y'",
             r"(?i)\bне только\b[^.?!\n]{1,70}?\bно и\b", 3,
             "скажи прямо, без рамки контраста"),
            # Russian doesn't repeat the copula the way English/Romance/
            # German do ("это не X, это Y") - it drops straight into the
            # contrastive "а" after a comma, so the flip is "это не X, а Y".
            ("оборот 'это не X, а Y'",
             r"(?i)\bэто не\b[^.?!\n]{1,45}?,\s*а\b", 2,
             "просто скажи, что это"),
            ("риторический вопрос-зачин",
             r"(?im)^\s*(?:задумывались ли вы|а что если"
             r"|представьте себе|представьте|вы когда-нибудь)\b", 2,
             "начни с сути, а не с крючка"),
            ("стопка оговорок (может/вероятно/обычно)",
             r"(?i)\b(?:может|могут|можно|вероятно|как правило|обычно"
             r"|зачастую|возможно|порой)\b", 0,
             "столько оговорок звучит уклончиво - утверждай или убери"),
        ],
        # ru was one of the three packs that got researched knowledge-
        # cutoff / no-browsing variants this pass (see AI_ARTIFACT_PHRASES).
        "artifact_phrases": [
            ("самоссылка чат-бота (языковая модель)", "как языковая модель"),
            ("самоссылка чат-бота (ИИ)", "как искусственный интеллект"),
            ("оговорка чат-бота (нет доступа в реальном времени)", "у меня нет доступа к интернету в реальном времени"),
            ("оговорка чат-бота (дата отсечки знаний)", "мои знания ограничены датой обучения"),
        ],
        # "является" (is/serves as) is an ordinary Russian copula verb, but
        # LLM Russian leans on it as a formal-register crutch well past the
        # rate of ordinary prose - excess over a calibrated per-1,000-word
        # allowance scores, the same density-allowance shape as em dashes.
        # See YAVLYAETSYA_ALLOWANCE_PER_1K near analyze().
        "density_crutch": ("является",),
        "stopwords": frozenset((
            "и", "в", "не", "на", "с", "что", "как", "это", "для", "но",
            "к", "по", "из", "о", "же", "только", "все", "от", "за",
            "тоже",
        )),
        "marks": "ыэъ",
        "em_dash_factor": 2.5,
    },
    "uk": {
        "name": "Українська",
        "buzzwords": [
            "занурмося", "зануртеся", "зануритися", "багатогранний",
            "багатогранна", "безшовний", "безшовна", "цілісний",
            "цілісна", "синергія", "парадигма", "зміна парадигми",
            "революційний", "революційна", "інноваційний", "інноваційна",
            "трансформаційний", "перетворювальний", "розкрити потенціал",
            "розкрийте свій потенціал", "екосистема", "ландшафт",
            "передовий", "передові", "ключову роль", "широкий спектр",
            "невід'ємна частина", "потужний інструмент",
            "гармонійно поєднує", "безмежні можливості",
            "на передньому краї", "наріжний камінь",
            "по-справжньому унікальний",
        ],
        "phrases": [
            "важливо зазначити", "варто зазначити", "слід зазначити",
            "у сучасному світі", "у швидкоплинному світі",
            "давайте зануримося", "давайте розберемося", "підсумовуючи",
            "на завершення", "у двох словах",
            # "як мовна модель" / "як штучний інтелект" moved to
            # artifact_phrases below in 0.9.0.
            "сподіваюся, це допоможе",
            "не соромтеся", "чудове запитання", "коли справа доходить до",
            "широкий спектр можливостей", "відкриває нові горизонти",
            "відіграє ключову роль", "відіграє важливу роль",
            "хочу підкреслити",
        ],
        "patterns": [
            ("конструкція 'не тільки X, а й Y'",
             r"(?i)\bне (?:тільки|лише)\b[^.?!\n]{1,70}?"
             r"\bа (?:й|також)\b", 3,
             "скажи прямо, без рамки контрасту"),
            # Same insight as Russian: no repeated copula, just the
            # contrastive "а" after a comma.
            ("зворот 'це не X, а Y'",
             r"(?i)\bце не\b[^.?!\n]{1,45}?,\s*а\b", 2,
             "просто скажи, що це"),
            ("риторичне питання-зачин",
             r"(?im)^\s*(?:чи замислювались ви|чи замислювалися ви"
             r"|а що якщо|уявіть собі|уявіть)\b", 2,
             "почни із суті, а не з гачка"),
            ("стос застережень (може/ймовірно/зазвичай)",
             r"(?i)\b(?:може|можуть|можна|ймовірно|як правило|зазвичай"
             r"|часто|можливо)\b", 0,
             "стільки застережень звучить ухильно - стверджуй або "
             "прибери"),
        ],
        "artifact_phrases": [
            ("самопосилання чат-бота (мовна модель)", "як мовна модель"),
            ("самопосилання чат-бота (ШІ)", "як штучний інтелект"),
        ],
        "stopwords": frozenset((
            "і", "це", "що", "як", "для", "з", "на", "не", "у", "до",
            "або", "але", "який", "від", "вже", "теж", "зі", "лише",
            "також", "тільки", "за",
        )),
        "marks": "іїєґ",
        "em_dash_factor": 2.5,
    },
    "pl": {
        "name": "Polski",
        "buzzwords": [
            "zanurz się", "zanurzmy się", "zagłębmy się",
            "wielowymiarowy", "wielowymiarowa", "bezproblemowy",
            "bezproblemowa", "płynne doświadczenie", "kompleksowy",
            "kompleksowa", "solidny", "solidna", "innowacyjny",
            "innowacyjna", "przełomowy", "przełomowa", "transformacyjny",
            "transformacyjna", "holistyczny", "holistyczna", "synergia",
            "paradygmat", "zmiana paradygmatu", "odblokować potencjał",
            "odblokuj swój potencjał", "krajobraz cyfrowy",
            "świat możliwości", "szeroka gama", "mnóstwo możliwości",
            "wzmacniać", "na najwyższym poziomie", "nieoceniony",
            "kamień węgielny", "wyjątkowy", "na czele",
        ],
        "phrases": [
            "warto zauważyć", "warto podkreślić", "należy zauważyć",
            "warto zaznaczyć", "w dzisiejszym świecie",
            "w dzisiejszym dynamicznie zmieniającym się świecie",
            "w erze cyfrowej", "zanurzmy się w", "zagłębmy się w",
            "podsumowując", "reasumując", "na koniec dnia",
            "mam nadzieję, że to pomoże", "nie wahaj się", "śmiało pytaj",
            "świetne pytanie",
            # "jako model językowy" / "jako sztuczna inteligencja" moved
            # to artifact_phrases below in 0.9.0.
            "kiedy przychodzi do",
            "szeroki wachlarz", "otwiera nowe możliwości",
            "więcej niż tylko", "niezależnie od tego, czy jesteś",
        ],
        "patterns": [
            ("konstrukcja 'nie tylko X, ale i Y'",
             r"(?i)\bnie tylko\b[^.?!\n]{1,70}?"
             r"\bale (?:i|także|również)\b", 3,
             "powiedz to wprost, bez ramy kontrastu"),
            # Polish leans on "tylko" (rather) for the flip, not a repeated
            # copula - "to nie X, tylko Y", closer to Russian's "а" than to
            # the Romance/Germanic "it's" repeat.
            ("zwrot 'to nie X, tylko Y'",
             r"(?i)\bto nie\b[^.?!\n]{1,45}?\btylko\b", 2,
             "powiedz wprost, czym to jest"),
            ("retoryczne pytanie otwierające",
             r"(?im)^\s*(?:czy zastanawiałeś się|czy zastanawiałaś się"
             r"|a co jeśli|wyobraź sobie|wyobraźcie sobie)\b", 2,
             "zacznij od sedna, nie od haczyka"),
            ("stos zastrzeżeń (może/często/zazwyczaj)",
             r"(?i)\b(?:może|mogą|często|zazwyczaj|zwykle"
             r"|prawdopodobnie|ewentualnie|ogólnie)\b", 0,
             "tyle zastrzeżeń brzmi wymijająco - stwierdź albo wytnij"),
        ],
        "artifact_phrases": [
            ("autoreferencja chatbota (model językowy)", "jako model językowy"),
            ("autoreferencja chatbota (SI)", "jako sztuczna inteligencja"),
        ],
        "stopwords": frozenset((
            "i", "w", "na", "nie", "z", "do", "że", "się", "to", "jest",
            "jak", "dla", "po", "ale", "czy", "o", "od", "za", "tak",
            "przez",
        )),
        "marks": "łżą",
        "em_dash_factor": 2.5,
    },
    "cs": {
        "name": "Čeština",
        "buzzwords": [
            "ponořte se", "ponořme se", "mnohostranný", "mnohostranná",
            "bezproblémový", "bezproblémová", "plynulý zážitek",
            "komplexní", "robustní", "inovativní", "průlomový",
            "průlomová", "převratný", "transformační", "holistický",
            "holistická", "synergie", "paradigma", "změna paradigmatu",
            "odemkněte svůj potenciál", "odemknout potenciál",
            "ekosystém", "digitální krajina", "klíčovou roli",
            "široká škála", "nekonečné možnosti", "neocenitelný",
            "na další úroveň", "posunout na další úroveň",
            "přelomový moment", "jedinečný", "na špici",
        ],
        "phrases": [
            "je důležité poznamenat", "je důležité zmínit",
            "stojí za zmínku", "stojí za povšimnutí", "v dnešním světě",
            "v dnešním uspěchaném světě", "v digitální době",
            "ponořme se do", "pojďme prozkoumat",
            "doufám, že to pomůže", "neváhejte", "skvělá otázka",
            # "jako jazykový model" / "jako umělá inteligence" moved to
            # artifact_phrases below in 0.9.0.
            "když přijde na", "široká škála možností",
            "otevírá nové možnosti", "hraje klíčovou roli",
            "hraje zásadní roli", "víc než jen",
        ],
        "patterns": [
            ("konstrukce 'nejen X, ale i Y'",
             r"(?i)\bnejen\b[^.?!\n]{1,70}?\bale\s+(?:i|také)\b", 3,
             "řekni to napřímo, bez rámce kontrastu"),
            ("obrat 'není to X, je to Y'",
             r"(?i)\bnení to\b[^.?!\n]{1,45}?\bje to\b", 2,
             "řekni prostě, co to je"),
            ("řečnická otázka na úvod",
             r"(?im)^\s*(?:přemýšleli jste někdy|napadlo vás někdy"
             r"|co kdyby|představte si)\b", 2,
             "začni podstatou, ne návnadou"),
            ("hromada výhrad (může/často/obvykle)",
             r"(?i)\b(?:může|mohou|často|obvykle|obecně"
             r"|pravděpodobně|možná)\b", 0,
             "tolik výhrad zní vyhýbavě - tvrď, nebo škrtni"),
        ],
        "artifact_phrases": [
            ("sebeodkaz chatbota (jazykový model)", "jako jazykový model"),
            ("sebeodkaz chatbota (UI)", "jako umělá inteligence"),
        ],
        "stopwords": frozenset((
            "a", "v", "na", "je", "se", "to", "kde", "pro", "před",
            "avšak", "co", "že", "od", "mezi", "také", "si", "už",
            "když", "nebo", "jen",
        )),
        "marks": "řěů",
        "em_dash_factor": 1.0,
    },
    "tr": {
        "name": "Türkçe",
        "buzzwords": [
            "dalın", "dalalım", "kapsamlı", "sorunsuz", "bütünsel",
            "sinerji", "paradigma", "paradigma değişimi", "yenilikçi",
            "devrim niteliğinde", "çığır açan", "dönüştürücü",
            "potansiyelinizi ortaya çıkarın",
            "potansiyelinizi açığa çıkarın", "eşsiz", "vazgeçilmez",
            "köşe taşı", "geniş bir yelpazesi",
            "bir sonraki seviyeye taşıyın", "dijital dönüşüm",
            "dijital dünya", "güçlü bir araç", "kilit rol oynar",
            "hayati önem taşır", "sınırsız olanaklar", "öncü",
            "çok yönlü", "kesintisiz deneyim", "güçlendirmek",
            "potansiyeli ortaya çıkarmak", "çığır açıcı",
            "eşi benzeri görülmemiş",
        ],
        "phrases": [
            "önemle belirtmek gerekir ki", "belirtmek gerekir ki",
            "unutulmamalıdır ki", "günümüzün hızlı dünyasında",
            "günümüz dünyasında", "sonuç olarak", "kısacası", "özetle",
            # "bir yapay zeka olarak" / "bir dil modeli olarak" moved to
            # artifact_phrases below in 0.9.0.
            "harika bir soru", "mükemmel bir soru", "çekinmeyin",
            "yardımcı olması umarım", "yardımcı olacağını umuyorum",
            "hadi dalalım", "gelin inceleyelim",
            "söz konusu olduğunda", "sadece bir araç değil",
            "günün sonunda", "artık geride kaldı",
        ],
        "patterns": [
            ("'sadece X değil, aynı zamanda Y' yapısı",
             r"(?i)\bsadece\b[^.?!\n]{1,70}?\baynı zamanda\b", 3,
             "çerçevelemeden doğrudan söyle"),
            # The Turkish copula is a suffix (-dır/-dir/-dur/-dür, plus
            # devoiced -tır/-tir/-tur/-tür after voiceless stems), not a
            # separate word, so the flip is matched as "değil" followed
            # by a word carrying that suffix rather than a repeated "is".
            ("'X değil, Y'dır' dönüşü",
             r"(?i)\bdeğil\b[^.?!\n]{1,45}?"
             r"\w+(?:dır|dir|dur|dür|tır|tir|tur|tür)\b", 2,
             "ne olduğunu doğrudan söyle"),
            ("retorik açılış sorusu",
             r"(?im)^\s*(?:hiç merak ettiniz mi|hiç düşündünüz mü"
             r"|hayal edin|bir düşünün)\b", 2,
             "kancayla değil, asıl noktayla aç"),
            # "-ebilir/-abilir" (can/may) is also a suffix, not a
            # standalone word, so it's matched the same way; the rest are
            # ordinary hedge adverbs.
            ("çekince yığını (-ebilir/genellikle/belki)",
             r"(?i)\b(?:\w*(?:abilir|ebilir)|muhtemelen|genellikle"
             r"|genelde|sıklıkla|belki|büyük ihtimalle)\b", 0,
             "bu kadar çekince kaçamak gibi duruyor - ya net konuş ya "
             "da çıkar"),
        ],
        "artifact_phrases": [
            ("chatbot öz-referansı (yapay zeka)", "bir yapay zeka olarak"),
            ("chatbot öz-referansı (dil modeli)", "bir dil modeli olarak"),
        ],
        "stopwords": frozenset((
            "ve", "bir", "bu", "için", "ile", "gibi", "ama", "veya",
            "çok", "daha", "olan", "her", "kadar", "sonra", "önce",
            "şey", "ne", "en", "mi",
        )),
        "marks": "ışğ",
        "em_dash_factor": 2.5,
    },
    "sv": {
        "name": "Svenska",
        "buzzwords": [
            "dyk ner i", "dyk djupare", "sömlös", "sömlöst", "holistisk",
            "holistiskt", "synergi", "synergieffekter", "paradigm",
            "paradigmskifte", "banbrytande", "omfattande", "robust",
            "frigör din potential", "frigöra potentialen", "oumbärlig",
            "hörnsten", "innovativ", "revolutionerande", "transformativ",
            "mångfacetterad", "till nästa nivå", "ett brett utbud",
            "en uppsjö av", "digital transformation", "dynamisk",
            "kraftfullt verktyg", "gränslösa möjligheter",
            "banar väg för", "spetskompetens",
        ],
        "phrases": [
            "det är viktigt att notera", "det är värt att notera",
            "värt att nämna", "i dagens snabbrörliga värld",
            "i dagens digitala värld", "sammanfattningsvis",
            "i slutändan",
            # "som en ai" / "som en språkmodell" moved to artifact_phrases
            # below in 0.9.0.
            "tveka inte", "bra fråga", "utmärkt fråga",
            "när det kommer till", "ett brett utbud av",
            "spelar en avgörande roll", "spelar en viktig roll",
            "mer än bara ett verktyg", "jag hoppas att detta hjälper",
            "tveka inte att höra av dig", "öppnar upp nya möjligheter",
        ],
        "patterns": [
            ("konstruktionen 'inte bara X utan också Y'",
             r"(?i)\binte bara\b[^.?!\n]{1,70}?\butan (?:också|även)\b",
             3, "säg det rakt ut, utan kontrastramen"),
            ("vändningen 'är inte X, det är Y'",
             r"(?i)\bär inte\b[^.?!\n]{1,45}?\bdet är\b", 2,
             "säg helt enkelt vad det är"),
            ("retorisk inledningsfråga",
             r"(?im)^\s*(?:har du någonsin undrat"
             r"|har du någonsin funderat|tänk om|föreställ dig)\b", 2,
             "öppna med poängen, inte med kroken"),
            ("garderingsstapel (kan/ofta/vanligtvis)",
             r"(?i)\b(?:kan|skulle kunna|ofta|vanligtvis|i allmänhet"
             r"|möjligen|kanske)\b", 0,
             "så mycket gardering läses undvikande - hävda eller stryk"),
        ],
        "artifact_phrases": [
            ("chatbotens självreferens (AI)", "som en ai"),
            ("chatbotens självreferens (språkmodell)", "som en språkmodell"),
        ],
        "stopwords": frozenset((
            "och", "är", "inte", "att", "det", "som", "för", "med",
            "jag", "du", "han", "hon", "vi", "ni", "de", "men", "också",
            "mycket", "kan", "vara",
        )),
        "marks": "åäö",
        "em_dash_factor": 1.0,
    },
    "ro": {
        "name": "Română",
        "buzzwords": [
            "scufundă-te", "scufundă-te în", "cuprinzător",
            "cuprinzătoare", "fără cusur", "impecabil", "holistic",
            "holistică", "sinergie", "paradigmă", "schimbare de paradigmă",
            "inovator", "inovatoare", "revoluționar", "revoluționară",
            "transformator", "transformatoare",
            "deblochează-ți potențialul", "multifațetat",
            "o gamă largă de", "la următorul nivel", "de neprețuit",
            "piatră de temelie", "remarcabil", "de neegalat",
            "peisaj digital", "ecosistem", "rol esențial", "rol crucial",
            "instrument puternic", "posibilități nelimitate", "de vârf",
        ],
        "phrases": [
            "este important de menționat", "merită menționat",
            "trebuie remarcat", "în lumea de azi în ritm alert",
            "în era digitală", "pe scurt", "în concluzie",
            "la sfârșitul zilei",
            # "ca inteligență artificială" / "ca model lingvistic" moved
            # to artifact_phrases below in 0.9.0.
            "nu ezita să", "sper că te ajută",
            "întrebare excelentă", "întrebare grozavă",
            "atunci când vine vorba de", "joacă un rol esențial",
            "joacă un rol crucial", "nu doar un instrument",
            "o gamă largă de opțiuni", "deschide noi orizonturi",
        ],
        "patterns": [
            ("construcția 'nu doar X, ci și Y'",
             r"(?i)\bnu doar\b[^.?!\n]{1,70}?\b(?:ci și|dar și)\b", 3,
             "spune-o direct, fără cadrul de contrast"),
            ("răsturnarea 'nu este X, este Y'",
             r"(?i)\bnu este\b[^.?!\n]{1,45}?\beste\b", 2,
             "spune pur și simplu ce este"),
            ("întrebare retorică de deschidere",
             r"(?im)^\s*(?:te-ai întrebat vreodată"
             r"|v-ați întrebat vreodată|ce-ar fi dacă|imaginează-ți"
             r"|imaginați-vă)\b", 2,
             "deschide cu ideea, nu cu cârligul"),
            ("stivă de rezerve (poate/adesea/de obicei)",
             r"(?i)\b(?:poate|ar putea|adesea|de obicei|în general"
             r"|probabil|posibil)\b", 0,
             "atâtea rezerve sună evaziv - afirmă sau taie"),
        ],
        "artifact_phrases": [
            ("auto-referință de chatbot (IA)", "ca inteligență artificială"),
            ("auto-referință de chatbot (model lingvistic)", "ca model lingvistic"),
        ],
        "stopwords": frozenset((
            "și", "în", "de", "un", "este", "cu", "care", "pentru",
            "nu", "pe", "mai", "dar", "sau", "din", "ca", "se", "să",
            "dacă", "foarte", "fără",
        )),
        "marks": "ăâîșț",
        "em_dash_factor": 2.5,
    },
    "hu": {
        "name": "Magyar",
        "buzzwords": [
            "merülj el", "merüljünk el", "zökkenőmentes", "holisztikus",
            "szinergia", "paradigma", "paradigmaváltás", "innovatív",
            "forradalmi", "korszakalkotó", "átalakító", "átfogó",
            "robusztus", "rejlő potenciál", "kulcsszerepet játszik",
            "széles skálája", "a következő szintre", "felbecsülhetetlen",
            "sarokköve", "egyedülálló", "nélkülözhetetlen", "sokrétű",
            "korlátlan lehetőségek", "úttörő", "digitális átalakulás",
            "dinamikus", "hatékony eszköz", "mérföldkő",
            "új szintre emeli",
        ],
        "phrases": [
            "fontos megjegyezni", "érdemes megjegyezni",
            "fontos kiemelni", "napjaink rohanó világában",
            "a mai digitális világban", "összefoglalva", "végezetül",
            # "mesterséges intelligenciaként" / "nyelvi modellként" moved
            # to artifact_phrases below in 0.9.0.
            "ne habozz", "remélem, ez segít", "nagyszerű kérdés",
            "kiváló kérdés", "amikor arról van szó",
            "szabadítsd fel a benned rejlő potenciált",
            "nem csak egy eszköz", "a nap végén", "új távlatokat nyit",
            "kulcsfontosságú szerepet tölt be",
        ],
        # Hungarian doesn't split "not just X but Y" and "isn't X it's Y"
        # into two separate idioms the way Indo-European languages do -
        # both lean on the same "nem X, hanem Y" contrast frame, with
        # "csak"/"is" as an optional intensifier rather than a different
        # construction. Forcing a second, separate flip pattern here would
        # just double-count the same sentence, so this pack ships 3.
        "patterns": [
            ("'nem csak X, hanem Y is' szerkezet",
             r"(?i)\bnem csak\b[^.?!\n]{1,70}?\bhanem\b", 3,
             "mondd ki egyenesen, kontrasztkeret nélkül"),
            ("retorikai nyitókérdés",
             r"(?im)^\s*(?:gondolkodtál már azon"
             r"|elgondolkodtál már azon|mi lenne ha|képzeld el"
             r"|képzeljük el)\b", 2,
             "a lényeggel nyiss, ne a csalival"),
            ("óvatoskodás-halom (lehet/gyakran/általában)",
             r"(?i)\b(?:lehet|lehetnek|gyakran|általában"
             r"|valószínűleg|esetleg)\b", 0,
             "ennyi óvatoskodás kitérőnek hat - állítsd, vagy húzd ki"),
        ],
        "artifact_phrases": [
            ("chatbot önhivatkozás (MI)", "mesterséges intelligenciaként"),
            ("chatbot önhivatkozás (nyelvi modell)", "nyelvi modellként"),
        ],
        "stopwords": frozenset((
            "és", "a", "az", "nem", "hogy", "van", "egy", "is", "de",
            "mint", "csak", "vagy", "ha", "meg", "már", "még", "kell",
            "majd", "ez", "azt",
        )),
        "marks": "őű",
        "em_dash_factor": 1.5,
    },
    "fi": {
        "name": "Suomi",
        "buzzwords": [
            "sukella", "sukella syvemmälle", "kokonaisvaltainen",
            "saumaton", "saumattomasti", "synergia", "paradigma",
            "paradigman muutos", "innovatiivinen", "mullistava",
            "vallankumouksellinen", "muutosvoimainen", "kattava",
            "vapauta potentiaalisi", "piilevä potentiaali",
            "avainasemassa", "laaja valikoima", "seuraavalle tasolle",
            "korvaamaton", "kulmakivi", "ainutlaatuinen",
            "välttämätön", "monipuolinen", "rajattomat mahdollisuudet",
            "edelläkävijä", "digitaalinen murros", "dynaaminen",
            "tehokas työkalu",
        ],
        "phrases": [
            "on tärkeää huomioida", "kannattaa muistaa",
            "on syytä mainita", "nykypäivän nopeatempoisessa maailmassa",
            "tämän päivän digitaalisessa maailmassa", "yhteenvetona",
            "loppujen lopuksi",
            # "tekoälynä" / "kielimallina" moved to artifact_phrases below
            # in 0.9.0.
            "älä epäröi", "toivottavasti tästä on apua",
            "loistava kysymys", "erinomainen kysymys", "kun kyse on",
            "laaja valikoima vaihtoehtoja", "ei vain työkalu",
            "avaa uusia mahdollisuuksia", "vie seuraavalle tasolle",
        ],
        "patterns": [
            ("'ei ainoastaan X vaan myös Y' -rakenne",
             r"(?i)\bei ainoastaan\b[^.?!\n]{1,70}?\bvaan myös\b", 3,
             "sano se suoraan, ilman vastakkainasettelua"),
            ("'ei ole X, vaan Y' -käänne",
             r"(?i)\bei ole\b[^.?!\n]{1,45}?\bvaan\b", 2,
             "sano suoraan mitä se on"),
            ("retorinen avauskysymys",
             r"(?im)^\s*(?:oletko koskaan miettinyt"
             r"|oletko koskaan pohtinut|entä jos|kuvittele"
             r"|kuvitellaan)\b", 2,
             "avaa asialla, älä koukulla"),
            ("varauksien kasa (voi/usein/yleensä)",
             r"(?i)\b(?:voi|voivat|saattaa|usein|yleensä"
             r"|tavallisesti|todennäköisesti)\b", 0,
             "noin moni varaus lukee välttelevältä - väitä tai poista"),
        ],
        "artifact_phrases": [
            ("chatbotin itseviittaus (tekoäly)", "tekoälynä"),
            ("chatbotin itseviittaus (kielimalli)", "kielimallina"),
        ],
        "stopwords": frozenset((
            "ja", "on", "ei", "että", "se", "joka", "kuin", "tämä",
            "myös", "mutta", "kanssa", "sekä", "vain", "vielä", "jo",
            "kun", "jos", "niin", "hyvin", "tai",
        )),
        "marks": "äö",
        "em_dash_factor": 1.0,
    },
}

# How much text detection reads. Plenty for a stop-word census, cheap on a
# book-sized paste.
_DETECT_SAMPLE = 4000


def detect_language(text):
    """Best-effort language sniff over the pack languages, stdlib only.

    Counts each pack's stop words in the first _DETECT_SAMPLE characters
    (plus a small bonus for characters distinctive of the language, like ñ
    or ß) and picks the language with the highest coverage - but only when
    the winner is clear: at least 4 stop-word hits, at least 7% of tokens,
    and 25% ahead of the runner-up. Anything murkier returns the fallback.

    Returns (code, source) where source is "detected" or "fallback".
    A fallback means: score with the English pack (its lexical tells simply
    won't fire on another language) and trust only the structural checks -
    the JSON says which happened, so a wrong-pack score never masquerades
    as a confident one.
    """
    sample = text[:_DETECT_SAMPLE].lower()
    tokens = re.findall(r"[^\W\d_]+", sample)
    if not tokens:
        return "en", "fallback"
    counts = {}
    for tok in tokens:
        counts[tok] = counts.get(tok, 0) + 1
    total = len(tokens)
    scored = []
    for code, pack in LANGUAGES.items():
        hits = sum(counts.get(w, 0) for w in pack["stopwords"])
        cov = hits / total
        for ch in pack["marks"]:
            if ch in sample:
                cov += 0.02
        scored.append((cov, hits, code))
    scored.sort(key=lambda t: -t[0])
    (best_cov, best_hits, best_code), (second_cov, _, _) = scored[0], scored[1]
    if best_hits >= 4 and best_cov >= 0.07 and best_cov >= second_cov * 1.25:
        return best_code, "detected"
    return "en", "fallback"


def resolve_language(text, lang=None):
    """Turn a --lang argument (None/"auto"/a pack code) into (code, source)."""
    if lang and lang != "auto":
        if lang not in LANGUAGES:
            raise ValueError(f"unknown language {lang!r}, choose from "
                             f"{sorted(LANGUAGES)} or auto")
        return lang, "forced"
    return detect_language(text)


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


def find_all_plain(text_lower, needle):
    """Plain substring spans, no word boundaries - for chat-UI artifacts
    like "utm_source=chatgpt.com" that live inside URLs and markup where
    \\b does the wrong thing."""
    spans, i = [], text_lower.find(needle)
    while i != -1:
        spans.append((i, i + len(needle)))
        i = text_lower.find(needle, i + 1)
    return spans


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


CONFIG_NAMES = (".noslop.json", ".nosloprc")


def find_config(start_dir):
    """Walk upward from start_dir looking for a config file, stopping at a
    filesystem root or a .git directory (repo boundary). Returns a path or
    None. JSON only, no extra parsing dependency and no 3.8-vs-3.11 tomllib
    split to reason about."""
    d = os.path.abspath(start_dir or os.getcwd())
    while True:
        for name in CONFIG_NAMES:
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate):
                return candidate
        if os.path.isdir(os.path.join(d, ".git")):
            return None
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_config(path):
    """Read a JSON config with optional ignore_words / ignore_phrases /
    extra_words / extra_phrases keys. Unknown keys are ignored so the format
    can grow without breaking old configs. Raises ValueError with a plain
    message on bad JSON or a non-object top level, so main() can report it
    without a traceback."""
    with open(path, "r", encoding="utf-8-sig") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a JSON object")
    return {
        "ignore_words": list(data.get("ignore_words", [])),
        "ignore_phrases": list(data.get("ignore_phrases", [])),
        "extra_words": list(data.get("extra_words", [])),
        "extra_phrases": list(data.get("extra_phrases", [])),
    }


def apply_config(config, buzzwords, phrases):
    """Return new (buzzwords, phrases) lists with the config's ignore/extra
    entries applied. Comparisons are case-insensitive since the lists
    themselves are matched against lowercased text."""
    ignore_w = {w.lower() for w in config["ignore_words"]}
    ignore_p = {p.lower() for p in config["ignore_phrases"]}
    words = [w for w in buzzwords if w.lower() not in ignore_w]
    phr = [p for p in phrases if p.lower() not in ignore_p]
    for w in config["extra_words"]:
        if w.lower() not in ignore_w and w not in words:
            words.append(w)
    for p in config["extra_phrases"]:
        if p.lower() not in ignore_p and p not in phr:
            phr.append(p)
    return words, phr


def load_ignore_file(path):
    """Read a .noslopignore file: one gitignore-style glob per line, blank
    lines and #-comments skipped."""
    patterns = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def is_ignored(path, patterns):
    """Match a path against .noslopignore-style patterns. Matches against
    both the full (forward-slash-normalized) path and the bare filename, so
    a pattern like "CHANGELOG.md" excludes it anywhere in the tree, same as
    gitignore's default behavior for a pattern with no slash."""
    norm = path.replace(os.sep, "/")
    base = os.path.basename(norm)
    for pat in patterns:
        if fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(base, pat):
            return True
    return False


def to_rdjsonl(path, r):
    """Yield rdjsonl (reviewdog diagnostic format) lines for one file's
    result: one JSON object per hit, message/location/severity shaped so
    `noslop --rdjson file.md | reviewdog -f=rdjsonl -name=noslop` works with
    no extra glue. https://github.com/reviewdog/reviewdog/tree/master/proto/rdf
    """
    src = path if path != "-" else "<stdin>"
    lines = []

    def emit(message, line, severity):
        lines.append(json.dumps({
            "message": message,
            "location": {"path": src, "range": {"start": {"line": max(line, 1)}}},
            "severity": severity,
        }))

    # Chat-UI residue and the chatbot disclaimer phrases that were promoted
    # to the same tier in 0.9.0 - direct paste evidence, flagged as errors
    # rather than warnings since a single hit already pins the hard verdict.
    for label, n, ls in r["ai_artifacts"]:
        for ln in ls:
            emit(f"{label} - direct paste evidence", ln, "ERROR")
    for word, n, ls in r["buzzwords"]:
        for ln in ls:
            emit(f'buzzword: "{word}" reads as an AI tell', ln, "WARNING")
    for phrase, n, ls in r["phrases"]:
        for ln in ls:
            emit(f'filler phrase: "{phrase}"', ln, "WARNING")
    for label, n, weight, hint, ls in r["patterns"]:
        severity = "WARNING" if weight else "INFO"
        for ln in ls:
            emit(f"{label} - {hint}", ln, severity)
    for phrase, n, ls in r["copula_avoidance"]:
        for ln in ls:
            emit(f'copula-avoidance phrase: "{phrase}"', ln,
                 "WARNING" if r["copula_avoidance_scored"] else "INFO")
    for phrase, n, ls in r["scope_inflation"]:
        for ln in ls:
            emit(f'scope-inflation phrase: "{phrase}"', ln, "WARNING")
    return lines


def analyze(text, buzzwords=None, phrases=None, lang=None, lang_source=None):
    """Score one piece of text.

    lang picks the language pack: a code from LANGUAGES forces that pack,
    None/"auto" sniffs the text with detect_language(). buzzwords/phrases
    default to the chosen pack's lists; pass overrides (see apply_config)
    to run with a project's config applied without mutating the packs.
    lang_source only overrides what the result reports (main() passes it
    so a --lang choice shows up as "forced" rather than re-detected)."""
    if lang is None or lang == "auto":
        code, source = detect_language(text)
    else:
        code, source = lang, (lang_source or "forced")
    if lang_source is not None:
        source = lang_source
    pack = LANGUAGES[code]
    if buzzwords is None:
        buzzwords = pack["buzzwords"]
    if phrases is None:
        phrases = pack["phrases"]
    # Exotic line terminators and the BOM sit in different \s classes in
    # Python and JavaScript, so both engines normalize them away up front -
    # otherwise multiline anchors and sentence splitting quietly disagree.
    # Every replacement is one-to-one except \r\n, which no UI input path
    # produces (textareas and text-mode file reads both normalize it first).
    text = re.sub("\\r\\n?|[\\x1c-\\x1f\\x85\\u2028\\u2029]", "\n", text)
    text = text.replace("\ufeff", " ")
    # One curly apostrophe (U+2019) normalized to the straight form the
    # phrase lists are written in - same length, so spans still line up.
    # "it's important to note" in curly-quoted prose counts the same way.
    lower = text.lower().replace("’", "'")
    # Letters in any script, not [A-Za-z]: an ASCII-only word count silently
    # collapses the per-1k denominator on accented or non-Latin text. Two
    # letters minimum, matching the old tokenizer's behavior on English.
    words = re.findall(r"[^\W\d_](?:[^\W\d_]|['\-])+", text)
    wc = max(len(words), 1)
    per1k = lambda n: round(n * 1000.0 / wc, 1)

    # Collect buzzword and phrase hits as spans, then keep the longest
    # non-overlapping ones, so "let's dive into" is one hit rather than
    # "let's dive" plus "dive into", and "rich tapestry" doesn't also
    # count as "tapestry".
    spans = []
    for w in buzzwords:
        spans += [(s, e, "buzz", w) for s, e in find_all(lower, w)]
    for p in phrases:
        spans += [(s, e, "phrase", p) for s, e in find_all(lower, p)]
    # Copula-avoidance and scope-inflation share the same overlap-resolution
    # pool as buzzwords/phrases (not a separate pass) so a longer existing
    # phrase entry wins over a shorter fragment that sits inside it - e.g.
    # "stands as a testament" (a PHRASES hit) beats the copula-avoidance
    # fragment "stands as a" it contains, rather than scoring both.
    for w in pack.get("copula_avoidance", ()):
        spans += [(s, e, "copula", w) for s, e in find_all(lower, w)]
    for w in pack.get("scope_inflation", ()):
        spans += [(s, e, "scope", w) for s, e in find_all(lower, w)]
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

    # Copula-avoidance ("X serves as a Y") is legitimate technical writing
    # occasionally - only scores past a density gate, like the hedge stack
    # and connective-opener checks. Scope-inflation ("cannot be overstated")
    # scores every hit, but at a lower weight (2, not 3) since each phrase
    # has everyday non-AI use on its own.
    copula_avoidance = tally("copula")
    scope_inflation = tally("scope")
    copula_total = sum(n for _, n, _ in copula_avoidance)
    scope_total = sum(n for _, n, _ in scope_inflation)
    # Density gate needs both an absolute floor (2+ hits) and a rate floor:
    # a rate alone would let a single hit in a 400-word note clear "2 per
    # 1,000 words" on arithmetic alone, the same short-document trap the
    # connective-opener and question-hook checks already guard against
    # elsewhere in this function.
    copula_avoidance_scored = (
        copula_total >= 2 and
        (copula_total * 1000.0 / wc) >= COPULA_AVOIDANCE_MIN_PER_1K
    )

    pat = []
    pat_raw = 0
    for entry in pack["patterns"]:
        label, rx, weight, hint = entry[:4]
        # Optional 5th field: hits that don't score. A device that's normal
        # rhetoric once (a single triad) only counts when it repeats.
        free = entry[4] if len(entry) > 4 else 0
        matches = list(re.finditer(rx, text))
        if matches:
            pat.append((label, len(matches), weight, hint,
                        [line_of(text, m.start()) for m in matches[:5]]))
            pat_raw += max(0, len(matches) - free) * weight

    emdash = len(re.findall(r"—", text))
    emoji = len(EMOJI.findall(text))

    # Chat-UI residue. Overlapping/adjacent spans merge (a pasted
    # ":contentReference[oaicite:...]" block is one artifact, not several).
    # Markup tokens (AI_ARTIFACTS) are matched as bare substrings since they
    # can sit inside a URL; chatbot disclaimer sentences (AI_ARTIFACT_PHRASES
    # and the pack's own researched artifact_phrases) are matched with word
    # boundaries like any other phrase - see the note on AI_ARTIFACT_PHRASES.
    art_spans = []
    for label, needle in AI_ARTIFACTS:
        art_spans += [(s, e, label) for s, e in find_all_plain(lower, needle)]
    for label, needle in AI_ARTIFACT_PHRASES:
        art_spans += [(s, e, label) for s, e in find_all(lower, needle)]
    for label, needle in pack.get("artifact_phrases", ()):
        art_spans += [(s, e, label) for s, e in find_all(lower, needle)]
    art_spans.sort()
    # Sentinel is -2, not -1: a span at offset 0 must still pass the
    # adjacency test (0 > -1), or an artifact that opens the text vanishes.
    art_rows, art_end = {}, -2
    for s, e, label in art_spans:
        if s > art_end + 1:
            art_rows.setdefault(label, []).append(s)
        art_end = max(art_end, e)
    artifacts = [(label, len(starts), [line_of(text, s) for s in starts[:5]])
                 for label, starts in art_rows.items()]
    artifacts.sort(key=lambda x: -x[1])
    art_total = sum(n for _, n, _ in artifacts)

    # Emoji decorating structure (headings, list bullets) is a stronger tell
    # than emoji inside body prose, so those occurrences score once as emoji
    # and once more here.
    header_emoji = 0
    bold_inline = 0
    for raw_line in text.split("\n"):
        ls = raw_line.lstrip()
        structural = ls.startswith("#") or re.match(r"(?:[-*+]|[0-9]{1,3}[.)])\s", ls)
        if structural:
            header_emoji += len(EMOJI.findall(raw_line))
        else:
            # Bold spray: **emphasis** sprinkled through flowing prose.
            # List items are excluded, and so is a bold label leading the
            # paragraph - the bold-label-bullet check below owns both.
            matches = re.findall(r"\*\*[^*\n]{1,60}\*\*", raw_line)
            if matches and re.match(
                    r"\s*\*\*[^*\n]{1,45}?(?::\*\*|\*\*:|[.!?]\*\*)", raw_line):
                matches = matches[1:]
            bold_inline += len(matches)

    # Bare bullet glyphs (•/▪/‣) opening a line - chat-UI copy/paste
    # residue, since the native way to hand-write a markdown list item is
    # "-" or "*". Phrase-tier weight, not the artifact floor - some
    # note-app exports legitimately carry these.
    bare_bullets = len(BARE_BULLET_RE.findall(text))

    # Generic AI-listicle headings (Introduction, Key Takeaways, Final
    # Thoughts...) only score at 2+ hits - one "Conclusion" is an ordinary
    # essay, several of these in one document is a template. Emphasis
    # markers and a trailing colon are stripped before matching so
    # "**Conclusion:**" and "Conclusion" count the same.
    generic_heading_lines = []
    for m in re.finditer(r"(?m)^#{1,6}[ \t]+(.+?)[ \t]*$", text):
        label = re.sub(r"[*_`]+", "", m.group(1)).strip().rstrip(":.").lower()
        if label in GENERIC_HEADINGS:
            generic_heading_lines.append(line_of(text, m.start()))
    generic_headings = len(generic_heading_lines)
    generic_heading_excess = max(0, generic_headings - 1) if generic_headings >= 2 else 0

    # Heading-level skip (H2 straight to H4, no H3 in between) - reported
    # only, like opener_top_share below. A skipped level is often just a
    # deliberate doc structure, not strong enough evidence on its own to
    # score, but it's a real templating habit worth surfacing.
    heading_levels = [len(m.group(1)) for m in re.finditer(r"(?m)^(#{1,6})[ \t]+\S", text)]
    heading_level_skips = sum(
        1 for i in range(1, len(heading_levels))
        if heading_levels[i] > heading_levels[i - 1] + 1)

    # Curly and straight marks of the SAME kind mixed in one document
    # usually means a paste boundary - chat UIs render smart quotes,
    # editors type straight ones. Cross-kind mixing (straight apostrophes
    # in the author's own prose around a curly-quoted excerpt) is how
    # humans normally quote a source, so it doesn't count.
    curly_apo = text.count("’") + text.count("‘")
    straight_apo = text.count("'")
    curly_dq = text.count("“") + text.count("”")
    straight_dq = text.count('"')
    quote_mix = 1 if ((curly_apo >= 3 and straight_apo >= 3) or
                      (curly_dq >= 3 and straight_dq >= 3)) else 0

    # Sentence-punctuation entropy: see punct_entropy()'s docstring. Small
    # fixed bump like uniformity/quote_mix, never verdict-crossing alone.
    punct_ent = punct_entropy(text)
    punct_entropy_low = punct_ent is not None and punct_ent < PUNCT_ENTROPY_LOW

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    slens = [len(re.findall(r"(?:[^\W\d_]|['\-])+", s)) for s in sentences if s.strip()]
    uniformity = None
    if len(slens) >= 5:
        mean = sum(slens) / len(slens)
        sd = (sum((x - mean) ** 2 for x in slens) / len(slens)) ** 0.5
        uniformity = round((sd / mean) if mean else 0, 2)

    # Staccato runs: 3+ consecutive very short sentences ("No fluff. No
    # filler. Just results.") - the punchy-fragment cadence. The sentence-CV
    # check above can't see it because a few fragments barely move a
    # document-wide coefficient of variation.
    staccato_runs, run = 0, 0
    for n in slens:
        if 0 < n <= 5:
            run += 1
        else:
            staccato_runs += 1 if run >= 3 else 0
            run = 0
    staccato_runs += 1 if run >= 3 else 0

    # Paragraph-length uniformity, same math as the sentence check. No
    # published threshold exists for paragraphs, so the cutoff is
    # deliberately more conservative than the sentence one (0.25 vs 0.35)
    # and the weight is lower.
    paras = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    plens = [n for n in
             (len(re.findall(r"(?:[^\W\d_]|['\-])+", p)) for p in paras) if n]
    paragraph_uniformity = None
    if len(plens) >= 5:
        pmean = sum(plens) / len(plens)
        psd = (sum((x - pmean) ** 2 for x in plens) / len(plens)) ** 0.5
        paragraph_uniformity = round((psd / pmean) if pmean else 0, 2)

    # Cross-paragraph opener self-repetition: normalize each paragraph's
    # first five words and look for the same opener starting 3+ paragraphs.
    # Pure string comparison, so it works identically in every language -
    # distinct from opener_top_share below, which tracks a single word
    # across sentences, not a five-word run across paragraphs.
    paragraph_opener_repeat = 0
    paragraph_opener_repeat_text = None
    if len(paras) >= 5:
        para_openers = {}
        for p in paras:
            head = re.findall(r"[^\W\d_]+", p.lower())[:5]
            if not head:
                continue
            key = " ".join(head)
            para_openers[key] = para_openers.get(key, 0) + 1
        best_opener, best_n = None, 0
        for key, n in para_openers.items():
            if n > best_n:
                best_opener, best_n = key, n
        if best_n >= 3:
            paragraph_opener_repeat = best_n
            paragraph_opener_repeat_text = best_opener

    # Self-answering question hooks: a tiny question dropped mid-paragraph
    # and immediately answered ("More miners join? The puzzle gets harder.").
    # Only mid-line questions count - a question at the start of a line is
    # normal FAQ/heading structure, and the rhetorical-opener pattern
    # already owns that case. One is rhetoric; a run of them is the tell.
    question_hooks = len(re.findall(
        r"(?<=[.!?]) [ \t]*(?:[^\W\d_][\w'\-]*[ \t]+){0,4}[^\W\d_][\w'\-]*\?",
        text))
    question_hook_excess = max(0, question_hooks - 1)

    # Sentence-initial connective adverbs, scored on density over an
    # allowance (like em dashes) because academic prose uses them
    # legitimately. The word list lives in the pack; packs without one
    # skip the check.
    connective_openers = 0
    connectives = pack.get("connectives", ())
    if connectives:
        alt = "|".join(re.escape(c) for c in connectives)
        connective_openers = len(re.findall(
            r"(?im)(?:^|(?<=[.!?])\s)[ \t]*(?:" + alt + r")\b", text))
    connective_excess = max(0, connective_openers - max(2, len(slens) // 10))

    # Sentence-opener concentration: share of sentences that open with the
    # document's most common first word. Reported but not scored - the
    # evidence is thinner than for the scored checks, and first-person prose
    # ("I did... I went...") legitimately concentrates openers. Single-pass
    # count: a chat log is tens of thousands of tiny sentences, and a
    # quadratic loop here once froze the browser tab for minutes.
    openers = []
    for s in sentences:
        m = re.match(r"[^\w]*([^\W\d_][\w'\-]*)", s)
        if m:
            openers.append(m.group(1).lower())
    opener_top_share = None
    if len(openers) >= 8:
        freq, best_n = {}, 0
        for w in openers:
            n = freq.get(w, 0) + 1
            freq[w] = n
            if n > best_n:
                best_n = n
        opener_top_share = round(best_n / len(openers), 2)

    # Windowed type-token ratio and function-word ratio: report-only
    # diagnostics, never scored. Both track how repetitive/formulaic the
    # vocabulary reads, but the same Stanford burstiness research that
    # documents the sentence-uniformity ESL false-positive risk (see the
    # README's limitations section) applies at least as much here - a
    # non-native writer's smaller working vocabulary would over-flag on
    # this family more, not less, than on sentence rhythm. --json exposes
    # both for anyone who wants them; the human-readable report never
    # prints or suggests "fixing" either one, on purpose.
    words_lc = [w.lower() for w in words]
    windowed_ttr = None
    if len(words_lc) >= 200:
        ratios = [
            len(set(words_lc[i:i + 200])) / 200
            for i in range(0, len(words_lc) - 200 + 1, 200)
        ]
        windowed_ttr = round(sum(ratios) / len(ratios), 3)
    stopwords = pack.get("stopwords", frozenset())
    function_word_ratio = round(
        sum(1 for w in words_lc if w in stopwords) / wc, 3)

    raw = (buzz_total * 3) + (phr_total * 3) + pat_raw
    raw += art_total * 10
    # Dialogue-dash languages get a wider allowance (see em_dash_factor in
    # LANGUAGES) - an em-dash budget tuned for English prose would flag
    # ordinary Spanish or French dialogue punctuation.
    emdash_excess = max(0, emdash - int(max(2, wc // 90) * pack["em_dash_factor"]))
    raw += emdash_excess
    raw += emoji * 2
    raw += header_emoji * 2
    # repeated "**Term:** explanation" bullets - a formatting tell, whether
    # the list uses dash/star markers, is numbered ("1. **Term:** ..."), or
    # drops the marker entirely and leads a paragraph with the bold label
    # ("**Term.** explanation")
    bold_bullets = len(re.findall(
        r"(?m)^\s*(?:(?:[-*+]|[0-9]{1,3}[.)])\s+)?\*\*[^*\n]{1,45}?(?::\*\*|\*\*:|[.!?]\*\*)",
        text))
    if bold_bullets >= 3:
        raw += (bold_bullets - 2) * 2
    # Inline bold gets an allowance like em dashes do - a little emphasis is
    # normal, a spray of it through prose is the tell.
    bold_inline_excess = max(0, bold_inline - max(2, wc // 150))
    raw += bold_inline_excess * 2
    raw += question_hook_excess * 2
    # Copula-avoidance only counts past its density gate; scope-inflation
    # scores every hit, at the lower weight noted above.
    if copula_avoidance_scored:
        raw += copula_total * 3
    raw += scope_total * 2
    raw += generic_heading_excess * 2
    raw += bare_bullets * 3
    density_crutch_total = sum(
        len(find_all(lower, w)) for w in pack.get("density_crutch", ()))
    density_crutch_allowance = max(2, wc // DENSITY_CRUTCH_ALLOWANCE_DIVISOR)
    density_crutch_excess = max(0, density_crutch_total - density_crutch_allowance)
    raw += density_crutch_excess * 2
    score = per1k(raw)
    # Rhythm and typography signals ride on top of the normalized score as
    # small fixed bumps instead of raw points: per-1k normalization
    # amplifies a raw point brutally on short texts (one +4 hit in a
    # 130-word note would be 30/1k on its own), and none of these signals
    # is strong enough evidence to cross a verdict line by itself. The
    # first staccato run is free - terse fragments are a legitimate human
    # style (fiction has written that way for a century); run after run
    # is the tell.
    if uniformity is not None and uniformity < 0.35:
        score += 8
    if paragraph_uniformity is not None and paragraph_uniformity < 0.25:
        score += 4
    score += min(max(0, staccato_runs - 1) * 4, 8)
    score += quote_mix * 4
    score += min(connective_excess, 2) * 2
    if punct_entropy_low:
        score += 5
    if paragraph_opener_repeat:
        score += 5
    # A chat-UI artifact is proof of paste, not a probabilistic signal - it
    # pins the score at the hard-verdict floor no matter how long the text
    # is (per-1k normalization would otherwise dilute it to nothing in a
    # long document).
    if art_total:
        score = max(score, 25.0)

    verdict = "looks human"
    if score >= 25:
        verdict = "reads as AI - needs a real rewrite"
    elif score >= 10:
        verdict = "some AI tells - worth a pass"

    return {
        "mode": "prose",
        "words": wc, "score_per_1k": score, "verdict": verdict,
        "language": code, "language_source": source,
        "buzzwords": buzz, "phrases": phr, "patterns": pat,
        "ai_artifacts": artifacts,
        "em_dashes": emdash, "em_dash_excess": emdash_excess, "emoji": emoji,
        "header_emoji": header_emoji,
        "bold_label_bullets": bold_bullets,
        "bold_inline": bold_inline, "bold_inline_excess": bold_inline_excess,
        "quote_mix": quote_mix, "staccato_runs": staccato_runs,
        "question_hooks": question_hooks,
        "question_hook_excess": question_hook_excess,
        "connective_openers": connective_openers,
        "connective_excess": connective_excess,
        "sentence_uniformity_cv": uniformity,
        "paragraph_uniformity_cv": paragraph_uniformity,
        "opener_top_share": opener_top_share,
        "copula_avoidance": copula_avoidance,
        "copula_avoidance_scored": copula_avoidance_scored,
        "scope_inflation": scope_inflation,
        "generic_headings": generic_headings,
        "bare_bullets": bare_bullets,
        "punct_entropy": punct_ent,
        "punct_entropy_low": punct_entropy_low,
        "heading_level_skips": heading_level_skips,
        "paragraph_opener_repeat": paragraph_opener_repeat,
        "paragraph_opener_repeat_text": paragraph_opener_repeat_text,
        "windowed_ttr": windowed_ttr,
        "function_word_ratio": function_word_ratio,
        "density_crutch": density_crutch_total,
        "density_crutch_excess": density_crutch_excess,
    }


def report(r, quiet=False):
    out = [f"words: {r['words']}   AI-tell score: {r['score_per_1k']}/1k   -> {r['verdict']}"]
    if quiet:
        return "\n".join(out)
    if r["language_source"] == "fallback":
        out.append("language: no pack matched - scored with the English lists and structural checks only")
    elif r["language"] != "en" or r["language_source"] == "forced":
        name = LANGUAGES[r["language"]]["name"]
        out.append(f"language: {name} ({r['language_source']})")
    if r["ai_artifacts"]:
        out.append("\nChat-UI residue (direct paste evidence - scores the hard verdict on its own):")
        for label, n, lines in r["ai_artifacts"]:
            out.append(f"  {n:>2}x  {label} (lines {', '.join(map(str, lines))})")
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
    if r["copula_avoidance"]:
        tag = "" if r["copula_avoidance_scored"] else "  [below the density gate, not scored]"
        out.append(f"\nCopula-avoidance phrases:{tag}")
        for p, n, lines in r["copula_avoidance"]:
            out.append(f'  {n:>2}x  "{p}" (lines {", ".join(map(str, lines))})')
    if r["scope_inflation"]:
        out.append("\nScope-inflation phrases:")
        for p, n, lines in r["scope_inflation"]:
            out.append(f'  {n:>2}x  "{p}" (lines {", ".join(map(str, lines))})')
    misc = []
    if r["em_dash_excess"]:
        misc.append(f"{r['em_dashes']} em dashes is dense for the length (vary the punctuation)")
    if r["emoji"]:
        misc.append(f"{r['emoji']} emoji (usually worth dropping in prose)")
    if r["header_emoji"]:
        misc.append(f"{r['header_emoji']} emoji decorating headings/bullets (the strongest emoji tell)")
    if r["sentence_uniformity_cv"] is not None and r["sentence_uniformity_cv"] < 0.35:
        misc.append(f"sentence lengths very even (cv={r['sentence_uniformity_cv']}) - vary the rhythm")
    if r["paragraph_uniformity_cv"] is not None and r["paragraph_uniformity_cv"] < 0.25:
        misc.append(f"paragraph lengths very even (cv={r['paragraph_uniformity_cv']}) - vary the block sizes")
    if r["staccato_runs"]:
        misc.append(f"{r['staccato_runs']} staccato run(s) of 3+ tiny sentences - the punchy-fragment cadence")
    if r["quote_mix"]:
        misc.append("curly and straight quotes mixed - usually a paste boundary; pick one style")
    if r["question_hook_excess"]:
        misc.append(f"{r['question_hooks']} mid-sentence question hooks ('The result? ...') - answer directly instead")
    if r["connective_excess"]:
        misc.append(f"{r['connective_openers']} sentences open on a connective (Moreover/Additionally/...) - most can go")
    if r.get("bold_label_bullets", 0) >= 3:
        misc.append(f"{r['bold_label_bullets']} '**Term:** ...' bullets - a formatting tell; write some as prose")
    if r["bold_inline_excess"]:
        misc.append(f"{r['bold_inline']} bold spans in running prose is heavy - keep the few that earn it")
    if r["opener_top_share"] is not None and r["opener_top_share"] >= 0.4:
        misc.append(f"{int(r['opener_top_share'] * 100)}% of sentences open with the same word [style, not scored] - vary the openers")
    if r["generic_headings"] and r["generic_headings"] >= 2:
        misc.append(f"{r['generic_headings']} generic listicle headings (Introduction/Conclusion/Key Takeaways/...) - the template shows")
    if r["bare_bullets"]:
        misc.append(f"{r['bare_bullets']} line(s) open with a bare •/▪/‣ glyph - chat-UI paste residue; use - or *")
    if r["punct_entropy_low"]:
        misc.append(f"punctuation leans on very few marks (entropy={r['punct_entropy']}) - vary the punctuation")
    if r["paragraph_opener_repeat"]:
        misc.append(f"{r['paragraph_opener_repeat']} paragraphs open with \"{r['paragraph_opener_repeat_text']}...\" - vary the opener")
    if r["density_crutch_excess"]:
        misc.append(f"{r['density_crutch']} uses of a formal-register crutch word is dense for the length (vary the phrasing)")
    if r["heading_level_skips"]:
        misc.append(f"{r['heading_level_skips']} heading level(s) skip a level (e.g. H2 straight to H4) [style, not scored]")
    if misc:
        out.append("\nRhythm & surface:")
        for m in misc:
            out.append(f"  - {m}")
    if not (r["ai_artifacts"] or r["buzzwords"] or r["phrases"] or r["patterns"] or
            r["copula_avoidance"] or r["scope_inflation"] or misc):
        out.append("\nNothing flagged. Reads clean.")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Code mode: was this source file written by an AI?
#
# Same contract as the prose engine - deterministic, standard library only,
# and every point on the score is a finding with a line number you can argue
# with. The extractor splits a source file into comments, docstrings, string
# literals, and blanked-out code BEFORE any rule runs, so a "//" inside a URL
# string never reads as a comment and a "#" in a C preprocessor line never
# does either. Each rule then looks only where its evidence lives: prose
# tells in comments and docstrings, typography in comments, structure in the
# code itself.

# Comment/string syntax families. "line" markers run to end of line, "block"
# pairs nest only where the language actually nests them (Rust), "triple"
# turns on Python-style triple-quoted strings and docstring detection,
# "backtick" turns on JS template literals, "quotes" lists the characters
# that open a string. Lisp keeps only double quotes: a leading apostrophe
# there is quote syntax, not a string.
CODE_SYNTAX = {
    "hash": {"line": ("#",), "block": (), "triple": True, "backtick": False,
             "quotes": "'\"", "nested": False},
    "shell": {"line": ("#",), "block": (), "triple": False, "backtick": False,
              "quotes": "'\"", "nested": False, "heredoc": True},
    "c": {"line": ("//",), "block": (("/*", "*/"),), "triple": False,
          "backtick": True, "quotes": "'\"", "nested": False},
    "rust": {"line": ("//",), "block": (("/*", "*/"),), "triple": False,
             "backtick": False, "quotes": "\"", "nested": True},
    "php": {"line": ("//", "#"), "block": (("/*", "*/"),), "triple": False,
            "backtick": False, "quotes": "'\"", "nested": False},
    "dash": {"line": ("--",), "block": (("/*", "*/"),), "triple": False,
             "backtick": False, "quotes": "'\"", "nested": False},
    "haskell": {"line": ("--",), "block": (("{-", "-}"),), "triple": False,
                "backtick": False, "quotes": "\"", "nested": True},
    "html": {"line": (), "block": (("<!--", "-->"),), "triple": False,
             "backtick": False, "quotes": "'\"", "nested": False},
    "lisp": {"line": (";",), "block": (), "triple": False, "backtick": False,
             "quotes": "\"", "nested": False},
    "percent": {"line": ("%",), "block": (), "triple": False,
                "backtick": False, "quotes": "'\"", "nested": False},
}

# Extension -> (syntax family, display name). Extensions listed here flip a
# file into code mode automatically; --code forces it for anything else.
CODE_EXTENSIONS = {
    ".py": ("hash", "Python"), ".pyw": ("hash", "Python"),
    ".rb": ("hash", "Ruby"), ".rake": ("hash", "Ruby"),
    ".sh": ("shell", "shell"), ".bash": ("shell", "shell"),
    ".zsh": ("shell", "shell"), ".ksh": ("shell", "shell"),
    ".ps1": ("hash", "PowerShell"), ".psm1": ("hash", "PowerShell"),
    ".yml": ("hash", "YAML"), ".yaml": ("hash", "YAML"),
    ".toml": ("hash", "TOML"), ".r": ("hash", "R"), ".jl": ("hash", "Julia"),
    ".pl": ("hash", "Perl"), ".pm": ("hash", "Perl"),
    ".nim": ("hash", "Nim"), ".cr": ("hash", "Crystal"),
    ".ex": ("hash", "Elixir"), ".exs": ("hash", "Elixir"),
    ".tcl": ("hash", "Tcl"),
    ".c": ("c", "C"), ".h": ("c", "C"),
    ".cpp": ("c", "C++"), ".cc": ("c", "C++"), ".cxx": ("c", "C++"),
    ".hpp": ("c", "C++"), ".hh": ("c", "C++"), ".hxx": ("c", "C++"),
    ".java": ("c", "Java"),
    ".js": ("c", "JavaScript"), ".jsx": ("c", "JavaScript"),
    ".mjs": ("c", "JavaScript"), ".cjs": ("c", "JavaScript"),
    ".ts": ("c", "TypeScript"), ".tsx": ("c", "TypeScript"),
    ".mts": ("c", "TypeScript"), ".cts": ("c", "TypeScript"),
    ".go": ("c", "Go"), ".rs": ("rust", "Rust"),
    ".cs": ("c", "C#"), ".swift": ("c", "Swift"),
    ".kt": ("c", "Kotlin"), ".kts": ("c", "Kotlin"),
    ".scala": ("c", "Scala"), ".dart": ("c", "Dart"),
    ".m": ("c", "Objective-C"), ".mm": ("c", "Objective-C"),
    ".groovy": ("c", "Groovy"), ".zig": ("c", "Zig"), ".v": ("c", "V"),
    ".proto": ("c", "protobuf"),
    ".css": ("c", "CSS"), ".scss": ("c", "SCSS"), ".less": ("c", "Less"),
    ".php": ("php", "PHP"),
    ".sql": ("dash", "SQL"), ".lua": ("dash", "Lua"), ".elm": ("dash", "Elm"),
    ".hs": ("haskell", "Haskell"),
    ".html": ("html", "HTML"), ".htm": ("html", "HTML"),
    ".xml": ("html", "XML"), ".svg": ("html", "SVG"), ".vue": ("html", "Vue"),
    ".lisp": ("lisp", "Lisp"), ".el": ("lisp", "Emacs Lisp"),
    ".clj": ("lisp", "Clojure"), ".cljs": ("lisp", "Clojure"),
    ".scm": ("lisp", "Scheme"), ".rkt": ("lisp", "Racket"),
    ".tex": ("percent", "LaTeX"), ".sty": ("percent", "LaTeX"),
    ".erl": ("percent", "Erlang"), ".hrl": ("percent", "Erlang"),
}


def sniff_code_family(text):
    """Guess a syntax family for extensionless input (stdin with --code).
    Counts comment markers at line starts, which is cruder than the
    extension table but only has to pick a comment syntax, not a language.
    A shell shebang is checked first: shell needs its own family for
    heredoc handling."""
    if re.match(r"#!\s*\S*/(?:env[ \t]+)?(?:ba|z|k|da)?sh\b", text):
        return "shell", "shell"
    heads = [ln.lstrip()[:4] for ln in text.split("\n")]
    c_hits = sum(1 for h in heads if h.startswith(("//", "/*")))
    hash_hits = sum(1 for h in heads if h.startswith("#") and
                    not h.startswith(("#!", "#inc", "#def", "#ifd", "#ifn",
                                      "#end", "#pra", "#els", "#und")))
    dash_hits = sum(1 for h in heads if h.startswith("--"))
    best = max(c_hits, hash_hits, dash_hits)
    if best == 0 or best == hash_hits:
        return "hash", "code"
    if best == c_hits:
        return "c", "code"
    return "dash", "code"


def extract_code_parts(text, family):
    """Split source into comments, docstrings, strings, and blanked code.

    Returns a dict with:
      comments   - [(first line number, comment text)] per comment
      docstrings - [(line, text)] (Python-style triple strings in doc
                   position: first statement of a file, or right after a
                   line ending in ":")
      strings    - [(line, text)] other string literals
      code       - the source with all of the above blanked to spaces,
                   newlines kept, so regexes over it get real line numbers
      loc        - lines with actual code on them after blanking
      comment_line_count - distinct lines carrying comment text

    One deliberate looseness: a single quote with no closing mate before
    end of line is treated as code, not an unterminated string, so Rust
    lifetimes ('a), Lisp quotes, and stray apostrophes don't swallow
    everything after them."""
    syntax = CODE_SYNTAX[family]
    line_markers = syntax["line"]
    blocks = syntax["block"]
    quotes = syntax["quotes"]
    n = len(text)
    out = {"comments": [], "docstrings": [], "strings": [],
           "body_line_comments": []}
    code_out = []
    comment_lines = set()
    i, line = 0, 1
    last_code_char = ""

    def advance(j, keep):
        nonlocal i, line
        seg = text[i:j]
        code_out.append(seg if keep else re.sub(r"[^\n]", " ", seg))
        line += seg.count("\n")
        i = j

    while i < n:
        ch = text[i]
        # Shell heredocs: the body of `cat <<EOF ... EOF` is payload being
        # written somewhere else, not shell - a "# Step 1" line inside one
        # is text, not a comment. Bare delimiters must start uppercase or
        # underscore (every real-world EOF/EOT/SQL does) so `$((1 << 20))`
        # arithmetic and `<<<` here-strings never read as heredocs; quoted
        # delimiters are unambiguous and can be anything.
        if (syntax.get("heredoc") and text.startswith("<<", i)
                and not text.startswith("<<<", i)
                and (i == 0 or text[i - 1] != "<")):
            hm = re.match(r"<<(-?)[ \t]*(?:(['\"])(\w+)\2|([A-Z_][A-Za-z0-9_]*))",
                          text[i:])
            if hm:
                strip_tabs = hm.group(1) == "-"
                word = hm.group(3) or hm.group(4)
                nl = text.find("\n", i)
                if nl == -1:
                    advance(n, keep=True)
                    continue
                # The rest of the opener line stays code; the body runs to
                # the line that is exactly the delimiter (bash is strict
                # about that, so this is too).
                advance(nl + 1, keep=True)
                body_line = line
                j = i
                while j < n:
                    eol = text.find("\n", j)
                    eol = n if eol == -1 else eol
                    cand = text[j:eol]
                    if strip_tabs:
                        cand = cand.lstrip("\t")
                    if cand == word:
                        break
                    j = eol + 1 if eol < n else n
                out["strings"].append((body_line, text[i:j]))
                advance(j, keep=False)
                continue
        lm = next((m for m in line_markers if text.startswith(m, i)), None)
        if lm is not None:
            j = text.find("\n", i)
            j = n if j == -1 else j
            body = text[i + len(lm):j].strip()
            out["comments"].append((line, body))
            # A line comment alone on an *indented* line is a body comment -
            # the kind that narrates the statement below it. Comments at
            # column 0 (file/function docs) and trailing comments after code
            # are collected above but excluded here.
            ls = text.rfind("\n", 0, i) + 1
            prefix = text[ls:i]
            if prefix and not prefix.strip():
                out["body_line_comments"].append((line, body))
            comment_lines.add(line)
            advance(j, keep=False)
            continue
        bm = next(((op, cl) for op, cl in blocks if text.startswith(op, i)), None)
        if bm is not None:
            op, cl = bm
            start_line = line
            depth, j = 1, i + len(op)
            while j < n and depth:
                if syntax["nested"] and text.startswith(op, j):
                    depth += 1
                    j += len(op)
                elif text.startswith(cl, j):
                    depth -= 1
                    j += len(cl)
                else:
                    j += 1
            body = text[i + len(op):j - len(cl)] if depth == 0 else text[i + len(op):j]
            out["comments"].append((start_line, body.strip()))
            for k in range(start_line, start_line + body.count("\n") + 1):
                comment_lines.add(k)
            advance(j, keep=False)
            continue
        if syntax["triple"] and text.startswith(('"""', "'''"), i):
            q = text[i:i + 3]
            start_line = line
            jc = text.find(q, i + 3)
            body = text[i + 3:jc] if jc != -1 else text[i + 3:]
            j = jc + 3 if jc != -1 else n
            # Doc position: nothing but whitespace before it in the file so
            # far, or the last real code character is the ":" that closed a
            # def/class line. Assignments (x = """...""") stay strings.
            if last_code_char in ("", ":"):
                out["docstrings"].append((start_line, body.strip()))
            else:
                out["strings"].append((start_line, body))
            advance(j, keep=False)
            continue
        if ch in quotes:
            j = i + 1
            closed = False
            while j < n:
                cj = text[j]
                if cj == "\\":
                    j += 2
                    continue
                if cj == ch:
                    closed = True
                    break
                if cj == "\n":
                    break
                j += 1
            if closed:
                out["strings"].append((line, text[i + 1:j]))
                advance(j + 1, keep=False)
            else:
                advance(i + 1, keep=True)
                last_code_char = ch
            continue
        if syntax["backtick"] and ch == "`":
            start_line = line
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "`":
                    break
                j += 1
            out["strings"].append((start_line, text[i + 1:min(j, n)]))
            advance(min(j + 1, n), keep=False)
            continue
        # Plain code: consume up to the next character anything above could
        # care about, in one slice rather than one char at a time.
        j = i
        while j < n:
            cj = text[j]
            if cj in quotes or (syntax["backtick"] and cj == "`"):
                break
            if any(text.startswith(m, j) for m in line_markers):
                break
            if any(text.startswith(op, j) for op, cl in blocks):
                break
            if syntax["triple"] and text.startswith(('"""', "'''"), j):
                break
            if (syntax.get("heredoc") and cj == "<" and j > i
                    and text.startswith("<<", j)):
                break
            j += 1
        j = max(j, i + 1)
        seg = text[i:j]
        stripped = seg.rstrip()
        if stripped:
            last_code_char = stripped[-1]
        advance(j, keep=True)

    code = "".join(code_out)
    out["code"] = code
    out["loc"] = sum(1 for ln in code.split("\n") if ln.strip())
    out["comment_line_count"] = len(comment_lines)
    return out


# Chat residue in comments - evidence the file passed through a chat window,
# not a style habit. Matched with word boundaries over comment/docstring text
# only; one hit pins the score at the hard verdict, same as prose artifacts.
CODE_ARTIFACT_PHRASES = [
    ("chatbot self-reference", "as an ai language model"),
    ("chatbot self-reference", "as an ai model"),
    ("chatbot self-reference", "as an ai assistant"),
    ("chat framing left in a comment", "certainly! here"),
    ("chat framing left in a comment", "here's the updated code"),
    ("chat framing left in a comment", "here is the updated code"),
    ("chat framing left in a comment", "here's the complete code"),
    ("chat framing left in a comment", "here is the complete code"),
    ("chat framing left in a comment", "here's the full code"),
    ("chat framing left in a comment", "i hope this helps"),
    ("chat framing left in a comment", "hope this helps"),
]

# Truncation markers: the "// ... rest of the code remains the same" a chat
# window prints when it elides code. Nobody types these into a working file.
# Each branch requires the elision context (a literal "..." or a
# remains/stays/unchanged claim) - a bare "rest of the file" is something a
# person can write about a file, and this tier can't afford that.
CODE_TRUNCATION_RE = re.compile(
    r"(?i)(?:\.\.\.\s*\(?\s*rest of (?:the|your) (?:code|file|function|class|script|implementation)\b"
    r"|\brest of (?:the|your) (?:code|file|function|class|script|implementation)"
    r" (?:remains|stays|is) (?:the same|unchanged)\b"
    r"|\.\.\.\s*existing code|\bexisting code (?:remains|stays|goes here)\b"
    r"|\byour (?:code|implementation|logic) goes here\b)")

# Explainer-voice comment phrases: the assistant narrating to the requester
# instead of documenting for the next maintainer. Weight 3 per hit, like
# prose phrases. Word-boundary matched over comments and docstrings.
CODE_COMMENT_PHRASES = [
    "in a real application", "in a real-world application", "in a real app",
    "in production, you would", "in a production environment",
    "for demonstration purposes", "for the sake of simplicity",
    "for simplicity, we", "this is a simplified",
    "you can customize", "you can modify", "you can adjust", "you can extend",
    "adjust as needed", "modify as needed", "customize as needed",
    "adjust this as needed", "change as needed",
    "replace with your", "replace this with your", "replace these with your",
    "add your own", "your actual api key", "insert your api key",
    "add your api key", "replace with the actual",
    "import the necessary", "import necessary", "necessary imports",
    "the following code", "the code below", "the above code",
    "this function is responsible for",
    "main entry point", "entry point of the",
    "example usage", "usage example", "sample usage",
]

# Comment-shape patterns, matched with (?m) over comment text one line at a
# time. (label, regex, weight, hint, free hits, gated). Gated patterns are
# the walkthrough voice - and humans have used that voice too (CPython's
# idna.py numbers its comments straight out of RFC 3490's steps), so like
# the narration-verb check they only score once another finding class has
# corroborated the file. Ungated patterns are residue, not voice, and score
# on their own.
CODE_COMMENT_PATTERNS = [
    ("narrated step comments (Step 1 / Step 2 / ...)",
     r"(?mi)^(?:step\s*\d+|\d+[.)])\s*:?\s+[a-z]", 2,
     "comments that walk a reader through steps are chat narration - document why, not what",
     1, True),
    ("'First/Next/Then/Finally, we...' narration",
     r"(?mi)^(?:first|next|then|now|finally)\b,?\s+(?:we|let's|you)\b", 2,
     "the walkthrough voice - a maintainer needs the why, not a tour",
     1, True),
    ("'Here we/Here, we...' narration",
     r"(?mi)^here,?\s+we\b", 2,
     "narrating the code to a reader is chat voice", 1, True),
    ("placeholder path (path/to/your...)",
     r"(?i)\bpath/to/your\b", 2,
     "a template path the chat answer expected you to fill in", 0, False),
]

# Buzzwords that mean something else near code: "underscore" in a comment is
# almost always the character, not the LLM verb (three stdlib files scored on
# it in the mass false-positive sweep). Skipped in code mode only; the -ing
# form still reads verbal and stays.
CODE_BUZZWORD_EXCLUSIONS = frozenset(("underscore", "underscores"))


# Identifiers with no domain in them. Report-only: generic naming is at
# least as junior-dev as it is AI, so it never moves the score - it's
# printed as a diagnostic for a reviewer to weigh.
_GENERIC_IDENTIFIERS = frozenset((
    "result", "results", "data", "temp", "item", "items", "output",
    "response", "res", "obj", "info",
))

# Generic error-message boilerplate: the assistant's stock catch-and-print.
# Matched over the ORIGINAL text (strings are blanked in the code view), and
# a commented-out copy is the same evidence. Case-insensitive.
CODE_ERROR_BOILERPLATE_RE = re.compile(
    r"(?i)(?:print\s*\(|console\.(?:log|error|warn)\s*\(|"
    r"System\.(?:out|err)\.println\s*\(|fmt\.Println\s*\(|echo\s+|"
    r"logger?\.(?:error|info|warning)\s*\(|eprintln!\s*\(|puts\s+)"
    r"\s*f?[\"'`](?:an (?:unexpected )?error occurred|error occurred"
    r"|something went wrong|an error has occurred|oops[,!]|error:\s*\{)")

# The victory lap: printing "... successfully" after routine operations.
# Humans log states and errors; the assistant congratulates the run.
CODE_SUCCESS_BOILERPLATE_RE = re.compile(
    r"(?i)(?:print\s*\(|console\.log\s*\(|System\.out\.println\s*\(|"
    r"fmt\.Println\s*\(|echo\s)[^\n]{0,60}?successfully")

# except/catch that only prints and moves on - the assistant's way of
# looking careful without deciding anything. Per-language variants.
CODE_SWALLOWED_ERROR_RE = re.compile(
    r"(?m)^[ \t]*except Exception as e:\s*\n[ \t]*print\s*\("
    r"|catch\s*\(\s*(?:error|err|e|ex|exception)\s*(?::[^)]*)?\)\s*\{\s*\n?\s*console\.(?:log|error)\s*\(")

# Typography in comments/docstrings. Editors type straight quotes, "--",
# "->", and "..."; chat output renders the typographic forms. In prose some
# of these need an allowance; inside source comments they're rare enough in
# human code to score per hit.
CODE_TYPOGRAPHY = [
    ("em dash in a comment", "—", 2,
     "editors type -- ; the em dash character is chat-render residue"),
    ("curly quote in a comment", "‘’“”", 2,
     "editors type straight quotes; curly ones arrive by paste"),
    ("arrow character in a comment", "→⇒", 1,
     "-> is what people type; the arrow glyph is rendered output"),
    ("ellipsis character in a comment", "…", 1,
     "three dots typed is ...; the single glyph is rendered output"),
]

# Invisible characters anywhere outside string literals are paste evidence
# at best and prompt-injection surface at worst. Artifact tier.
INVISIBLE_CHARS = "".join(chr(c) for c in
                          (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD))

# Words a comment shares with the identifiers on the very next code line.
# These function words don't count toward the overlap.
_COMMENT_STOPWORDS = frozenset((
    "the", "a", "an", "to", "of", "in", "for", "and", "or", "is", "this",
    "that", "with", "on", "it", "we", "be", "as", "are", "if", "then",
    "will", "its", "from", "by", "at", "into", "our", "all", "each",
))

# Narration verbs: the imperative a chat assistant opens a walkthrough
# comment with ("Create the new todo object", "Iterate over the users").
# Used two ways: excluded from the redundancy overlap (the verb isn't in
# the code, the nouns are), and counted as a density signal over indented
# body comments. Indented-only keeps the check off doc comments above
# functions, where imperative mood is a legitimate human convention
# ("Create a new sds string..." - redis).
_NARRATION_VERBS = frozenset((
    "create", "creates", "initialize", "initializes", "define", "defines",
    "declare", "set", "sets", "get", "gets", "check", "checks", "iterate",
    "iterates", "loop", "loops", "convert", "converts", "sort", "sorts",
    "print", "prints", "collect", "collects", "normalize", "normalizes",
    "skip", "skips", "increment", "increments", "decrement", "send",
    "sends", "close", "closes", "open", "opens", "return", "returns",
    "extract", "extracts", "combine", "combines", "slice", "clear",
    "clears", "update", "updates", "add", "adds", "remove", "removes",
    "filter", "filters", "parse", "parses", "load", "loads", "save",
    "saves", "fetch", "fetches", "handle", "handles", "process",
    "calculate", "calculates", "compute", "computes", "generate",
    "generates", "validate", "validates", "read", "reads", "write",
    "writes", "append", "appends", "insert", "inserts", "delete",
    "deletes", "search", "searches", "find", "finds", "build", "builds",
    "make", "makes", "start", "starts", "stop", "stops", "run", "runs",
    "call", "calls", "import", "imports", "render", "renders", "display",
    "displays", "show", "shows", "store", "stores", "retrieve",
    "retrieves", "wait", "waits",
))


def _ident_tokens(code_line):
    """Identifier words on a code line: snake_case and camelCase split into
    lowercase word pieces, so 'user_count' and 'userCount' both yield
    {'user', 'count'}."""
    toks = set()
    for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code_line):
        for part in ident.split("_"):
            for w in re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", part):
                if len(w) >= 2:
                    toks.add(w.lower())
    return toks


def _word_matches_tokens(word, tokens):
    if word in tokens:
        return True
    # Light stemming both ways: "initializes" matches "init"-ish tokens and
    # "config" matches "configuration". Four-char minimum keeps "in"/"int"
    # from matching everything.
    for t in tokens:
        if len(t) >= 4 and word.startswith(t):
            return True
        if len(word) >= 4 and t.startswith(word):
            return True
    return False


def redundant_comments(comments, code_text):
    """Line comments that restate the code they sit on or above - the
    '# increment the counter' above 'counter += 1'. Returns (line, comment)
    pairs where roughly two-thirds of the comment's content words appear
    among the identifiers of the same or next code line. TODO/FIXME-style
    tags and short comments are exempt."""
    code_lines = code_text.split("\n")
    hits = []
    for line, body in comments:
        text = body.strip()
        if not text or re.match(r"(?i)^(?:todo|fixme|xxx|hack|note|nb|warning|see|https?:)\b", text):
            continue
        # A comment that IS code - the equivalent expression in another
        # language (CPython's _ios_support.py mirrors each ctypes call with
        # "device = [UIDevice currentDevice]") or commented-out code - maps
        # onto the next line by design. Same for "Step N" labels, which are
        # spec references, not restatements.
        if "=" in text or text.endswith(";") or re.match(r"(?i)step\s*\d+\b", text):
            continue
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text)]
        # Narration verbs are excluded from the overlap: in "Add the product
        # to the list", the verb isn't in the code - the nouns are, and the
        # nouns are what make the comment redundant.
        content = [w for w in words if w not in _COMMENT_STOPWORDS and
                   w not in _NARRATION_VERBS and len(w) >= 2]
        if len(content) < 2 or len(words) < 3:
            continue
        # Candidate code lines: the comment's own line (trailing comment),
        # then the next two lines with code on them.
        tokens = set()
        found_code = 0
        for cand in range(line, min(line + 4, len(code_lines) + 1)):
            cl = code_lines[cand - 1] if cand - 1 < len(code_lines) else ""
            if cl.strip():
                tokens |= _ident_tokens(cl)
                found_code += 1
                if found_code == 2 and cand > line:
                    break
        if not tokens:
            continue
        matched = sum(1 for w in content if _word_matches_tokens(w, tokens))
        if matched / len(content) >= 0.65:
            hits.append((line, text))
    return hits


def docstring_name_echoes(docstrings, code_text):
    """Python docstrings whose first line just restates the function name:
    def get_user_name -> \"\"\"Get the user name.\"\"\". Returns (line, text)."""
    code_lines = code_text.split("\n")
    def_names = {}
    for m in re.finditer(r"(?m)^[ \t]*(?:async[ \t]+)?def[ \t]+(\w+)", code_text):
        def_names[code_text.count("\n", 0, m.start()) + 1] = m.group(1)
    hits = []
    for line, body in docstrings:
        first = body.split("\n")[0].strip()
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]*", first)]
        content = [w for w in words if w not in _COMMENT_STOPWORDS]
        if not content:
            continue
        name = None
        for back in range(line - 1, max(line - 4, 0), -1):
            if back in def_names:
                name = def_names[back]
                break
            if back - 1 < len(code_lines) and code_lines[back - 1].strip():
                break
        if not name:
            continue
        tokens = _ident_tokens(name)
        if len(content) <= len(tokens) + 1 and all(
                _word_matches_tokens(w, tokens) for w in content):
            hits.append((line, first))
    return hits


JSON_SCHEMA_KEYS_CODE = {
    "mode", "code_language", "lines", "sloc", "comment_lines",
    "comment_share", "words", "score_per_100", "verdict",
    "language", "language_source",
    "ai_artifacts", "buzzwords", "phrases", "comment_patterns",
    "comment_phrases", "typography", "emoji", "error_boilerplate",
    "swallowed_errors", "redundant_comments", "docstring_name_echoes",
    "success_boilerplate", "narration_comments", "narration_comment_count",
    "narration_scored", "corroborated",
    "invisible_chars", "comment_sentence_share", "docstring_coverage",
    "banner_comments", "line_length_cv", "generic_identifier_share",
}


def analyze_code(text, ext=None, config=None, lang=None):
    """Score one source file for AI-written tells. ext picks the comment
    syntax (falls back to sniffing); lang forces the prose pack used on the
    comment text; config is a parsed .noslop.json applied to that pack."""
    text = re.sub("\\r\\n?|[\\x1c-\\x1f\\x85\\u2028\\u2029]", "\n", text)
    if ext and ext.lower() in CODE_EXTENSIONS:
        family, code_language = CODE_EXTENSIONS[ext.lower()]
    else:
        family, code_language = sniff_code_family(text)
    parts = extract_code_parts(text, family)
    total_lines = text.count("\n") + 1
    sloc = parts["loc"]

    # The prose the file carries: every comment and docstring flattened to
    # one line each, with a map back to real line numbers, so the prose
    # engine's word lists and the comment-shape patterns run over exactly
    # the text a human would read as prose.
    prose_entries = []
    for line, body in parts["comments"] + sorted(parts["docstrings"]):
        for off, piece in enumerate(body.split("\n")):
            prose_entries.append((line + off, piece.strip()))
    prose_entries.sort()
    # Mention-vs-use: a comment that QUOTES a tell ("as an AI" in double
    # quotes or `backticks`) is talking about the phrase, not writing in it -
    # the same escape hatch prose mode gives via code formatting. Quoted
    # spans are blanked to spaces (lengths kept, so line mapping and match
    # offsets stay honest) before any comment-text rule runs.
    def _blank_quoted(s):
        s = re.sub(r'"[^"\n]{0,120}"', lambda m: " " * len(m.group()), s)
        return re.sub(r"`[^`\n]{0,120}`", lambda m: " " * len(m.group()), s)

    prose_text = "\n".join(_blank_quoted(p) for _, p in prose_entries)
    prose_lower = prose_text.lower().replace("’", "'")

    def real_line(idx):
        pseudo = prose_text.count("\n", 0, idx)
        return prose_entries[pseudo][0] if pseudo < len(prose_entries) else 1

    if lang is None or lang == "auto":
        pack_code, lang_source = detect_language(prose_text)
    else:
        pack_code, lang_source = lang, "forced"
    pack = LANGUAGES[pack_code]
    buzzwords, phrases = pack["buzzwords"], pack["phrases"]
    if config is not None:
        buzzwords, phrases = apply_config(config, buzzwords, phrases)

    # Buzzwords and filler phrases in comments, same overlap resolution as
    # prose so a phrase hit doesn't double-count the buzzword inside it.
    spans = []
    for w in buzzwords:
        if w in CODE_BUZZWORD_EXCLUSIONS:
            continue
        spans += [(s, e, "buzz", w) for s, e in find_all(prose_lower, w)]
    for p in phrases:
        spans += [(s, e, "phrase", p) for s, e in find_all(prose_lower, p)]
    for p in CODE_COMMENT_PHRASES:
        spans += [(s, e, "cphrase", p) for s, e in find_all(prose_lower, p)]
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
        rows = [(key, len(starts), [real_line(s) for s in starts[:5]])
                for key, starts in counts.items()]
        rows.sort(key=lambda x: -x[1])
        return rows

    buzz = tally("buzz")
    phr = tally("phrase")
    cphr = tally("cphrase")

    # Chat residue: the shared prose artifact phrases (chatbot disclaimers
    # in a comment are still chatbot disclaimers), the code-specific chat
    # framings, truncation markers, and invisible characters outside
    # strings. Any hit pins the hard verdict.
    art_rows = {}
    for label, needle in AI_ARTIFACT_PHRASES + CODE_ARTIFACT_PHRASES:
        for s, e in find_all(prose_lower, needle):
            art_rows.setdefault(label, []).append(real_line(s))
    # Markup artifacts are scanned over code and comments but NOT string
    # literals: a string is data, and any tool that handles these markers
    # (including this one) has to name them in strings to do its job.
    code_lower = parts["code"].lower()
    for label, needle in AI_ARTIFACTS:
        for s, e in find_all_plain(code_lower, needle):
            art_rows.setdefault(label, []).append(line_of(parts["code"], s))
        for s, e in find_all_plain(prose_lower, needle):
            art_rows.setdefault(label, []).append(real_line(s))
    for m in CODE_TRUNCATION_RE.finditer(prose_text):
        art_rows.setdefault("chat truncation marker ('... rest of the code')",
                            []).append(real_line(m.start()))
    fence_lines = [ln for ln, body in parts["comments"] if "```" in body]
    for ln in fence_lines:
        art_rows.setdefault("markdown fence inside a comment", []).append(ln)
    # Invisible characters count against the original text for line numbers,
    # but occurrences inside string literals are excused: a test fixture or
    # i18n catalog legitimately carries zero-width characters as data.
    inv_lines = []
    for ch in INVISIBLE_CHARS:
        inv_lines += [line_of(text, m.start())
                      for m in re.finditer(re.escape(ch), text)]
    string_text = "\n".join(s for _, s in parts["strings"])
    inv_in_strings = sum(string_text.count(ch) for ch in INVISIBLE_CHARS)
    inv_scored = max(0, len(inv_lines) - inv_in_strings)
    if inv_scored:
        art_rows["invisible unicode character"] = sorted(inv_lines)[:5]
    artifacts = [(label, len(lines), sorted(lines)[:5])
                 for label, lines in art_rows.items() if lines]
    artifacts.sort(key=lambda x: -x[1])
    art_total = sum(n for _, n, _ in artifacts)

    # Comment-shape patterns over the flattened prose lines. Gated patterns
    # accumulate separately and only join the score if the file is
    # corroborated (decided below, once every finding class is in).
    cpat, cpat_raw, cpat_raw_gated = [], 0, 0
    for label, rx, weight, hint, free, gated in CODE_COMMENT_PATTERNS:
        matches = list(re.finditer(rx, prose_text))
        if matches:
            cpat.append((label, len(matches), weight, hint,
                         [real_line(m.start()) for m in matches[:5]], gated))
            points = max(0, len(matches) - free) * weight
            if gated:
                cpat_raw_gated += points
            else:
                cpat_raw += points

    # Typography in comments/docstrings only - string literals hold data
    # (i18n catalogs, test fixtures) and stay out of these counts.
    typography = []
    typo_raw = 0
    for label, chars, weight, hint in CODE_TYPOGRAPHY:
        lines = []
        for ch in chars:
            lines += [real_line(m.start())
                      for m in re.finditer(re.escape(ch), prose_text)]
        if lines:
            typography.append((label, len(lines), weight, hint, sorted(lines)[:5]))
            typo_raw += len(lines) * weight

    # Emoji in comments (quoted mentions already excused), in code regions
    # (JSX text and template bodies - exactly where an assistant decorates
    # the UI copy), and in strings that carry actual words. A string of
    # bare emoji with no words is a data table, not decoration.
    emoji_n = len(EMOJI.findall(prose_text))
    emoji_n += len(EMOJI.findall(parts["code"]))
    for _, s in parts["strings"]:
        if re.search(r"[A-Za-z]{3}", s):
            emoji_n += len(EMOJI.findall(s))

    err_boiler = [line_of(text, m.start())
                  for m in CODE_ERROR_BOILERPLATE_RE.finditer(text)]
    success_boiler = [line_of(text, m.start())
                      for m in CODE_SUCCESS_BOILERPLATE_RE.finditer(text)]
    swallowed = [line_of(text, m.start())
                 for m in CODE_SWALLOWED_ERROR_RE.finditer(text)]

    # Narration-verb comment openers ("Create the new todo object", "Iterate
    # over the users"), measured over indented body comments only and scored
    # past a density gate: one imperative comment is a human writing a note,
    # a file where nearly every body comment opens on Create/Check/Iterate
    # is a walkthrough.
    body_comments = [(ln, t) for ln, t in parts["body_line_comments"]
                     if len(t.split()) >= 2]
    narrated = []
    for ln, t in body_comments:
        first = t.split()[0].strip(",.:;!")
        if len(first) >= 2 and first.isupper():
            continue  # "HANDLE: ..." tags are a human convention
        if first.lower() in _NARRATION_VERBS:
            narrated.append((ln, t))
    redundant = redundant_comments(parts["comments"], parts["code"])
    echoes = docstring_name_echoes(parts["docstrings"], parts["code"]) \
        if family == "hash" else []

    # Corroboration gate: the walkthrough voice - imperative body comments,
    # Step 1/Step 2 numbering, "First, we..." - was a human convention long
    # before chat assistants (2012 jQuery and CPython's RFC-step comments in
    # the eval sweeps both write this way), so that class never scores on
    # its own. It only counts once something OUTSIDE the class already reads
    # AI - at which point wall-to-wall narration is confirming evidence, not
    # the accusation itself. Gated patterns don't corroborate each other.
    corroborated = bool(
        art_rows or buzz or phr or cphr or typography or
        any(not row[5] for row in cpat) or
        emoji_n or err_boiler or swallowed or redundant or echoes or
        len(success_boiler) >= 2)
    narration_scored = (corroborated and len(narrated) >= 4 and
                        len(narrated) / max(len(body_comments), 1) >= 0.4)

    # Report-only diagnostics, never scored: tutorial code and disciplined
    # human codebases (CPython's comment style guide asks for full
    # sentences) legitimately sit high on both.
    comment_share = round(parts["comment_line_count"] /
                          max(sloc + parts["comment_line_count"], 1), 2)
    sentence_comments = 0
    counted_comments = 0
    for _, body in parts["comments"]:
        t = body.strip()
        if len(t.split()) >= 3:
            counted_comments += 1
            if t[:1].isupper() and t.rstrip().endswith((".", "!", "?")):
                sentence_comments += 1
    comment_sentence_share = (round(sentence_comments / counted_comments, 2)
                              if counted_comments >= 5 else None)
    defs = len(re.findall(r"(?m)^[ \t]*(?:async[ \t]+)?def[ \t]+\w+",
                          parts["code"])) if family == "hash" else 0
    docstring_coverage = (round(len(parts["docstrings"]) / defs, 2)
                          if defs >= 3 else None)

    # More report-only diagnostics. Banners are a decades-old human habit
    # (IDEs ship comment-divider extensions), formatters flatten everyone's
    # line lengths, and generic naming is at least as junior-dev as it is
    # AI - so none of these move the score.
    banner_comments = sum(
        1 for _, body in parts["comments"]
        if re.match(r"^[=\-*~_#]{4,}(?:\s*[\w /&'-]{1,40}?\s*[=\-*~_#]{2,})?$",
                    body.strip()))
    lens = [len(ln) for ln in parts["code"].split("\n") if ln.strip()]
    line_length_cv = None
    if len(lens) >= 30:
        mean = sum(lens) / len(lens)
        sd = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
        line_length_cv = round(sd / mean, 2) if mean else None
    idents = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", parts["code"])
    generic_identifier_share = (
        round(sum(1 for i in idents if i.lower() in _GENERIC_IDENTIFIERS) /
              len(idents), 3) if len(idents) >= 40 else None)

    words = len(re.findall(r"[^\W\d_](?:[^\W\d_]|['\-])+", prose_text))

    buzz_total = sum(n for _, n, _ in buzz)
    phr_total = sum(n for _, n, _ in phr)
    cphr_total = sum(n for _, n, _ in cphr)
    raw = (buzz_total * 3) + (phr_total * 3) + (cphr_total * 3)
    raw += cpat_raw + typo_raw
    if corroborated:
        raw += cpat_raw_gated
    raw += emoji_n * 2
    raw += len(err_boiler) * 3
    raw += max(0, len(success_boiler) - 1) * 2
    raw += len(swallowed) * 2
    raw += max(0, len(redundant) - 1) * 2
    raw += max(0, len(echoes) - 1) * 1
    if narration_scored:
        raw += (len(narrated) - 3) * 2
    raw += art_total * 10
    # Per-100-lines normalization with a floored denominator: one weighted
    # hit in a ten-line snippet is a data point, not a verdict. The floor of
    # 40 keeps a single strong hit (weight 3) in a tiny file under the soft
    # threshold - the short-snippet regime is where the literature says
    # every detector is closest to a coin flip, so a lone finding there
    # reads as a note, not an accusation.
    score = round(raw * 100.0 / max(sloc, 40), 1)
    if art_total:
        score = max(score, 25.0)

    verdict = "looks human-written"
    if score >= 25:
        verdict = "reads as AI-written code"
    elif score >= 10:
        verdict = "some AI tells - worth a look"

    return {
        "mode": "code", "code_language": code_language,
        "lines": total_lines, "sloc": sloc,
        "comment_lines": parts["comment_line_count"],
        "comment_share": comment_share, "words": words,
        "score_per_100": score, "verdict": verdict,
        "language": pack_code, "language_source": lang_source,
        "ai_artifacts": artifacts, "buzzwords": buzz, "phrases": phr,
        "comment_phrases": cphr, "comment_patterns": cpat,
        "typography": typography, "emoji": emoji_n,
        "error_boilerplate": err_boiler,
        "success_boilerplate": success_boiler,
        "swallowed_errors": swallowed,
        "narration_comments": [(ln, t) for ln, t in narrated[:8]],
        "narration_comment_count": len(narrated),
        "narration_scored": narration_scored,
        "corroborated": corroborated,
        "redundant_comments": [(ln, t) for ln, t in redundant],
        "docstring_name_echoes": [(ln, t) for ln, t in echoes],
        "invisible_chars": len(inv_lines),
        "comment_sentence_share": comment_sentence_share,
        "docstring_coverage": docstring_coverage,
        "banner_comments": banner_comments,
        "line_length_cv": line_length_cv,
        "generic_identifier_share": generic_identifier_share,
    }


def report_code(r, quiet=False):
    out = [f"lines: {r['lines']} ({r['sloc']} code, {r['comment_lines']} comment)   "
           f"AI-tell score: {r['score_per_100']}/100 lines   -> {r['verdict']}"]
    if quiet:
        return "\n".join(out)
    out.append(f"language: {r['code_language']}")
    if r["ai_artifacts"]:
        out.append("\nChat residue (direct paste evidence - scores the hard verdict on its own):")
        for label, n, lines in r["ai_artifacts"]:
            out.append(f"  {n:>2}x  {label} (lines {', '.join(map(str, lines))})")
    if r["buzzwords"]:
        out.append("\nLLM buzzwords in comments:")
        for w, n, lines in r["buzzwords"]:
            out.append(f"  {n:>2}x  {w:<18} (lines {', '.join(map(str, lines))})")
    if r["phrases"]:
        out.append("\nFiller phrases in comments:")
        for p, n, lines in r["phrases"]:
            out.append(f'  {n:>2}x  "{p}" (lines {", ".join(map(str, lines))})')
    if r["comment_phrases"]:
        out.append("\nExplainer-voice comments (written for the requester, not the maintainer):")
        for p, n, lines in r["comment_phrases"]:
            out.append(f'  {n:>2}x  "{p}" (lines {", ".join(map(str, lines))})')
    if r["comment_patterns"]:
        out.append("\nComment constructions:")
        for label, n, weight, hint, lines, gated in r["comment_patterns"]:
            tag = ("" if not gated or r["corroborated"]
                   else "  [needs corroboration, not scored]")
            out.append(f"  {n:>2}x  {label}{tag} (lines {', '.join(map(str, lines))})")
            out.append(f"        -> {hint}")
    if r["typography"]:
        out.append("\nTypography (chat-render characters in comments):")
        for label, n, weight, hint, lines in r["typography"]:
            out.append(f"  {n:>2}x  {label} (lines {', '.join(map(str, lines))})")
            out.append(f"        -> {hint}")
    misc = []
    if r["emoji"]:
        misc.append(f"{r['emoji']} emoji in comments or strings - assistants decorate, programmers rarely do")
    if r["error_boilerplate"]:
        misc.append(f"{len(r['error_boilerplate'])} stock error message(s) "
                    f"('An error occurred...') (lines {', '.join(map(str, r['error_boilerplate'][:5]))})")
    if len(r["success_boilerplate"]) >= 2:
        misc.append(f"{len(r['success_boilerplate'])} '...successfully' victory-lap message(s) "
                    f"(lines {', '.join(map(str, r['success_boilerplate'][:5]))})")
    if r["narration_scored"]:
        lines = ", ".join(str(ln) for ln, _ in r["narration_comments"][:5])
        misc.append(f"{r['narration_comment_count']} body comments open on a narration verb "
                    f"(Create/Check/Iterate...) - the walkthrough voice (lines {lines})")
    if r["swallowed_errors"]:
        misc.append(f"{len(r['swallowed_errors'])} catch-and-print handler(s) that swallow the error "
                    f"(lines {', '.join(map(str, r['swallowed_errors'][:5]))})")
    if r["redundant_comments"]:
        lines = ", ".join(str(ln) for ln, _ in r["redundant_comments"][:5])
        misc.append(f"{len(r['redundant_comments'])} comment(s) that restate the code they sit on (lines {lines})")
    if r["docstring_name_echoes"]:
        lines = ", ".join(str(ln) for ln, _ in r["docstring_name_echoes"][:5])
        misc.append(f"{len(r['docstring_name_echoes'])} docstring(s) that just restate the function name (lines {lines})")
    if misc:
        out.append("\nCode habits:")
        for m in misc:
            out.append(f"  - {m}")
    diag = []
    if r["comment_sentence_share"] is not None and r["comment_sentence_share"] >= 0.8:
        diag.append(f"{int(r['comment_sentence_share'] * 100)}% of comments are full capitalized sentences "
                    "[style, not scored - disciplined humans do this too]")
    if r["docstring_coverage"] is not None and r["docstring_coverage"] >= 1.0:
        diag.append("every function carries a docstring [style, not scored]")
    if r["comment_share"] >= 0.4 and r["sloc"] >= 20:
        diag.append(f"comments on {int(r['comment_share'] * 100)}% of content lines "
                    "[style, not scored - tutorial code does this too]")
    if r["banner_comments"] >= 3:
        diag.append(f"{r['banner_comments']} banner/divider comments "
                    "[style, not scored - a decades-old human habit too]")
    if r["line_length_cv"] is not None and r["line_length_cv"] < 0.35:
        diag.append(f"code line lengths unusually even (cv={r['line_length_cv']}) "
                    "[not scored - auto-formatters do this to everyone]")
    if r["generic_identifier_share"] is not None and r["generic_identifier_share"] >= 0.12:
        diag.append(f"{int(r['generic_identifier_share'] * 100)}% of identifiers are generic "
                    "(result/data/temp/item...) [style, not scored]")
    if diag:
        out.append("\nDiagnostics:")
        for d in diag:
            out.append(f"  - {d}")
    if not (r["ai_artifacts"] or r["buzzwords"] or r["phrases"] or
            r["comment_phrases"] or r["comment_patterns"] or r["typography"] or misc):
        out.append("\nNothing flagged. Reads human-written.")
    return "\n".join(out)


def to_rdjsonl_code(path, r):
    """rdjsonl lines for a code-mode result, same shape as to_rdjsonl."""
    src = path if path != "-" else "<stdin>"
    lines = []

    def emit(message, line, severity):
        lines.append(json.dumps({
            "message": message,
            "location": {"path": src, "range": {"start": {"line": max(line, 1)}}},
            "severity": severity,
        }))

    for label, n, ls in r["ai_artifacts"]:
        for ln in ls:
            emit(f"{label} - direct paste evidence", ln, "ERROR")
    for word, n, ls in r["buzzwords"]:
        for ln in ls:
            emit(f'buzzword in a comment: "{word}"', ln, "WARNING")
    for phrase, n, ls in r["phrases"]:
        for ln in ls:
            emit(f'filler phrase in a comment: "{phrase}"', ln, "WARNING")
    for phrase, n, ls in r["comment_phrases"]:
        for ln in ls:
            emit(f'explainer-voice comment: "{phrase}"', ln, "WARNING")
    for label, n, weight, hint, ls, gated in r["comment_patterns"]:
        severity = "WARNING" if (not gated or r["corroborated"]) else "INFO"
        for ln in ls:
            emit(f"{label} - {hint}", ln, severity)
    for label, n, weight, hint, ls in r["typography"]:
        for ln in ls:
            emit(f"{label} - {hint}", ln, "WARNING")
    for ln in r["error_boilerplate"]:
        emit("stock error message ('An error occurred...')", ln, "WARNING")
    for ln in r["swallowed_errors"]:
        emit("catch-and-print handler that swallows the error", ln, "WARNING")
    for ln, t in r["redundant_comments"]:
        emit(f'comment restates the code: "{t}"', ln, "WARNING")
    for ln, t in r["docstring_name_echoes"]:
        emit(f'docstring restates the function name: "{t}"', ln, "INFO")
    return lines


def main(argv=None):
    # Windows consoles default to a legacy code page, and the language packs'
    # names, labels, and hints are not all cp1252-encodable. Emit UTF-8 and
    # degrade to replacement characters rather than crash mid-report.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="noslop", description="Flag the AI tells in a piece of writing.")
    ap.add_argument("paths", nargs="*", default=["-"], metavar="path",
                    help="text files, or - for stdin (default: stdin)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--rdjson", action="store_true",
                    help="emit rdjsonl (reviewdog diagnostic format) instead of the normal report")
    ap.add_argument("--quiet", action="store_true", help="verdict line only")
    ap.add_argument("--markdown", action="store_true",
                    help="skip fenced/inline code when scoring (automatic for .md files)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--code", action="store_true",
                      help="score as source code (automatic for known code "
                           "extensions; use this for stdin or odd extensions)")
    mode.add_argument("--prose", action="store_true",
                      help="score as prose even if the extension says code")
    ap.add_argument("--threshold", type=float, default=10.0,
                    help="score at/above which exit code is 1 (default 10)")
    ap.add_argument("--lang", default="auto", choices=["auto"] + sorted(LANGUAGES),
                    help="language pack to score with (default: auto-detect "
                         "per input; falls back to en + structural checks "
                         "when unsure)")
    ap.add_argument("--config", metavar="PATH",
                    help="path to a .noslop.json config (default: search upward from cwd)")
    ap.add_argument("--no-config", action="store_true",
                    help="ignore any .noslop.json / .nosloprc, even if one is found")
    ap.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                    help="glob pattern to skip (repeatable); also see .noslopignore")
    ap.add_argument("--version", action="version", version=f"noslop {__version__}")
    args = ap.parse_args(argv)

    config = None
    if not args.no_config:
        if args.config and not os.path.isfile(args.config):
            print(f"noslop: {args.config}: no such file", file=sys.stderr)
            return 2
        config_path = args.config or find_config(os.getcwd())
        if config_path:
            try:
                config = load_config(config_path)
            except (ValueError, OSError) as exc:
                print(f"noslop: {exc}", file=sys.stderr)
                return 2

    ignore_patterns = list(args.exclude)
    if os.path.isfile(".noslopignore"):
        ignore_patterns += load_ignore_file(".noslopignore")

    # Expand any glob argument ourselves. POSIX shells already do this
    # before we see argv, but PowerShell and cmd.exe never expand
    # wildcards, so "noslop docs/*.md" would otherwise reach open() as a
    # literal, nonexistent path on Windows.
    paths = []
    for p in (args.paths or ["-"]):
        if p != "-" and any(ch in p for ch in "*?["):
            matches = sorted(glob.glob(p))
            matches = [m for m in matches if not is_ignored(m, ignore_patterns)]
            if not matches:
                print(f"noslop: {p}: no files match", file=sys.stderr)
                return 2
            paths.extend(matches)
        elif p != "-" and is_ignored(p, ignore_patterns):
            continue
        else:
            paths.append(p)

    # A bare `noslop` on an interactive terminal sits waiting on stdin with
    # no prompt, which looks like a hang. Say so on stderr - stdout stays
    # untouched, so piped and redirected output is unaffected.
    if "-" in paths and getattr(sys.stdin, "isatty", lambda: False)():
        print("noslop: reading from stdin - paste text, then press Ctrl-D "
              "(Ctrl-Z then Enter on Windows), or pass a file path instead",
              file=sys.stderr)

    results = []
    for p in paths:
        # Mode is decided per file, so `noslop README.md src/*.py` scores
        # the README as prose and the sources as code in one run.
        ext = os.path.splitext(p)[1].lower() if p != "-" else ""
        code_mode = args.code or (not args.prose and ext in CODE_EXTENSIONS)
        try:
            text = load_text(p, force_markdown=args.markdown and not code_mode)
        except OSError as exc:
            print(f"noslop: {p}: {exc.strerror or exc}", file=sys.stderr)
            return 2
        if code_mode:
            r = analyze_code(text, ext=ext or None, config=config,
                             lang=args.lang)
        else:
            # Language is resolved per input, not per run - a docs sweep can
            # mix English and translated files, and the config's ignore/extra
            # lists apply to whichever pack each file lands on.
            code, source = resolve_language(text, args.lang)
            pack = LANGUAGES[code]
            bw, ph = ((None, None) if config is None else
                      apply_config(config, pack["buzzwords"], pack["phrases"]))
            r = analyze(text, buzzwords=bw, phrases=ph, lang=code, lang_source=source)
        if p != "-":
            r["path"] = p
        results.append((p, r))

    def final_score(r):
        return r["score_per_100"] if r["mode"] == "code" else r["score_per_1k"]

    if args.rdjson:
        for p, r in results:
            emitter = to_rdjsonl_code if r["mode"] == "code" else to_rdjsonl
            for line in emitter(p, r):
                print(line)
    elif args.json:
        payload = results[0][1] if len(results) == 1 else [r for _, r in results]
        print(json.dumps(payload, indent=2))
    else:
        multi = len(results) > 1
        blocks = []
        for p, r in results:
            body = (report_code(r, quiet=args.quiet) if r["mode"] == "code"
                    else report(r, quiet=args.quiet))
            if multi and args.quiet:
                blocks.append(f"{p}: {body}")
            elif multi:
                blocks.append(f"== {p} ==\n{body}")
            else:
                blocks.append(body)
        print("\n".join(blocks) if (multi and args.quiet) else "\n\n".join(blocks))
    return 0 if all(final_score(r) < args.threshold for _, r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
