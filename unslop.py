#!/usr/bin/env python3
"""unslop - flag the AI tells in a piece of writing.

Reads text from file arguments or stdin and prints the patterns that make prose
read as LLM-generated: filler phrases, overused buzzwords, the "not just X, but Y"
frame, em-dash spray, emoji, and suspiciously even sentence rhythm. It does NOT
rewrite anything - that's your job. It just shows you where to look.

Speaks more than English: each language in LANGUAGES carries its own researched
tell lists (an LLM's crutch words in Spanish are Spanish, not translations of
the English list). Input language is sniffed per file, or forced with --lang;
text that can't be confidently identified falls back to the English pack plus
the structural checks, and the output says so.

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
import os
import fnmatch
import argparse

__version__ = "0.5.0"

# analyze()'s return dict is unslop's only machine-readable contract. If you
# add, rename, or remove a top-level key, update this set and bump the
# version - anything parsing --json is relying on these names staying put.
JSON_SCHEMA_KEYS = {
    "words", "score_per_1k", "verdict", "language", "language_source",
    "buzzwords", "phrases", "patterns",
    "em_dashes", "em_dash_excess", "emoji", "bold_label_bullets",
    "sentence_uniformity_cv",
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
# language.
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
            "gran pregunta", "excelente pregunta", "como modelo de lenguaje",
            "como inteligencia artificial", "desbloquea todo tu potencial",
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
            "en tant que modèle de langage",
            "en tant qu'intelligence artificielle",
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
            "als ki-modell", "als sprachmodell",
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
            "como modelo de linguagem", "como inteligência artificial",
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
            "come modello linguistico", "come intelligenza artificiale",
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
            "uitstekende vraag", "als taalmodel", "als ai-model",
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
        ],
        "phrases": [
            "важно отметить", "стоит отметить", "следует отметить",
            "нельзя не отметить", "в современном мире",
            "в быстро меняющемся мире", "давайте погрузимся",
            "давайте разберемся", "в заключение", "подводя итог",
            "в двух словах", "как языковая модель",
            "как искусственный интеллект", "надеюсь, это поможет",
            "не стесняйтесь", "отличный вопрос", "когда речь заходит о",
            "широкий спектр возможностей", "открывает новые горизонты",
            "играет ключевую роль", "играет важную роль",
            "хочу подчеркнуть",
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
            "на завершення", "у двох словах", "як мовна модель",
            "як штучний інтелект", "сподіваюся, це допоможе",
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
            "świetne pytanie", "jako model językowy",
            "jako sztuczna inteligencja", "kiedy przychodzi do",
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
            "jako jazykový model", "jako umělá inteligence",
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
            "bir yapay zeka olarak", "bir dil modeli olarak",
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
            "i slutändan", "som en ai", "som en språkmodell",
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
            "la sfârșitul zilei", "ca inteligență artificială",
            "ca model lingvistic", "nu ezita să", "sper că te ajută",
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
            "mesterséges intelligenciaként", "nyelvi modellként",
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
            "loppujen lopuksi", "tekoälynä", "kielimallina",
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


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


CONFIG_NAMES = (".unslop.json", ".unsloprc")


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
    """Read a .unslopignore file: one gitignore-style glob per line, blank
    lines and #-comments skipped."""
    patterns = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def is_ignored(path, patterns):
    """Match a path against .unslopignore-style patterns. Matches against
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
    `unslop --rdjson file.md | reviewdog -f=rdjsonl -name=unslop` works with
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
    for label, rx, weight, hint in pack["patterns"]:
        matches = list(re.finditer(rx, text))
        if matches:
            pat.append((label, len(matches), weight, hint,
                        [line_of(text, m.start()) for m in matches[:5]]))

    emdash = len(re.findall(r"—", text))
    emoji = len(EMOJI.findall(text))

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    slens = [len(re.findall(r"(?:[^\W\d_]|['\-])+", s)) for s in sentences if s.strip()]
    uniformity = None
    if len(slens) >= 5:
        mean = sum(slens) / len(slens)
        sd = (sum((x - mean) ** 2 for x in slens) / len(slens)) ** 0.5
        uniformity = round((sd / mean) if mean else 0, 2)

    raw = (buzz_total * 3) + (phr_total * 3)
    for _, n, weight, _, _ in pat:
        raw += n * weight
    # Dialogue-dash languages get a wider allowance (see em_dash_factor in
    # LANGUAGES) - an em-dash budget tuned for English prose would flag
    # ordinary Spanish or French dialogue punctuation.
    emdash_excess = max(0, emdash - int(max(2, wc // 90) * pack["em_dash_factor"]))
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
        "language": code, "language_source": source,
        "buzzwords": buzz, "phrases": phr, "patterns": pat,
        "em_dashes": emdash, "em_dash_excess": emdash_excess, "emoji": emoji,
        "bold_label_bullets": bold_bullets, "sentence_uniformity_cv": uniformity,
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
    # Windows consoles default to a legacy code page, and the language packs'
    # names, labels, and hints are not all cp1252-encodable. Emit UTF-8 and
    # degrade to replacement characters rather than crash mid-report.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="unslop", description="Flag the AI tells in a piece of writing.")
    ap.add_argument("paths", nargs="*", default=["-"], metavar="path",
                    help="text files, or - for stdin (default: stdin)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--rdjson", action="store_true",
                    help="emit rdjsonl (reviewdog diagnostic format) instead of the normal report")
    ap.add_argument("--quiet", action="store_true", help="verdict line only")
    ap.add_argument("--markdown", action="store_true",
                    help="skip fenced/inline code when scoring (automatic for .md files)")
    ap.add_argument("--threshold", type=float, default=10.0,
                    help="score at/above which exit code is 1 (default 10)")
    ap.add_argument("--lang", default="auto", choices=["auto"] + sorted(LANGUAGES),
                    help="language pack to score with (default: auto-detect "
                         "per input; falls back to en + structural checks "
                         "when unsure)")
    ap.add_argument("--config", metavar="PATH",
                    help="path to a .unslop.json config (default: search upward from cwd)")
    ap.add_argument("--no-config", action="store_true",
                    help="ignore any .unslop.json / .unsloprc, even if one is found")
    ap.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                    help="glob pattern to skip (repeatable); also see .unslopignore")
    ap.add_argument("--version", action="version", version=f"unslop {__version__}")
    args = ap.parse_args(argv)

    config = None
    if not args.no_config:
        if args.config and not os.path.isfile(args.config):
            print(f"unslop: {args.config}: no such file", file=sys.stderr)
            return 2
        config_path = args.config or find_config(os.getcwd())
        if config_path:
            try:
                config = load_config(config_path)
            except (ValueError, OSError) as exc:
                print(f"unslop: {exc}", file=sys.stderr)
                return 2

    ignore_patterns = list(args.exclude)
    if os.path.isfile(".unslopignore"):
        ignore_patterns += load_ignore_file(".unslopignore")

    # Expand any glob argument ourselves. POSIX shells already do this
    # before we see argv, but PowerShell and cmd.exe never expand
    # wildcards, so "unslop docs/*.md" would otherwise reach open() as a
    # literal, nonexistent path on Windows.
    paths = []
    for p in (args.paths or ["-"]):
        if p != "-" and any(ch in p for ch in "*?["):
            matches = sorted(glob.glob(p))
            matches = [m for m in matches if not is_ignored(m, ignore_patterns)]
            if not matches:
                print(f"unslop: {p}: no files match", file=sys.stderr)
                return 2
            paths.extend(matches)
        elif p != "-" and is_ignored(p, ignore_patterns):
            continue
        else:
            paths.append(p)

    results = []
    for p in paths:
        try:
            text = load_text(p, force_markdown=args.markdown)
        except OSError as exc:
            print(f"unslop: {p}: {exc.strerror or exc}", file=sys.stderr)
            return 2
        # Language is resolved per input, not per run - a docs sweep can mix
        # English and translated files, and the config's ignore/extra lists
        # apply to whichever pack each file lands on.
        code, source = resolve_language(text, args.lang)
        pack = LANGUAGES[code]
        bw, ph = ((None, None) if config is None else
                  apply_config(config, pack["buzzwords"], pack["phrases"]))
        r = analyze(text, buzzwords=bw, phrases=ph, lang=code, lang_source=source)
        if p != "-":
            r["path"] = p
        results.append((p, r))

    if args.rdjson:
        for p, r in results:
            for line in to_rdjsonl(p, r):
                print(line)
    elif args.json:
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
