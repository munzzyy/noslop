/*
 * noslop detector - browser/Node port of the analyze() core in noslop.py.
 *
 * This is a faithful reimplementation of the Python scorer so the web app
 * gives the exact same number the CLI does. web/parity.js checks that against
 * `py noslop.py --json` on every commit; if you touch the word lists, the
 * language packs, or the math here, update noslop.py to match (or the parity
 * job goes red).
 *
 * Loads two ways with no build step:
 *   - browser:  <script src="detector.js"></script>  ->  window.Noslop
 *   - Node:     const Noslop = require("./detector.js")
 * No imports, no network, no dependencies - same promise as the CLI.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.Noslop = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  // ---- English lists (kept in lockstep with noslop.py) ----

  const BUZZWORDS = [
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
    // Post-2024 additions - see the annotated list in noslop.py.
    "groundbreaking", "aligns", "surpassing", "surpasses",
    "emphasizing", "comprehending",
    "showcases", "trailblazing", "bolstered", "resonate", "resonates",
    "solidify", "solidifies", "solidifying", "diverse array", "focal point",
    "indelible mark", "deeply rooted",
    "enduring legacy", "lasting legacy",
  ];

  const PHRASES = [
    "it's important to note", "it is important to note", "it's worth noting",
    "it is worth noting", "in conclusion", "in summary", "to sum up",
    "that said", "rest assured", "needless to say", "at the end of the day",
    "in today's world", "in today's fast-paced", "let's dive", "dive into",
    "let's break it down", "here's the thing", "i hope this helps",
    "feel free to", "happy to help", "great question",
    // "as an ai" / "as a language model" moved to AI_ARTIFACT_PHRASES in
    // 0.9.0 - see the note there.
    "this is where", "look no further",
    "without further ado", "the key takeaway", "let's explore",
    "let's take a look", "buckle up", "when it comes to", "at its core",
    "the world of", "in the realm of", "plays a vital role",
    "plays a crucial role", "a wide range of", "more than just",
    "not just a", "whether you're a", "gone are the days",
    // Significance inflation and chat-native framing - see noslop.py for
    // the annotated list and what's deliberately absent.
    "stands as a testament", "a testament to", "marks a pivotal",
    "a pivotal moment", "continues to captivate", "continues to thrive",
    "cements its legacy", "solidifies its position", "leaves a lasting",
    "setting the stage for", "represents a significant shift",
    "industry experts note", "experts agree that",
    "observers have noted", "in a world where",
  ];

  // [label, regex (on original-case text), weight, hint]
  //
  // Word boundaries are written as explicit Unicode lookarounds, not \b:
  // JS \b is ASCII-only regardless of the u flag, so "buté" would end a
  // "word" mid-token and these patterns would fire on accented text that
  // Python's Unicode-aware \b never matches. Same idiom as needleRegex()
  // and the es pack. Apostrophes match straight or curly forms because
  // patterns run on the raw text, not the normalized copy.
  const PATTERNS = [
    ["'not just X but Y' construction",
      /(?<![\p{L}\p{N}_])not (?:just|only)(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])but(?![\p{L}\p{N}_])/gu, 3,
      "state it plainly instead of the contrast frame"],
    ["'it isn't X, it's Y' flip",
      /(?<![\p{L}\p{N}_])is(?:n['’]t| not)(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])it(?:['’]s| is)(?![\p{L}\p{N}_])/gu, 2,
      "just say what it is"],
    ["rhetorical question opener",
      /^\s*(?:ever wondered|have you ever|what if|imagine (?:a|if|that)|picture this)(?![\p{L}\p{N}_])/gimu, 2,
      "open with the point, not a hook"],
    ["hedge stack (may/can/often/typically)",
      /(?<![\p{L}\p{N}_])(?:may|might|can|could|often|typically|generally|usually|arguably)(?![\p{L}\p{N}_])/gu, 0,
      "too many hedges reads evasive - commit or cut"],
    // The 2025 wave - see the annotated entries in noslop.py. 5th element,
    // when present, is free hits (occurrences that don't score).
    ["dangling '-ing' significance closer",
      /,\s+(?:highlighting|reflecting|symbolizing|cementing|reinforcing|cultivating|encompassing)(?![\p{L}\p{N}_])[^.?!\n]{0,80}[.?!]/giu, 3,
      "end at the fact - the tacked-on significance clause adds nothing", 1],
    ["'It's not X. It's Y.' split flip",
      /(?<![\p{L}\p{N}_])(?:is(?:n['’]t| not)|are(?:n['’]t| not)|does(?:n['’]t| not)|was(?:n['’]t| not))(?![\p{L}\p{N}_])[^.?!\n]{1,60}[.!]\s+it(?:['’]s| is)(?![\p{L}\p{N}_])/giu, 3,
      "merge the flip into one plain statement of what it is", 1],
    ["anaphora triad (where X, where Y, where Z)",
      /(?<![\p{L}\p{N}_])(?!(?:and|or|nor|the|an?)(?![\p{L}\p{N}_]))([a-z]{2,12})(?![\p{L}\p{N}_])[^,.?!\n]{2,40},\s+\1(?![\p{L}\p{N}_])[^,.?!\n]{2,40},\s+(?:and\s+)?\1(?![\p{L}\p{N}_])/giu, 2,
      "one of the three carries the point - keep that one", 1],
    ["ta-da opener ('Here's why...')",
      /^\s*#*\s*here['’]s (?:why|how|what)(?![\p{L}\p{N}_])/gimu, 2,
      "skip the reveal frame - state the thing itself"],
    ["fragment hook ('The result?')",
      /(?:^\s*|(?<=[.!?])\s+)(?:the result|the best part|the catch|the takeaway|the kicker|the bottom line|translation)\?/gimu, 2,
      "answer in the same sentence, or cut the hook"],
    ["sycophantic opener",
      /^\s*(?:great question|certainly|absolutely|of course|sure thing)!/gimu, 3,
      "drop the chat-style opener - prose isn't answering anyone"],
    ["'despite challenges ... continues to' arc",
      /(?<![\p{L}\p{N}_])despite(?![\p{L}\p{N}_])[^.?!\n]{0,80}?(?<![\p{L}\p{N}_])(?:challenges|obstacles|setbacks|hurdles)(?![\p{L}\p{N}_])[^.?!\n]{0,120}?(?<![\p{L}\p{N}_])continues? to(?![\p{L}\p{N}_])/giu, 2,
      "name the specific challenge and the specific response"],
  ];

  // Chat-UI residue - mirrors AI_ARTIFACTS in noslop.py. Direct paste
  // evidence: a single hit pins the score at the hard-verdict floor.
  // Template placeholders are deliberately absent - humans write those.
  const AI_ARTIFACTS = [
    ["chatbot citation residue (oaicite)", "oaicite"],
    ["chatbot citation residue (oai_citation)", "oai_citation"],
    ["chatbot citation residue (grok_card)", "grok_card"],
    ["chatgpt.com link-tracking parameter", "utm_source=chatgpt.com"],
    ["openai link-tracking parameter", "utm_source=openai"],
    // Coding-tool signatures - literal strings the tools write into commit
    // messages and PR bodies by default. Presence is proof; absence proves
    // nothing. The Claude trailer matches on the noreply address so a human
    // co-author actually named Claude doesn't trip it.
    ["Claude Code commit trailer", "noreply@anthropic.com"],
    ["Claude Code PR footer", "generated with [claude code]"],
    ["Cursor agent commit trailer", "cursoragent@cursor.com"],
    ["Devin commit trailer", "devin-ai-integration"],
    ["AI chat share link", "claude.ai/share"],
    ["AI chat share link", "chatgpt.com/share"],
    ["AI chat share link", "chat.openai.com/share"],
    ["AI chat share link", "gemini.google.com/share"],
  ];

  // Chatbot disclaimer sentences - same floor-at-25 tier as AI_ARTIFACTS,
  // but matched with findAll()'s word-boundary search (not a bare
  // indexOf scan) since these are natural-language phrases that can wrap
  // across an edited line, not markup tokens that sit inside a URL.
  // Mirrors AI_ARTIFACT_PHRASES in noslop.py.
  const AI_ARTIFACT_PHRASES = [
    ["chatbot self-reference (\"as an AI\")", "as an ai"],
    ["chatbot self-reference (\"as a language model\")", "as a language model"],
    ["chatbot knowledge-cutoff disclaimer (\"as of my last update\")", "as of my last update"],
    ["chatbot knowledge-cutoff disclaimer (\"as of my knowledge cutoff\")", "as of my knowledge cutoff"],
    ["chatbot no-browsing disclaimer (\"I don't have real-time access\")", "i don't have real-time access"],
    ["chatbot no-browsing disclaimer (\"I cannot browse the internet\")", "i cannot browse the internet"],
  ];

  // Sentence-initial connective adverbs for the en pack - scored on
  // density over an allowance, mirroring noslop.py. Packs without a
  // connectives list skip the check.
  const EN_CONNECTIVES = [
    "moreover", "furthermore", "additionally", "notably",
    "ultimately", "importantly", "crucially", "significantly",
    "in essence", "overall",
  ];

  // Copula-avoidance and scope-inflation filler - mirrors COPULA_AVOIDANCE/
  // SCOPE_INFLATION in noslop.py. English only for now.
  const COPULA_AVOIDANCE = [
    "serves as a", "stands as a", "functions as a", "acts as a testament",
  ];
  const COPULA_AVOIDANCE_MIN_PER_1K = 2.0;
  const SCOPE_INFLATION = [
    "cannot be overstated", "cannot be understated", "in every sense of the word",
    "from the moment",
  ];

  // Generic AI-listicle headings - mirrors GENERIC_HEADINGS in noslop.py.
  // Only scores at 2+ hits in one document.
  const GENERIC_HEADINGS = new Set([
    "introduction", "conclusion", "overview", "key takeaways",
    "final thoughts", "in summary", "background", "the bottom line",
    "why it matters", "getting started",
  ]);

  // Bare bullet glyphs opening a line - mirrors BARE_BULLET_RE.
  const BARE_BULLET_RE = /^[ \t]*[•▪‣]/gm;

  // Sentence-punctuation entropy - mirrors punct_entropy() in noslop.py.
  const PUNCT_CLASS = new Set(".,;:!?…()'\"’“”—-".split(""));
  const PUNCT_ENTROPY_MIN_CHARS = 30;
  const PUNCT_ENTROPY_LOW = 0.55;

  function punctEntropy(text) {
    const counts = new Map();
    let total = 0;
    for (const ch of text) {
      if (PUNCT_CLASS.has(ch)) {
        counts.set(ch, (counts.get(ch) || 0) + 1);
        total++;
      }
    }
    if (total < PUNCT_ENTROPY_MIN_CHARS) return null;
    const classes = counts.size;
    if (classes <= 1) return 0.0;
    let ent = 0;
    for (const c of counts.values()) {
      const p = c / total;
      ent -= p * Math.log2(p);
    }
    return pyRound(ent / Math.log2(classes), 3);
  }

  // Per-language "density crutch" words - mirrors DENSITY_CRUTCH_ALLOWANCE_DIVISOR
  // and pack["density_crutch"] in noslop.py. A pack opts in with a
  // densityCrutch array; packs without one skip the check.
  const DENSITY_CRUTCH_ALLOWANCE_DIVISOR = 150;

  // ---- language packs (kept in lockstep with LANGUAGES in noslop.py) ----
  //
  // Same idea as the Python side: every language carries its own researched
  // tell lists - an LLM's crutch words in Spanish are Spanish words, not
  // translations of the English list. Pack order matters: detection ties
  // resolve by insertion order, identically in both implementations.

  const LANGUAGES = {
    "en": {
      name: "English",
      buzzwords: BUZZWORDS,
      phrases: PHRASES,
      patterns: PATTERNS,
      stopwords: new Set([
        "the", "and", "of", "to", "is", "that", "it", "with", "for",
        "this", "was", "are", "have", "but", "they", "from", "not",
        "what", "you", "all",
      ]),
      connectives: EN_CONNECTIVES,
      copulaAvoidance: COPULA_AVOIDANCE,
      scopeInflation: SCOPE_INFLATION,
      marks: "",
      emDashFactor: 1.0,
    },
    "es": {
      name: "Español",
      buzzwords: [
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
      phrases: [
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
        // "como modelo de lenguaje" / "como inteligencia artificial" moved
        // to artifactPhrases below in 0.9.0.
        "desbloquea todo tu potencial",
        "libera todo tu potencial", "ya seas", "tanto si eres",
        "atrás quedaron los días", "más que un simple",
        "juega un papel crucial", "juega un papel fundamental",
        "desempeña un papel", "una amplia variedad de",
        "cuando se trata de",
      ],
      patterns: [
        // Boundaries are Unicode lookarounds, not \b - see needleRegex().
        ["construcción 'no solo X, sino Y'",
          /(?<![\p{L}\p{N}_])no (?:solo|sólo|solamente)(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])sino(?![\p{L}\p{N}_])/giu, 3,
          "dilo directamente, sin el marco de contraste"],
        ["giro 'no es X, es Y'",
          /(?<![\p{L}\p{N}_])no es(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])es(?![\p{L}\p{N}_])/giu, 2,
          "di lo que es, sin el rodeo"],
        ["pregunta retórica de apertura",
          /^\s*(?:¿alguna vez te has preguntado|¿te has preguntado|¿alguna vez has|imagina (?:un|una|que)|imagínate|¿qué pasaría si)/gim, 2,
          "abre con la idea, no con el gancho"],
        ["acumulación de matizadores (puede/podría/a menudo)",
          /(?<![\p{L}\p{N}_])(?:puede|podría|podrían|a menudo|generalmente|típicamente|usualmente|posiblemente|quizás|tal vez)(?![\p{L}\p{N}_])/giu, 0,
          "tantos matices suenan evasivos - afirma o corta"],
      ],
      // es was one of the three packs that got researched knowledge-cutoff
      // / no-browsing variants this pass (see AI_ARTIFACT_PHRASES).
      artifactPhrases: [
        ["autorreferencia de chatbot (modelo de lenguaje)", "como modelo de lenguaje"],
        ["autorreferencia de chatbot (ia)", "como inteligencia artificial"],
        ["aviso de chatbot (sin acceso en tiempo real)", "no tengo acceso a internet en tiempo real"],
        ["aviso de chatbot (fecha de corte de conocimiento)", "mi conocimiento tiene fecha de corte"],
      ],
      stopwords: new Set([
        "el", "la", "los", "las", "de", "que", "y", "en", "un", "una",
        "es", "por", "para", "con", "como", "pero", "más", "muy", "sin",
        "sobre", "esto", "hay",
      ]),
      marks: "ñ¿¡",
      emDashFactor: 2.5,
    },
    "fr": {
      name: "Français",
      buzzwords: [
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
      phrases: [
        "il est important de noter", "il est important de souligner",
        "il convient de noter", "il convient de souligner",
        "il est essentiel de", "notez que", "en conclusion", "en résumé",
        "pour résumer", "en fin de compte", "au bout du compte",
        "dans le monde d'aujourd'hui", "à l'ère du numérique",
        "dans un monde en constante évolution", "plongeons dans",
        "explorons", "penchons-nous sur", "j'espère que cela vous aide",
        "j'espère que cela aide", "n'hésitez pas à",
        "excellente question", "très bonne question",
        // "en tant que modèle de langage" / "...intelligence artificielle"
        // moved to artifactPhrases below in 0.9.0.
        "libérez tout votre potentiel", "que vous soyez",
        "joue un rôle crucial", "joue un rôle essentiel",
        "une large gamme de", "lorsqu'il s'agit de",
        "bien plus qu'un simple", "l'époque où",
      ],
      patterns: [
        ["construction 'pas seulement X, c'est Y'",
          /(?<![\p{L}\p{N}_])ce n[’']est pas (?:seulement|juste|simplement)(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])c[’']est(?![\p{L}\p{N}_])/giu, 3,
          "dites-le directement, sans le cadre de contraste"],
        ["bascule 'n'est pas X, c'est Y'",
          /(?<![\p{L}\p{N}_])n[’']est pas(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])c[’']est(?![\p{L}\p{N}_])/giu, 2,
          "dites simplement ce que c'est"],
        ["question rhétorique d'ouverture",
          /^\s*(?:vous êtes-vous déjà demandé|avez-vous déjà|et si|imaginez|qu[’']en serait-il si)(?![\p{L}\p{N}_])/gimu, 2,
          "ouvrez sur l'idée, pas sur l'accroche"],
        ["empilement de précautions (peut/pourrait/souvent)",
          /(?<![\p{L}\p{N}_])(?:peut|pourrait|pourraient|souvent|généralement|typiquement|habituellement|sans doute|peut-être)(?![\p{L}\p{N}_])/giu, 0,
          "trop de précautions sonne évasif - affirmez ou coupez"],
      ],
      artifactPhrases: [
        ["auto-référence de chatbot (modèle de langage)", "en tant que modèle de langage"],
        ["auto-référence de chatbot (ia)", "en tant qu'intelligence artificielle"],
      ],
      stopwords: new Set([
        "le", "la", "les", "des", "de", "et", "est", "une", "un", "dans",
        "que", "pour", "avec", "sur", "pas", "qui", "nous", "vous",
        "plus", "mais", "ce", "aux",
      ]),
      marks: "êœâ",
      emDashFactor: 2.5,
    },
    "de": {
      name: "Deutsch",
      buzzwords: [
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
      phrases: [
        // both orders: German V2 inverts the frame after a fronted
        // adverbial ("In der heutigen Welt ist es wichtig zu beachten")
        "es ist wichtig zu beachten", "ist es wichtig zu beachten",
        "es ist wichtig zu betonen", "ist es wichtig zu betonen",
        "es sei darauf hingewiesen", "es ist erwähnenswert",
        "zusammenfassend lässt sich sagen",
        "abschließend lässt sich sagen", "am ende des tages",
        "in der heutigen schnelllebigen welt", "im digitalen zeitalter",
        "in der heutigen zeit", "tauchen wir ein", "tauchen sie ein",
        "lassen sie uns eintauchen", "ich hoffe, das hilft",
        "zögern sie nicht", "gute frage", "ausgezeichnete frage",
        // "als ki-modell" / "als sprachmodell" moved to artifactPhrases
        // below in 0.9.0.
        "entfesseln sie ihr volles potenzial",
        "schöpfen sie ihr volles potenzial aus", "egal, ob sie",
        "ganz gleich, ob sie", "spielt eine entscheidende rolle",
        "spielt eine wichtige rolle", "eine breite palette",
        "eine große auswahl an", "wenn es darum geht",
        "mehr als nur ein", "die zeiten, in denen",
      ],
      patterns: [
        ["'nicht nur X, sondern Y'-Konstruktion",
          /(?<![\p{L}\p{N}_])nicht nur(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])sondern(?![\p{L}\p{N}_])/giu, 3,
          "sag es direkt, ohne den Kontrastrahmen"],
        ["'ist nicht X, es ist Y'-Wendung",
          /(?<![\p{L}\p{N}_])ist (?:kein|keine|nicht)(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])es ist(?![\p{L}\p{N}_])/giu, 2,
          "sag einfach, was es ist"],
        ["rhetorische Eröffnungsfrage",
          /^\s*(?:haben sie sich jemals gefragt|hast du dich jemals gefragt|stellen sie sich vor|stell dir vor|was wäre, wenn|was wäre wenn)(?![\p{L}\p{N}_])/gimu, 2,
          "beginn mit dem Punkt, nicht mit dem Köder"],
        ["Absicherungs-Stapel (kann/könnte/oft)",
          /(?<![\p{L}\p{N}_])(?:kann|könnte|könnten|oft|typischerweise|in der regel|üblicherweise|möglicherweise|vielleicht)(?![\p{L}\p{N}_])/giu, 0,
          "so viel Absicherung wirkt ausweichend - behaupten oder streichen"],
      ],
      // de was one of the three packs that got researched knowledge-cutoff
      // / no-browsing variants this pass (see AI_ARTIFACT_PHRASES).
      artifactPhrases: [
        ["Chatbot-Selbstbezug (als KI-Modell)", "als ki-modell"],
        ["Chatbot-Selbstbezug (als Sprachmodell)", "als sprachmodell"],
        ["Chatbot-Hinweis (kein Echtzeitzugriff)", "ich habe keinen zugriff auf das internet in echtzeit"],
        ["Chatbot-Hinweis (Wissensstand-Stichtag)", "mein wissensstand reicht bis"],
      ],
      stopwords: new Set([
        "der", "die", "das", "und", "ist", "nicht", "mit", "für", "auf",
        "ein", "eine", "den", "von", "zu", "sich", "auch", "sind",
        "wird", "dass", "wie", "im", "es",
      ]),
      marks: "ßäö",
      emDashFactor: 1.5,
    },
    "pt-BR": {
      name: "Português (Brasil)",
      buzzwords: [
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
      phrases: [
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
        // "como modelo de linguagem" / "como inteligência artificial"
        // moved to artifactPhrases below in 0.9.0.
        "desbloqueie todo o seu potencial",
        "libere todo o seu potencial", "seja você", "quer você seja",
        "desempenha um papel crucial",
        "desempenha um papel fundamental", "uma ampla variedade de",
        "quando se trata de", "mais do que um simples",
        "ficaram para trás os dias", "longe vão os dias",
      ],
      patterns: [
        ["construção 'não é apenas X, mas Y'",
          /(?<![\p{L}\p{N}_])não (?:é|se trata) (?:apenas|só|somente)(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])(?:mas|é)(?![\p{L}\p{N}_])/giu, 3,
          "diga diretamente, sem o quadro de contraste"],
        ["virada 'não é X, é Y'",
          /(?<![\p{L}\p{N}_])não é(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])é(?![\p{L}\p{N}_])/giu, 2,
          "diga o que é, sem o rodeio"],
        ["pergunta retórica de abertura",
          /^\s*(?:você já se perguntou|já se perguntou|já imaginou|imagine (?:um|uma|que)|e se)(?![\p{L}\p{N}_])/gimu, 2,
          "abra com o ponto, não com a isca"],
        ["pilha de ressalvas (pode/poderia/frequentemente)",
          /(?<![\p{L}\p{N}_])(?:pode|poderia|poderiam|frequentemente|geralmente|tipicamente|normalmente|possivelmente|talvez)(?![\p{L}\p{N}_])/giu, 0,
          "tanta ressalva soa evasivo - afirme ou corte"],
      ],
      artifactPhrases: [
        ["autorreferência de chatbot (modelo de linguagem)", "como modelo de linguagem"],
        ["autorreferência de chatbot (ia)", "como inteligência artificial"],
      ],
      stopwords: new Set([
        "o", "os", "as", "de", "que", "e", "em", "um", "uma", "é",
        "não", "para", "com", "mais", "você", "são", "como", "mas",
        "isso", "foi", "tem", "muito",
      ]),
      marks: "ãõ",
      emDashFactor: 2.5,
    },
    "it": {
      name: "Italiano",
      buzzwords: [
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
      phrases: [
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
        // "come modello linguistico" / "come intelligenza artificiale"
        // moved to artifactPhrases below in 0.9.0.
        "sblocca tutto il tuo potenziale",
        "libera tutto il tuo potenziale", "che tu sia",
        "svolge un ruolo cruciale", "svolge un ruolo fondamentale",
        "gioca un ruolo cruciale", "un'ampia gamma di",
        "quando si tratta di", "molto più di un semplice",
        "sono lontani i tempi",
      ],
      patterns: [
        ["costruzione 'non solo X, ma Y'",
          /(?<![\p{L}\p{N}_])non (?:è|si tratta) (?:solo|soltanto|semplicemente)(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])(?:ma|è)(?![\p{L}\p{N}_])/giu, 3,
          "dillo direttamente, senza la cornice di contrasto"],
        ["svolta 'non è X, è Y'",
          /(?<![\p{L}\p{N}_])non è(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])è(?![\p{L}\p{N}_])/giu, 2,
          "di' semplicemente cos'è"],
        ["domanda retorica di apertura",
          /^\s*(?:ti sei mai chiesto|vi siete mai chiesti|hai mai|immagina (?:un|una|che)|e se)(?![\p{L}\p{N}_])/gimu, 2,
          "apri con il punto, non con l'esca"],
        ["pila di cautele (può/potrebbe/spesso)",
          /(?<![\p{L}\p{N}_])(?:può|potrebbe|potrebbero|spesso|generalmente|tipicamente|solitamente|possibilmente|forse)(?![\p{L}\p{N}_])/giu, 0,
          "troppe cautele suonano evasive - afferma o taglia"],
      ],
      artifactPhrases: [
        ["autoreferenza del chatbot (modello linguistico)", "come modello linguistico"],
        ["autoreferenza del chatbot (ia)", "come intelligenza artificiale"],
      ],
      stopwords: new Set([
        "il", "la", "le", "gli", "di", "che", "e", "è", "per", "con",
        "non", "un", "una", "sono", "del", "della", "più", "anche",
        "come", "ma", "questo", "si",
      ]),
      marks: "òì",
      emDashFactor: 2.5,
    },
    "nl": {
      name: "Nederlands",
      buzzwords: [
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
      phrases: [
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
        // "als taalmodel" / "als ai-model" moved to artifactPhrases below
        // in 0.9.0.
        "ontgrendel je volledige potentieel",
        "ontketen je volledige potentieel", "of je nu",
        "speelt een cruciale rol", "speelt een belangrijke rol",
        "een breed scala aan", "als het gaat om",
        "het is niet zomaar", "meer dan alleen een",
        "voorbij zijn de dagen",
      ],
      patterns: [
        ["'niet alleen X, maar Y'-constructie",
          /(?<![\p{L}\p{N}_])niet (?:alleen|enkel|slechts)(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])maar(?![\p{L}\p{N}_])/giu, 3,
          "zeg het gewoon, zonder het contrastframe"],
        ["'is geen X, het is Y'-wending",
          /(?<![\p{L}\p{N}_])is (?:geen|niet)(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])het is(?![\p{L}\p{N}_])/giu, 2,
          "zeg gewoon wat het is"],
        ["retorische openingsvraag",
          /^\s*(?:heb je je ooit afgevraagd|heeft u zich ooit afgevraagd|stel je voor|stelt u zich voor|wat als)(?![\p{L}\p{N}_])/gimu, 2,
          "open met het punt, niet met de lokker"],
        ["stapel voorbehouden (kan/zou kunnen/vaak)",
          /(?<![\p{L}\p{N}_])(?:kan|kunnen|zou kunnen|vaak|meestal|doorgaans|over het algemeen|mogelijk|misschien)(?![\p{L}\p{N}_])/giu, 0,
          "zoveel voorbehoud leest ontwijkend - beweer of schrap"],
      ],
      artifactPhrases: [
        ["chatbot-zelfverwijzing (taalmodel)", "als taalmodel"],
        ["chatbot-zelfverwijzing (ai-model)", "als ai-model"],
      ],
      stopwords: new Set([
        "de", "het", "een", "en", "van", "is", "dat", "niet", "met",
        "voor", "op", "zijn", "aan", "ook", "maar", "naar", "deze",
        "wordt", "uit", "bij", "dan", "te",
      ]),
      marks: "",
      emDashFactor: 1.0,
    },
    "ru": {
      name: "Русский",
      buzzwords: [
        "погрузиться", "погрузитесь", "погружение", "многогранный",
        "многогранная", "бесшовный", "бесшовная", "бесшовно", "целостный",
        "целостная", "синергия", "парадигма", "смена парадигмы",
        "революционный", "революционная", "инновационный", "инновационная",
        "преобразующий", "преобразующая", "трансформационный",
        "раскрыть потенциал", "раскройте свой потенциал", "экосистема",
        "ландшафт", "передовой", "передовые", "ключевую роль",
        "широкий спектр", "неотъемлемая часть", "мощный инструмент",
        "гармонично сочетает", "безграничные возможности",
        "на переднем крае", "краеугольный камень",
        "по-настоящему уникальный",
        // Bureaucratic determiners and nominalizations (канцелярит) -
        // 0.9.0 research pass. Calibrated against a formal-Russian human
        // sample in eval/corpus/human - see eval/README.md.
        "данный", "указанный", "вышеупомянутый",
        "осуществление", "проведение", "обеспечение",
      ],
      phrases: [
        "важно отметить", "стоит отметить", "следует отметить",
        "нельзя не отметить", "в современном мире",
        "в быстро меняющемся мире", "давайте погрузимся",
        "давайте разберемся", "в заключение", "подводя итог",
        "в двух словах",
        // "как языковая модель" / "как искусственный интеллект" moved to
        // artifactPhrases below in 0.9.0.
        "надеюсь, это поможет",
        "не стесняйтесь", "отличный вопрос", "когда речь заходит о",
        "широкий спектр возможностей", "открывает новые горизонты",
        "играет ключевую роль", "играет важную роль", "хочу подчеркнуть",
        // 0.9.0 opener cliché.
        "в эпоху цифровизации",
      ],
      patterns: [
        ["конструкция 'не только X, но и Y'",
          /(?<![\p{L}\p{N}_])не только(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])но и(?![\p{L}\p{N}_])/giu, 3,
          "скажи прямо, без рамки контраста"],
        // Russian doesn't repeat the copula the way English/Romance/German
        // do ("это не X, это Y") - it drops straight into the contrastive
        // "а" after a comma, so the flip is "это не X, а Y".
        ["оборот 'это не X, а Y'",
          /(?<![\p{L}\p{N}_])это не(?![\p{L}\p{N}_])[^.?!\n]{1,45}?,\s*а(?![\p{L}\p{N}_])/giu, 2,
          "просто скажи, что это"],
        ["риторический вопрос-зачин",
          /^\s*(?:задумывались ли вы|а что если|представьте себе|представьте|вы когда-нибудь)(?![\p{L}\p{N}_])/gimu, 2,
          "начни с сути, а не с крючка"],
        ["стопка оговорок (может/вероятно/обычно)",
          /(?<![\p{L}\p{N}_])(?:может|могут|можно|вероятно|как правило|обычно|зачастую|возможно|порой)(?![\p{L}\p{N}_])/giu, 0,
          "столько оговорок звучит уклончиво - утверждай или убери"],
      ],
      // ru was one of the three packs that got researched knowledge-cutoff
      // / no-browsing variants this pass (see AI_ARTIFACT_PHRASES).
      artifactPhrases: [
        ["самоссылка чат-бота (языковая модель)", "как языковая модель"],
        ["самоссылка чат-бота (ИИ)", "как искусственный интеллект"],
        ["оговорка чат-бота (нет доступа в реальном времени)", "у меня нет доступа к интернету в реальном времени"],
        ["оговорка чат-бота (дата отсечки знаний)", "мои знания ограничены датой обучения"],
      ],
      // "является" (is/serves as) is an ordinary Russian copula verb, but
      // LLM Russian leans on it as a formal-register crutch well past the
      // rate of ordinary prose - see DENSITY_CRUTCH_ALLOWANCE_DIVISOR.
      densityCrutch: ["является"],
      stopwords: new Set([
        "в", "все", "для", "же", "за", "и", "из", "к", "как", "на", "не",
        "но", "о", "от", "по", "с", "тоже", "только", "что", "это",
      ]),
      marks: "ыэъ",
      emDashFactor: 2.5,
    },
    "uk": {
      name: "Українська",
      buzzwords: [
        "занурмося", "зануртеся", "зануритися", "багатогранний",
        "багатогранна", "безшовний", "безшовна", "цілісний", "цілісна",
        "синергія", "парадигма", "зміна парадигми", "революційний",
        "революційна", "інноваційний", "інноваційна", "трансформаційний",
        "перетворювальний", "розкрити потенціал", "розкрийте свій потенціал",
        "екосистема", "ландшафт", "передовий", "передові", "ключову роль",
        "широкий спектр", "невід'ємна частина", "потужний інструмент",
        "гармонійно поєднує", "безмежні можливості", "на передньому краї",
        "наріжний камінь", "по-справжньому унікальний",
      ],
      phrases: [
        "важливо зазначити", "варто зазначити", "слід зазначити",
        "у сучасному світі", "у швидкоплинному світі", "давайте зануримося",
        "давайте розберемося", "підсумовуючи", "на завершення",
        "у двох словах",
        // "як мовна модель" / "як штучний інтелект" moved to
        // artifactPhrases below in 0.9.0.
        "сподіваюся, це допоможе", "не соромтеся", "чудове запитання",
        "коли справа доходить до", "широкий спектр можливостей",
        "відкриває нові горизонти", "відіграє ключову роль",
        "відіграє важливу роль", "хочу підкреслити",
      ],
      patterns: [
        ["конструкція 'не тільки X, а й Y'",
          /(?<![\p{L}\p{N}_])не (?:тільки|лише)(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])а (?:й|також)(?![\p{L}\p{N}_])/giu, 3,
          "скажи прямо, без рамки контрасту"],
        // Same insight as Russian: no repeated copula, just the contrastive
        // "а" after a comma.
        ["зворот 'це не X, а Y'",
          /(?<![\p{L}\p{N}_])це не(?![\p{L}\p{N}_])[^.?!\n]{1,45}?,\s*а(?![\p{L}\p{N}_])/giu, 2,
          "просто скажи, що це"],
        ["риторичне питання-зачин",
          /^\s*(?:чи замислювались ви|чи замислювалися ви|а що якщо|уявіть собі|уявіть)(?![\p{L}\p{N}_])/gimu, 2,
          "почни із суті, а не з гачка"],
        ["стос застережень (може/ймовірно/зазвичай)",
          /(?<![\p{L}\p{N}_])(?:може|можуть|можна|ймовірно|як правило|зазвичай|часто|можливо)(?![\p{L}\p{N}_])/giu, 0,
          "стільки застережень звучить ухильно - стверджуй або прибери"],
      ],
      artifactPhrases: [
        ["самопосилання чат-бота (мовна модель)", "як мовна модель"],
        ["самопосилання чат-бота (ШІ)", "як штучний інтелект"],
      ],
      stopwords: new Set([
        "або", "але", "вже", "від", "для", "до", "за", "з", "зі", "лише",
        "на", "не", "також", "теж", "тільки", "у", "це", "що", "як", "який",
        "і",
      ]),
      marks: "іїєґ",
      emDashFactor: 2.5,
    },
    "pl": {
      name: "Polski",
      buzzwords: [
        "zanurz się", "zanurzmy się", "zagłębmy się", "wielowymiarowy",
        "wielowymiarowa", "bezproblemowy", "bezproblemowa",
        "płynne doświadczenie", "kompleksowy", "kompleksowa", "solidny",
        "solidna", "innowacyjny", "innowacyjna", "przełomowy", "przełomowa",
        "transformacyjny", "transformacyjna", "holistyczny", "holistyczna",
        "synergia", "paradygmat", "zmiana paradygmatu",
        "odblokować potencjał", "odblokuj swój potencjał",
        "krajobraz cyfrowy", "świat możliwości", "szeroka gama",
        "mnóstwo możliwości", "wzmacniać", "na najwyższym poziomie",
        "nieoceniony", "kamień węgielny", "wyjątkowy", "na czele",
      ],
      phrases: [
        "warto zauważyć", "warto podkreślić", "należy zauważyć",
        "warto zaznaczyć", "w dzisiejszym świecie",
        "w dzisiejszym dynamicznie zmieniającym się świecie",
        "w erze cyfrowej", "zanurzmy się w", "zagłębmy się w",
        "podsumowując", "reasumując", "na koniec dnia",
        "mam nadzieję, że to pomoże", "nie wahaj się", "śmiało pytaj",
        "świetne pytanie",
        // "jako model językowy" / "jako sztuczna inteligencja" moved to
        // artifactPhrases below in 0.9.0.
        "kiedy przychodzi do",
        "szeroki wachlarz", "otwiera nowe możliwości", "więcej niż tylko",
        "niezależnie od tego, czy jesteś",
      ],
      patterns: [
        ["konstrukcja 'nie tylko X, ale i Y'",
          /(?<![\p{L}\p{N}_])nie tylko(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])ale (?:i|także|również)(?![\p{L}\p{N}_])/giu, 3,
          "powiedz to wprost, bez ramy kontrastu"],
        // Polish leans on "tylko" (rather) for the flip, not a repeated
        // copula - "to nie X, tylko Y", closer to Russian's "а" than to the
        // Romance/Germanic "it's" repeat.
        ["zwrot 'to nie X, tylko Y'",
          /(?<![\p{L}\p{N}_])to nie(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])tylko(?![\p{L}\p{N}_])/giu, 2,
          "powiedz wprost, czym to jest"],
        ["retoryczne pytanie otwierające",
          /^\s*(?:czy zastanawiałeś się|czy zastanawiałaś się|a co jeśli|wyobraź sobie|wyobraźcie sobie)(?![\p{L}\p{N}_])/gimu, 2,
          "zacznij od sedna, nie od haczyka"],
        ["stos zastrzeżeń (może/często/zazwyczaj)",
          /(?<![\p{L}\p{N}_])(?:może|mogą|często|zazwyczaj|zwykle|prawdopodobnie|ewentualnie|ogólnie)(?![\p{L}\p{N}_])/giu, 0,
          "tyle zastrzeżeń brzmi wymijająco - stwierdź albo wytnij"],
      ],
      artifactPhrases: [
        ["autoreferencja chatbota (model językowy)", "jako model językowy"],
        ["autoreferencja chatbota (SI)", "jako sztuczna inteligencja"],
      ],
      stopwords: new Set([
        "ale", "czy", "dla", "do", "i", "jak", "jest", "na", "nie", "o",
        "od", "po", "przez", "się", "tak", "to", "w", "z", "za", "że",
      ]),
      marks: "łżą",
      emDashFactor: 2.5,
    },
    "cs": {
      name: "Čeština",
      buzzwords: [
        "ponořte se", "ponořme se", "mnohostranný", "mnohostranná",
        "bezproblémový", "bezproblémová", "plynulý zážitek", "komplexní",
        "robustní", "inovativní", "průlomový", "průlomová", "převratný",
        "transformační", "holistický", "holistická", "synergie", "paradigma",
        "změna paradigmatu", "odemkněte svůj potenciál",
        "odemknout potenciál", "ekosystém", "digitální krajina",
        "klíčovou roli", "široká škála", "nekonečné možnosti",
        "neocenitelný", "na další úroveň", "posunout na další úroveň",
        "přelomový moment", "jedinečný", "na špici",
      ],
      phrases: [
        "je důležité poznamenat", "je důležité zmínit", "stojí za zmínku",
        "stojí za povšimnutí", "v dnešním světě",
        "v dnešním uspěchaném světě", "v digitální době", "ponořme se do",
        "pojďme prozkoumat", "doufám, že to pomůže", "neváhejte",
        "skvělá otázka",
        // "jako jazykový model" / "jako umělá inteligence" moved to
        // artifactPhrases below in 0.9.0.
        "když přijde na", "široká škála možností", "otevírá nové možnosti",
        "hraje klíčovou roli", "hraje zásadní roli", "víc než jen",
      ],
      patterns: [
        ["konstrukce 'nejen X, ale i Y'",
          /(?<![\p{L}\p{N}_])nejen(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])ale\s+(?:i|také)(?![\p{L}\p{N}_])/giu, 3,
          "řekni to napřímo, bez rámce kontrastu"],
        ["obrat 'není to X, je to Y'",
          /(?<![\p{L}\p{N}_])není to(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])je to(?![\p{L}\p{N}_])/giu, 2,
          "řekni prostě, co to je"],
        ["řečnická otázka na úvod",
          /^\s*(?:přemýšleli jste někdy|napadlo vás někdy|co kdyby|představte si)(?![\p{L}\p{N}_])/gimu, 2,
          "začni podstatou, ne návnadou"],
        ["hromada výhrad (může/často/obvykle)",
          /(?<![\p{L}\p{N}_])(?:může|mohou|často|obvykle|obecně|pravděpodobně|možná)(?![\p{L}\p{N}_])/giu, 0,
          "tolik výhrad zní vyhýbavě - tvrď, nebo škrtni"],
      ],
      artifactPhrases: [
        ["sebeodkaz chatbota (jazykový model)", "jako jazykový model"],
        ["sebeodkaz chatbota (UI)", "jako umělá inteligence"],
      ],
      stopwords: new Set([
        "a", "avšak", "co", "je", "jen", "kde", "když", "mezi", "na", "nebo",
        "od", "pro", "před", "se", "si", "také", "to", "už", "v", "že",
      ]),
      marks: "řěů",
      emDashFactor: 1.0,
    },
    "tr": {
      name: "Türkçe",
      buzzwords: [
        "dalın", "dalalım", "kapsamlı", "sorunsuz", "bütünsel", "sinerji",
        "paradigma", "paradigma değişimi", "yenilikçi", "devrim niteliğinde",
        "çığır açan", "dönüştürücü", "potansiyelinizi ortaya çıkarın",
        "potansiyelinizi açığa çıkarın", "eşsiz", "vazgeçilmez", "köşe taşı",
        "geniş bir yelpazesi", "bir sonraki seviyeye taşıyın",
        "dijital dönüşüm", "dijital dünya", "güçlü bir araç",
        "kilit rol oynar", "hayati önem taşır", "sınırsız olanaklar", "öncü",
        "çok yönlü", "kesintisiz deneyim", "güçlendirmek",
        "potansiyeli ortaya çıkarmak", "çığır açıcı",
        "eşi benzeri görülmemiş",
      ],
      phrases: [
        "önemle belirtmek gerekir ki", "belirtmek gerekir ki",
        "unutulmamalıdır ki", "günümüzün hızlı dünyasında",
        "günümüz dünyasında", "sonuç olarak", "kısacası", "özetle",
        // "bir yapay zeka olarak" / "bir dil modeli olarak" moved to
        // artifactPhrases below in 0.9.0.
        "harika bir soru",
        "mükemmel bir soru", "çekinmeyin", "yardımcı olması umarım",
        "yardımcı olacağını umuyorum", "hadi dalalım", "gelin inceleyelim",
        "söz konusu olduğunda", "sadece bir araç değil", "günün sonunda",
        "artık geride kaldı",
      ],
      patterns: [
        ["'sadece X değil, aynı zamanda Y' yapısı",
          /(?<![\p{L}\p{N}_])sadece(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])aynı zamanda(?![\p{L}\p{N}_])/giu, 3,
          "çerçevelemeden doğrudan söyle"],
        // The Turkish copula is a suffix (-dır/-dir/-dur/-dür, plus devoiced
        // -tır/-tir/-tur/-tür after voiceless stems), not a separate word, so
        // the flip is matched as "değil" followed by a word carrying that
        // suffix rather than a repeated "is".
        ["'X değil, Y'dır' dönüşü",
          /(?<![\p{L}\p{N}_])değil(?![\p{L}\p{N}_])[^.?!\n]{1,45}?\w+(?:dır|dir|dur|dür|tır|tir|tur|tür)(?![\p{L}\p{N}_])/giu, 2,
          "ne olduğunu doğrudan söyle"],
        ["retorik açılış sorusu",
          /^\s*(?:hiç merak ettiniz mi|hiç düşündünüz mü|hayal edin|bir düşünün)(?![\p{L}\p{N}_])/gimu, 2,
          "kancayla değil, asıl noktayla aç"],
        // "-ebilir/-abilir" (can/may) is also a suffix, not a standalone
        // word, so it's matched the same way; the rest are ordinary hedge
        // adverbs.
        ["çekince yığını (-ebilir/genellikle/belki)",
          /(?<![\p{L}\p{N}_])(?:\w*(?:abilir|ebilir)|muhtemelen|genellikle|genelde|sıklıkla|belki|büyük ihtimalle)(?![\p{L}\p{N}_])/giu, 0,
          "bu kadar çekince kaçamak gibi duruyor - ya net konuş ya da çıkar"],
      ],
      artifactPhrases: [
        ["chatbot öz-referansı (yapay zeka)", "bir yapay zeka olarak"],
        ["chatbot öz-referansı (dil modeli)", "bir dil modeli olarak"],
      ],
      stopwords: new Set([
        "ama", "bir", "bu", "daha", "en", "gibi", "her", "ile", "için",
        "kadar", "mi", "ne", "olan", "sonra", "ve", "veya", "çok", "önce",
        "şey",
      ]),
      marks: "ışğ",
      emDashFactor: 2.5,
    },
    "sv": {
      name: "Svenska",
      buzzwords: [
        "dyk ner i", "dyk djupare", "sömlös", "sömlöst", "holistisk",
        "holistiskt", "synergi", "synergieffekter", "paradigm",
        "paradigmskifte", "banbrytande", "omfattande", "robust",
        "frigör din potential", "frigöra potentialen", "oumbärlig",
        "hörnsten", "innovativ", "revolutionerande", "transformativ",
        "mångfacetterad", "till nästa nivå", "ett brett utbud",
        "en uppsjö av", "digital transformation", "dynamisk",
        "kraftfullt verktyg", "gränslösa möjligheter", "banar väg för",
        "spetskompetens",
      ],
      phrases: [
        "det är viktigt att notera", "det är värt att notera",
        "värt att nämna", "i dagens snabbrörliga värld",
        "i dagens digitala värld", "sammanfattningsvis", "i slutändan",
        // "som en ai" / "som en språkmodell" moved to artifactPhrases
        // below in 0.9.0.
        "tveka inte", "bra fråga",
        "utmärkt fråga", "när det kommer till", "ett brett utbud av",
        "spelar en avgörande roll", "spelar en viktig roll",
        "mer än bara ett verktyg", "jag hoppas att detta hjälper",
        "tveka inte att höra av dig", "öppnar upp nya möjligheter",
      ],
      patterns: [
        ["konstruktionen 'inte bara X utan också Y'",
          /(?<![\p{L}\p{N}_])inte bara(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])utan (?:också|även)(?![\p{L}\p{N}_])/giu, 3,
          "säg det rakt ut, utan kontrastramen"],
        ["vändningen 'är inte X, det är Y'",
          /(?<![\p{L}\p{N}_])är inte(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])det är(?![\p{L}\p{N}_])/giu, 2,
          "säg helt enkelt vad det är"],
        ["retorisk inledningsfråga",
          /^\s*(?:har du någonsin undrat|har du någonsin funderat|tänk om|föreställ dig)(?![\p{L}\p{N}_])/gimu, 2,
          "öppna med poängen, inte med kroken"],
        ["garderingsstapel (kan/ofta/vanligtvis)",
          /(?<![\p{L}\p{N}_])(?:kan|skulle kunna|ofta|vanligtvis|i allmänhet|möjligen|kanske)(?![\p{L}\p{N}_])/giu, 0,
          "så mycket gardering läses undvikande - hävda eller stryk"],
      ],
      artifactPhrases: [
        ["chatbotens självreferens (AI)", "som en ai"],
        ["chatbotens självreferens (språkmodell)", "som en språkmodell"],
      ],
      stopwords: new Set([
        "att", "de", "det", "du", "för", "han", "hon", "inte", "jag", "kan",
        "med", "men", "mycket", "ni", "och", "också", "som", "vara", "vi",
        "är",
      ]),
      marks: "åäö",
      emDashFactor: 1.0,
    },
    "ro": {
      name: "Română",
      buzzwords: [
        "scufundă-te", "scufundă-te în", "cuprinzător", "cuprinzătoare",
        "fără cusur", "impecabil", "holistic", "holistică", "sinergie",
        "paradigmă", "schimbare de paradigmă", "inovator", "inovatoare",
        "revoluționar", "revoluționară", "transformator", "transformatoare",
        "deblochează-ți potențialul", "multifațetat", "o gamă largă de",
        "la următorul nivel", "de neprețuit", "piatră de temelie",
        "remarcabil", "de neegalat", "peisaj digital", "ecosistem",
        "rol esențial", "rol crucial", "instrument puternic",
        "posibilități nelimitate", "de vârf",
      ],
      phrases: [
        "este important de menționat", "merită menționat",
        "trebuie remarcat", "în lumea de azi în ritm alert",
        "în era digitală", "pe scurt", "în concluzie", "la sfârșitul zilei",
        // "ca inteligență artificială" / "ca model lingvistic" moved to
        // artifactPhrases below in 0.9.0.
        "nu ezita să",
        "sper că te ajută", "întrebare excelentă", "întrebare grozavă",
        "atunci când vine vorba de", "joacă un rol esențial",
        "joacă un rol crucial", "nu doar un instrument",
        "o gamă largă de opțiuni", "deschide noi orizonturi",
      ],
      patterns: [
        ["construcția 'nu doar X, ci și Y'",
          /(?<![\p{L}\p{N}_])nu doar(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])(?:ci și|dar și)(?![\p{L}\p{N}_])/giu, 3,
          "spune-o direct, fără cadrul de contrast"],
        ["răsturnarea 'nu este X, este Y'",
          /(?<![\p{L}\p{N}_])nu este(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])este(?![\p{L}\p{N}_])/giu, 2,
          "spune pur și simplu ce este"],
        ["întrebare retorică de deschidere",
          /^\s*(?:te-ai întrebat vreodată|v-ați întrebat vreodată|ce-ar fi dacă|imaginează-ți|imaginați-vă)(?![\p{L}\p{N}_])/gimu, 2,
          "deschide cu ideea, nu cu cârligul"],
        ["stivă de rezerve (poate/adesea/de obicei)",
          /(?<![\p{L}\p{N}_])(?:poate|ar putea|adesea|de obicei|în general|probabil|posibil)(?![\p{L}\p{N}_])/giu, 0,
          "atâtea rezerve sună evaziv - afirmă sau taie"],
      ],
      artifactPhrases: [
        ["auto-referință de chatbot (IA)", "ca inteligență artificială"],
        ["auto-referință de chatbot (model lingvistic)", "ca model lingvistic"],
      ],
      stopwords: new Set([
        "ca", "care", "cu", "dacă", "dar", "de", "din", "este", "foarte",
        "fără", "mai", "nu", "pe", "pentru", "sau", "se", "să", "un", "în",
        "și",
      ]),
      marks: "ăâîșț",
      emDashFactor: 2.5,
    },
    "hu": {
      name: "Magyar",
      buzzwords: [
        "merülj el", "merüljünk el", "zökkenőmentes", "holisztikus",
        "szinergia", "paradigma", "paradigmaváltás", "innovatív",
        "forradalmi", "korszakalkotó", "átalakító", "átfogó", "robusztus",
        "rejlő potenciál", "kulcsszerepet játszik", "széles skálája",
        "a következő szintre", "felbecsülhetetlen", "sarokköve",
        "egyedülálló", "nélkülözhetetlen", "sokrétű",
        "korlátlan lehetőségek", "úttörő", "digitális átalakulás",
        "dinamikus", "hatékony eszköz", "mérföldkő", "új szintre emeli",
      ],
      phrases: [
        "fontos megjegyezni", "érdemes megjegyezni", "fontos kiemelni",
        "napjaink rohanó világában", "a mai digitális világban",
        "összefoglalva", "végezetül",
        // "mesterséges intelligenciaként" / "nyelvi modellként" moved to
        // artifactPhrases below in 0.9.0.
        "ne habozz", "remélem, ez segít",
        "nagyszerű kérdés", "kiváló kérdés", "amikor arról van szó",
        "szabadítsd fel a benned rejlő potenciált", "nem csak egy eszköz",
        "a nap végén", "új távlatokat nyit",
        "kulcsfontosságú szerepet tölt be",
      ],
      // Hungarian doesn't split "not just X but Y" and "isn't X it's Y"
      // into two separate idioms the way Indo-European languages do - both
      // lean on the same "nem X, hanem Y" contrast frame, with "csak"/"is"
      // as an optional intensifier rather than a different construction.
      // Forcing a second, separate flip pattern here would just double-
      // count the same sentence, so this pack ships 3.
      patterns: [
        ["'nem csak X, hanem Y is' szerkezet",
          /(?<![\p{L}\p{N}_])nem csak(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])hanem(?![\p{L}\p{N}_])/giu, 3,
          "mondd ki egyenesen, kontrasztkeret nélkül"],
        ["retorikai nyitókérdés",
          /^\s*(?:gondolkodtál már azon|elgondolkodtál már azon|mi lenne ha|képzeld el|képzeljük el)(?![\p{L}\p{N}_])/gimu, 2,
          "a lényeggel nyiss, ne a csalival"],
        ["óvatoskodás-halom (lehet/gyakran/általában)",
          /(?<![\p{L}\p{N}_])(?:lehet|lehetnek|gyakran|általában|valószínűleg|esetleg)(?![\p{L}\p{N}_])/giu, 0,
          "ennyi óvatoskodás kitérőnek hat - állítsd, vagy húzd ki"],
      ],
      artifactPhrases: [
        ["chatbot önhivatkozás (MI)", "mesterséges intelligenciaként"],
        ["chatbot önhivatkozás (nyelvi modell)", "nyelvi modellként"],
      ],
      stopwords: new Set([
        "a", "az", "azt", "csak", "de", "egy", "ez", "ha", "hogy", "is",
        "kell", "majd", "meg", "mint", "már", "még", "nem", "vagy", "van",
        "és",
      ]),
      marks: "őű",
      emDashFactor: 1.5,
    },
    "fi": {
      name: "Suomi",
      buzzwords: [
        "sukella", "sukella syvemmälle", "kokonaisvaltainen", "saumaton",
        "saumattomasti", "synergia", "paradigma", "paradigman muutos",
        "innovatiivinen", "mullistava", "vallankumouksellinen",
        "muutosvoimainen", "kattava", "vapauta potentiaalisi",
        "piilevä potentiaali", "avainasemassa", "laaja valikoima",
        "seuraavalle tasolle", "korvaamaton", "kulmakivi", "ainutlaatuinen",
        "välttämätön", "monipuolinen", "rajattomat mahdollisuudet",
        "edelläkävijä", "digitaalinen murros", "dynaaminen",
        "tehokas työkalu",
      ],
      phrases: [
        "on tärkeää huomioida", "kannattaa muistaa", "on syytä mainita",
        "nykypäivän nopeatempoisessa maailmassa",
        "tämän päivän digitaalisessa maailmassa", "yhteenvetona",
        "loppujen lopuksi",
        // "tekoälynä" / "kielimallina" moved to artifactPhrases below in
        // 0.9.0.
        "älä epäröi",
        "toivottavasti tästä on apua", "loistava kysymys",
        "erinomainen kysymys", "kun kyse on", "laaja valikoima vaihtoehtoja",
        "ei vain työkalu", "avaa uusia mahdollisuuksia",
        "vie seuraavalle tasolle",
      ],
      patterns: [
        ["'ei ainoastaan X vaan myös Y' -rakenne",
          /(?<![\p{L}\p{N}_])ei ainoastaan(?![\p{L}\p{N}_])[^.?!\n]{1,70}?(?<![\p{L}\p{N}_])vaan myös(?![\p{L}\p{N}_])/giu, 3,
          "sano se suoraan, ilman vastakkainasettelua"],
        ["'ei ole X, vaan Y' -käänne",
          /(?<![\p{L}\p{N}_])ei ole(?![\p{L}\p{N}_])[^.?!\n]{1,45}?(?<![\p{L}\p{N}_])vaan(?![\p{L}\p{N}_])/giu, 2,
          "sano suoraan mitä se on"],
        ["retorinen avauskysymys",
          /^\s*(?:oletko koskaan miettinyt|oletko koskaan pohtinut|entä jos|kuvittele|kuvitellaan)(?![\p{L}\p{N}_])/gimu, 2,
          "avaa asialla, älä koukulla"],
        ["varauksien kasa (voi/usein/yleensä)",
          /(?<![\p{L}\p{N}_])(?:voi|voivat|saattaa|usein|yleensä|tavallisesti|todennäköisesti)(?![\p{L}\p{N}_])/giu, 0,
          "noin moni varaus lukee välttelevältä - väitä tai poista"],
      ],
      artifactPhrases: [
        ["chatbotin itseviittaus (tekoäly)", "tekoälynä"],
        ["chatbotin itseviittaus (kielimalli)", "kielimallina"],
      ],
      stopwords: new Set([
        "ei", "että", "hyvin", "ja", "jo", "joka", "jos", "kanssa", "kuin",
        "kun", "mutta", "myös", "niin", "on", "se", "sekä", "tai", "tämä",
        "vain", "vielä",
      ]),
      marks: "äö",
      emDashFactor: 1.0,
    },
  };

  // Real emoji + the decorative dingbats used as slop. Mirrors the Python
  // EMOJI regex: plain check/cross/arrow glyphs only count when a U+FE0F
  // variation selector forces emoji presentation; a flag (two regional
  // indicators) counts once.
  const _BMP_EMOJI = "✅❌✨⭐⭕❗⚡❤⬆\u{1f004}";
  const EMOJI = new RegExp(
    "[\\u{1f1e6}-\\u{1f1ff}]{2}" +
    "|[\\u{1f300}-\\u{1faff}" + _BMP_EMOJI + "]\\u{fe0f}?" +
    "|[\\u2190-\\u2bff]\\u{fe0f}", "gu");

  const BOLD_BULLET =
    /^\s*(?:(?:[-*+]|\d{1,3}[.)])\s+)?\*\*[^*\n]{1,45}?(?::\*\*|\*\*:|[.!?]\*\*)/gm;

  // Letters in any script, not [A-Za-z] - mirrors the Python tokenizer's
  // [^\W\d_] classes so accented and non-Latin words count as words. Two
  // letters minimum for the word count, same as the tokenizer always was.
  // (Python's class also matches bare combining marks; for the NFC text
  // both sides see in practice, the two are equivalent.)
  const WORD_RE = /\p{L}(?:\p{L}|['\-])+/gu;   // for word count
  const SENT_WORD_RE = /(?:\p{L}|['\-])+/gu;   // for per-sentence length
  const EMDASH_RE = /—/g;
  const DETECT_TOKEN_RE = /\p{L}+/gu;

  // How much text detection reads - mirrors _DETECT_SAMPLE in noslop.py.
  const DETECT_SAMPLE = 4000;

  // ---- helpers ----

  function escapeToken(tok) {
    return tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Reproduces noslop.py find_all(): a word-bounded match that tolerates the
  // line wraps editors insert mid-phrase (single spaces -> \s+). Runs on the
  // lowercased text, so matching is case-insensitive like the CLI.
  //
  // The boundaries are explicit Unicode lookarounds, not \b: JS \b only
  // knows [A-Za-z0-9_], so a needle that starts or ends on an accented
  // letter ("n'hésitez pas à", "não é") would silently never match while
  // Python's Unicode-aware \b matches fine. [\p{L}\p{N}_] mirrors what
  // Python counts as a word character.
  function needleRegex(needle) {
    const parts = needle.split(/\s+/).map(escapeToken);
    return new RegExp(
      "(?<![\\p{L}\\p{N}_])" + parts.join("\\s+") + "(?![\\p{L}\\p{N}_])", "gu");
  }
  const NEEDLE_CACHE = new Map();
  function findAll(lower, needle) {
    let rx = NEEDLE_CACHE.get(needle);
    if (!rx) { rx = needleRegex(needle); NEEDLE_CACHE.set(needle, rx); }
    rx.lastIndex = 0;
    const spans = [];
    let m;
    while ((m = rx.exec(lower)) !== null) {
      spans.push([m.index, m.index + m[0].length]);
      if (m.index === rx.lastIndex) rx.lastIndex++; // guard against zero-width
    }
    return spans;
  }

  function lineOf(text, idx) {
    let n = 1;
    for (let i = 0; i < idx && i < text.length; i++) {
      if (text[i] === "\n") n++;
    }
    return n;
  }

  // Python round(x, nd): round-half-to-even on the exact double, so the
  // per-1k score lands on the CLI's value. Scaling by 10^nd first would
  // destroy the above/below-tie information (0.1499999999999999944 * 10
  // is exactly 1.5), and even 15 extra digits can round the evidence away
  // - so take 60: every double in this code's value range is a dyadic
  // rational whose decimal expansion terminates well inside that, making
  // the tie comparison exact. Half-to-even only on a true tie, by
  // magnitude otherwise.
  function pyRound(x, nd) {
    if (!isFinite(x)) return x;
    const neg = x < 0;
    const digits = Math.abs(x).toFixed(Math.min(100, nd + 60));
    const dot = digits.indexOf(".");
    const keep = digits.slice(0, dot) + digits.slice(dot + 1, dot + 1 + nd);
    const rest = digits.slice(dot + 1 + nd);
    let n = BigInt(keep);
    const half = "5" + "0".repeat(rest.length - 1);
    if (rest > half || (rest === half && n % 2n === 1n)) n += 1n;
    let s = n.toString().padStart(nd + 1, "0");
    const out = Number(s.slice(0, s.length - nd) + "." + s.slice(s.length - nd));
    return neg ? -out : out;
  }

  function countMatches(text, rx) {
    rx.lastIndex = 0;
    let n = 0;
    while (rx.exec(text) !== null) n++;
    return n;
  }

  // First n CODE POINTS of text, matching Python's text[:n] - a plain
  // .slice() counts UTF-16 units and would cut a different sample on
  // emoji-bearing text.
  function samplePrefix(text, n) {
    if (text.length <= n) return text;
    let count = 0, end = 0;
    for (const ch of text) {
      end += ch.length;
      if (++count === n) break;
    }
    return text.slice(0, end);
  }

  // ---- language detection: mirrors detect_language() in noslop.py ----

  function detectLanguage(text) {
    const sample = samplePrefix(text, DETECT_SAMPLE).toLowerCase();
    DETECT_TOKEN_RE.lastIndex = 0;
    const counts = new Map();
    let total = 0;
    let m;
    while ((m = DETECT_TOKEN_RE.exec(sample)) !== null) {
      counts.set(m[0], (counts.get(m[0]) || 0) + 1);
      total++;
      if (m.index === DETECT_TOKEN_RE.lastIndex) DETECT_TOKEN_RE.lastIndex++;
    }
    if (!total) return ["en", "fallback"];
    const scored = [];
    for (const [code, pack] of Object.entries(LANGUAGES)) {
      let hits = 0;
      for (const w of pack.stopwords) hits += counts.get(w) || 0;
      let cov = hits / total;
      for (const ch of pack.marks) {
        if (sample.includes(ch)) cov += 0.02;
      }
      scored.push([cov, hits, code]);
    }
    scored.sort((a, b) => b[0] - a[0]); // stable: insertion order breaks ties
    const [bestCov, bestHits, bestCode] = scored[0];
    const secondCov = scored[1][0];
    if (bestHits >= 4 && bestCov >= 0.07 && bestCov >= secondCov * 1.25) {
      return [bestCode, "detected"];
    }
    return ["en", "fallback"];
  }

  function resolvePack(text, opts) {
    let code, source;
    if (opts.lang && opts.lang !== "auto") {
      code = opts.lang;
      source = opts.langSource || "forced";
    } else {
      [code, source] = detectLanguage(text);
      if (opts.langSource) source = opts.langSource;
    }
    if (!LANGUAGES[code]) throw new Error("unknown language " + code);
    return [code, source, LANGUAGES[code]];
  }

  // ---- core: mirrors analyze() in noslop.py ----

  function analyze(text, opts) {
    opts = opts || {};
    const [code, source, pack] = resolvePack(text, opts);
    const buzzwords = opts.buzzwords || pack.buzzwords;
    const phrases = opts.phrases || pack.phrases;
    // Exotic line terminators and the BOM sit in different \s classes in
    // Python and JavaScript - normalize them away so multiline anchors and
    // sentence splitting agree with the CLI. Mirrors noslop.py analyze().
    text = text.replace(/\r\n?|[\x1c-\x1f\x85\u2028\u2029]/g, "\n").replace(/\ufeff/g, " ");
    // One curly apostrophe (U+2019) normalized to the straight form the
    // phrase lists are written in - same length, spans still line up.
    const lower = text.toLowerCase().replace(/’/g, "'");

    const words = text.match(WORD_RE) || [];
    const wc = Math.max(words.length, 1);
    const per1k = (n) => pyRound((n * 1000.0) / wc, 1);

    // Collect buzzword + phrase spans, keep the longest non-overlapping ones
    // so "let's dive into" is one hit, not "let's dive" plus "dive into".
    const spans = [];
    for (const w of buzzwords) for (const [s, e] of findAll(lower, w)) spans.push([s, e, "buzz", w]);
    for (const p of phrases) for (const [s, e] of findAll(lower, p)) spans.push([s, e, "phrase", p]);
    // Copula-avoidance and scope-inflation share the same overlap-resolution
    // pool as buzzwords/phrases, so a longer existing phrase entry wins over
    // a shorter fragment it contains. Mirrors noslop.py analyze().
    for (const w of (pack.copulaAvoidance || [])) for (const [s, e] of findAll(lower, w)) spans.push([s, e, "copula", w]);
    for (const w of (pack.scopeInflation || [])) for (const [s, e] of findAll(lower, w)) spans.push([s, e, "scope", w]);
    spans.sort((a, b) => (a[0] - b[0]) || (b[1] - a[1]));
    const kept = [];
    let lastEnd = -1;
    for (const [s, e, kind, key] of spans) {
      if (s >= lastEnd) { kept.push([s, e, kind, key]); lastEnd = e; }
    }

    function tally(which) {
      const counts = new Map(); // key -> array of start offsets (insertion order)
      for (const [s, , kind, key] of kept) {
        if (kind !== which) continue;
        if (!counts.has(key)) counts.set(key, []);
        counts.get(key).push(s);
      }
      const rows = [];
      for (const [key, starts] of counts) {
        rows.push([key, starts.length, starts.slice(0, 5).map((s) => lineOf(text, s))]);
      }
      rows.sort((a, b) => b[1] - a[1]); // stable in modern JS engines
      return rows;
    }

    const buzz = tally("buzz");
    const phr = tally("phrase");
    const buzzTotal = buzz.reduce((t, r) => t + r[1], 0);
    const phrTotal = phr.reduce((t, r) => t + r[1], 0);

    // Copula-avoidance only counts past a density gate (2+ hits AND 2+ per
    // 1,000 words - the absolute floor guards short documents the same way
    // noslop.py's does); scope-inflation scores every hit, at a lower
    // weight (applied below).
    const copulaAvoidance = tally("copula");
    const scopeInflation = tally("scope");
    const copulaTotal = copulaAvoidance.reduce((t, r) => t + r[1], 0);
    const scopeTotal = scopeInflation.reduce((t, r) => t + r[1], 0);
    const copulaAvoidanceScored =
      copulaTotal >= 2 && (copulaTotal * 1000.0) / wc >= COPULA_AVOIDANCE_MIN_PER_1K;

    const pat = [];
    let patRaw = 0;
    for (const entry of pack.patterns) {
      const [label, rx, weight, hint] = entry;
      // Optional 5th field: hits that don't score (a device that's normal
      // rhetoric once only counts when it repeats). Mirrors noslop.py.
      const free = entry.length > 4 ? entry[4] : 0;
      rx.lastIndex = 0;
      const lines = [];
      let count = 0;
      let m;
      while ((m = rx.exec(text)) !== null) {
        if (count < 5) lines.push(lineOf(text, m.index));
        count++;
        if (m.index === rx.lastIndex) rx.lastIndex++;
      }
      if (count > 0) {
        pat.push([label, count, weight, hint, lines]);
        patRaw += Math.max(0, count - free) * weight;
      }
    }

    const emdash = countMatches(text, EMDASH_RE);
    const emoji = countMatches(text, EMOJI);

    // Chat-UI residue. Overlapping/adjacent spans merge - mirrors the
    // artifact block in noslop.py analyze(). Markup tokens (AI_ARTIFACTS)
    // are bare substring matches since they can sit inside a URL; chatbot
    // disclaimer sentences (AI_ARTIFACT_PHRASES and the pack's own
    // artifactPhrases) use findAll()'s word-boundary search like any other
    // phrase.
    const artSpans = [];
    for (const [label, needle] of AI_ARTIFACTS) {
      let i = lower.indexOf(needle);
      while (i !== -1) {
        artSpans.push([i, i + needle.length, label]);
        i = lower.indexOf(needle, i + 1);
      }
    }
    for (const [label, needle] of AI_ARTIFACT_PHRASES) {
      for (const [s, e] of findAll(lower, needle)) artSpans.push([s, e, label]);
    }
    for (const [label, needle] of (pack.artifactPhrases || [])) {
      for (const [s, e] of findAll(lower, needle)) artSpans.push([s, e, label]);
    }
    artSpans.sort((a, b) => (a[0] - b[0]) || (a[1] - b[1]));
    const artRows = new Map();
    // Sentinel is -2, not -1: a span at offset 0 must still pass the
    // adjacency test, or an artifact that opens the text vanishes.
    let artEnd = -2;
    for (const [s, e, label] of artSpans) {
      if (s > artEnd + 1) {
        if (!artRows.has(label)) artRows.set(label, []);
        artRows.get(label).push(s);
      }
      artEnd = Math.max(artEnd, e);
    }
    const artifacts = [];
    for (const [label, starts] of artRows) {
      artifacts.push([label, starts.length, starts.slice(0, 5).map((s) => lineOf(text, s))]);
    }
    artifacts.sort((a, b) => b[1] - a[1]); // stable in modern JS engines
    const artTotal = artifacts.reduce((t, r) => t + r[1], 0);

    // Structure-decorating emoji and inline bold spray - mirrors the
    // per-line loop in noslop.py analyze().
    let headerEmoji = 0;
    let boldInline = 0;
    const STRUCT_RE = /^(?:[-*+]|\d{1,3}[.)])\s/;
    const BOLD_SPAN_RE = /\*\*[^*\n]{1,60}\*\*/g;
    const BOLD_LEAD_RE = /^\s*\*\*[^*\n]{1,45}?(?::\*\*|\*\*:|[.!?]\*\*)/;
    for (const rawLine of text.split("\n")) {
      const ls = rawLine.replace(/^\s+/, "");
      if (ls.startsWith("#") || STRUCT_RE.test(ls)) {
        headerEmoji += countMatches(rawLine, EMOJI);
      } else {
        let matches = rawLine.match(BOLD_SPAN_RE) || [];
        if (matches.length && BOLD_LEAD_RE.test(rawLine)) {
          matches = matches.slice(1);
        }
        boldInline += matches.length;
      }
    }

    // Bare bullet glyphs (•/▪/‣) opening a line - mirrors noslop.py.
    const bareBullets = countMatches(text, BARE_BULLET_RE);

    // Generic AI-listicle headings - only score at 2+ hits. Mirrors
    // noslop.py's generic-heading block, including stripping emphasis
    // markers and a trailing colon before matching.
    const HEADING_TEXT_RE = /^#{1,6}[ \t]+(.+?)[ \t]*$/gm;
    let genericHeadingLines = [];
    let hm;
    while ((hm = HEADING_TEXT_RE.exec(text)) !== null) {
      const label = hm[1].replace(/[*_`]+/g, "").trim().replace(/[:.]+$/, "").toLowerCase();
      if (GENERIC_HEADINGS.has(label)) genericHeadingLines.push(lineOf(text, hm.index));
      if (hm.index === HEADING_TEXT_RE.lastIndex) HEADING_TEXT_RE.lastIndex++;
    }
    const genericHeadings = genericHeadingLines.length;
    const genericHeadingExcess = genericHeadings >= 2 ? Math.max(0, genericHeadings - 1) : 0;

    // Heading-level skip (H2 straight to H4, no H3) - reported only.
    const HEADING_LEVEL_RE = /^(#{1,6})[ \t]+\S/gm;
    const headingLevels = [];
    let hl;
    while ((hl = HEADING_LEVEL_RE.exec(text)) !== null) {
      headingLevels.push(hl[1].length);
      if (hl.index === HEADING_LEVEL_RE.lastIndex) HEADING_LEVEL_RE.lastIndex++;
    }
    let headingLevelSkips = 0;
    for (let i = 1; i < headingLevels.length; i++) {
      if (headingLevels[i] > headingLevels[i - 1] + 1) headingLevelSkips++;
    }

    // Curly and straight marks of the SAME kind mixed in one document -
    // a paste boundary. Cross-kind mixing is how humans quote sources.
    const curlyApo = (text.split("’").length - 1) + (text.split("‘").length - 1);
    const straightApo = text.split("'").length - 1;
    const curlyDq = (text.split("“").length - 1) + (text.split("”").length - 1);
    const straightDq = text.split('"').length - 1;
    const quoteMix = ((curlyApo >= 3 && straightApo >= 3) ||
                      (curlyDq >= 3 && straightDq >= 3)) ? 1 : 0;

    // Sentence-punctuation entropy - mirrors noslop.py's punct_entropy().
    const punctEnt = punctEntropy(text);
    const punctEntropyLow = punctEnt !== null && punctEnt < PUNCT_ENTROPY_LOW;

    const sentences = text.trim().split(/(?<=[.!?])\s+/).filter((s) => s.trim());
    const slens = sentences.filter((s) => s.trim()).map((s) => (s.match(SENT_WORD_RE) || []).length);
    let uniformity = null;
    if (slens.length >= 5) {
      const mean = slens.reduce((a, b) => a + b, 0) / slens.length;
      const sd = Math.sqrt(slens.reduce((a, x) => a + (x - mean) ** 2, 0) / slens.length);
      uniformity = pyRound(mean ? sd / mean : 0, 2);
    }

    // Staccato runs: 3+ consecutive very short sentences.
    let staccatoRuns = 0;
    let run = 0;
    for (const n of slens) {
      if (n > 0 && n <= 5) {
        run++;
      } else {
        if (run >= 3) staccatoRuns++;
        run = 0;
      }
    }
    if (run >= 3) staccatoRuns++;

    // Paragraph-length uniformity, same math as the sentence check.
    const paras = text.trim().split(/\n\s*\n/).filter((p) => p.trim());
    const plens = paras.map((p) => (p.match(SENT_WORD_RE) || []).length).filter((n) => n > 0);
    let paragraphUniformity = null;
    if (plens.length >= 5) {
      const pmean = plens.reduce((a, b) => a + b, 0) / plens.length;
      const psd = Math.sqrt(plens.reduce((a, x) => a + (x - pmean) ** 2, 0) / plens.length);
      paragraphUniformity = pyRound(pmean ? psd / pmean : 0, 2);
    }

    // Cross-paragraph opener self-repetition - mirrors noslop.py. Pure
    // string comparison over each paragraph's first five words, so it
    // works identically in every language.
    let paragraphOpenerRepeat = 0;
    let paragraphOpenerRepeatText = null;
    if (paras.length >= 5) {
      const paraOpeners = new Map();
      for (const p of paras) {
        const head = (p.toLowerCase().match(/[\p{L}]+/gu) || []).slice(0, 5);
        if (!head.length) continue;
        const key = head.join(" ");
        paraOpeners.set(key, (paraOpeners.get(key) || 0) + 1);
      }
      let bestOpener = null, bestN = 0;
      for (const [key, n] of paraOpeners) {
        if (n > bestN) { bestOpener = key; bestN = n; }
      }
      if (bestN >= 3) {
        paragraphOpenerRepeat = bestN;
        paragraphOpenerRepeatText = bestOpener;
      }
    }

    // Self-answering question hooks (mid-line only) - mirrors noslop.py.
    const QUESTION_HOOK_RE =
      /(?<=[.!?]) [ \t]*(?:\p{L}[\p{L}\p{N}_'\-]*[ \t]+){0,4}\p{L}[\p{L}\p{N}_'\-]*\?/gu;
    const questionHooks = countMatches(text, QUESTION_HOOK_RE);
    const questionHookExcess = Math.max(0, questionHooks - 1);

    // Sentence-initial connective adverbs, scored on density over an
    // allowance. The word list lives in the pack; packs without one skip.
    let connectiveOpeners = 0;
    const connectives = pack.connectives || [];
    if (connectives.length) {
      const alt = connectives.map(escapeToken).join("|");
      const rx = new RegExp("(?:^|(?<=[.!?])\\s)[ \\t]*(?:" + alt + ")\\b", "gim");
      connectiveOpeners = countMatches(text, rx);
    }
    const connectiveExcess = Math.max(0, connectiveOpeners - Math.max(2, Math.floor(slens.length / 10)));

    // Sentence-opener concentration - reported, not scored. The skip class
    // is non-word chars only ([^\w]* in Python): a sentence opening on a
    // digit records no opener there, so none here either.
    const OPENER_RE = /^[^\p{L}\p{N}_]*(\p{L}[\p{L}\p{N}_'\-]*)/u;
    const openers = [];
    for (const s of sentences) {
      const m = s.match(OPENER_RE);
      if (m) openers.push(m[1].toLowerCase());
    }
    let openerTopShare = null;
    if (openers.length >= 8) {
      // Single pass - a quadratic count here froze the tab on chat logs.
      const freq = new Map();
      let bestN = 0;
      for (const w of openers) {
        const n = (freq.get(w) || 0) + 1;
        freq.set(w, n);
        if (n > bestN) bestN = n;
      }
      openerTopShare = pyRound(bestN / openers.length, 2);
    }

    // Windowed type-token ratio and function-word ratio - report-only
    // diagnostics, never scored (same ESL false-positive risk noted on
    // sentence-uniformity in the README applies here, if not more so).
    // Mirrors noslop.py; the UI never surfaces either as something to fix.
    const wordsLc = words.map((w) => w.toLowerCase());
    let windowedTtr = null;
    if (wordsLc.length >= 200) {
      const ratios = [];
      for (let i = 0; i + 200 <= wordsLc.length; i += 200) {
        ratios.push(new Set(wordsLc.slice(i, i + 200)).size / 200);
      }
      windowedTtr = pyRound(ratios.reduce((a, b) => a + b, 0) / ratios.length, 3);
    }
    const stopwordSet = pack.stopwords || new Set();
    const functionWordRatio = pyRound(
      wordsLc.filter((w) => stopwordSet.has(w)).length / wc, 3);

    let raw = buzzTotal * 3 + phrTotal * 3 + patRaw;
    raw += artTotal * 10;
    // Dialogue-dash languages get a wider allowance (emDashFactor) - an
    // em-dash budget tuned for English prose would flag ordinary Spanish
    // or French dialogue punctuation.
    const emdashExcess = Math.max(0, emdash - Math.floor(Math.max(2, Math.floor(wc / 90)) * pack.emDashFactor));
    raw += emdashExcess;
    raw += emoji * 2;
    raw += headerEmoji * 2;
    const boldBullets = countMatches(text, BOLD_BULLET);
    if (boldBullets >= 3) raw += (boldBullets - 2) * 2;
    const boldInlineExcess = Math.max(0, boldInline - Math.max(2, Math.floor(wc / 150)));
    raw += boldInlineExcess * 2;
    raw += questionHookExcess * 2;
    // Copula-avoidance only counts past its density gate; scope-inflation
    // scores every hit, at the lower weight noted above.
    if (copulaAvoidanceScored) raw += copulaTotal * 3;
    raw += scopeTotal * 2;
    raw += genericHeadingExcess * 2;
    raw += bareBullets * 3;
    let densityCrutchTotal = 0;
    for (const w of (pack.densityCrutch || [])) {
      densityCrutchTotal += findAll(lower, w).length;
    }
    const densityCrutchAllowance = Math.max(2, Math.floor(wc / DENSITY_CRUTCH_ALLOWANCE_DIVISOR));
    const densityCrutchExcess = Math.max(0, densityCrutchTotal - densityCrutchAllowance);
    raw += densityCrutchExcess * 2;

    let score = per1k(raw);
    // Rhythm and typography signals ride on top of the normalized score
    // as small fixed bumps - mirrors the block in noslop.py analyze().
    if (uniformity !== null && uniformity < 0.35) score += 8;
    if (paragraphUniformity !== null && paragraphUniformity < 0.25) score += 4;
    score += Math.min(Math.max(0, staccatoRuns - 1) * 4, 8);
    score += quoteMix * 4;
    score += Math.min(connectiveExcess, 2) * 2;
    if (punctEntropyLow) score += 5;
    if (paragraphOpenerRepeat) score += 5;
    // A chat-UI artifact is proof of paste - it pins the score at the
    // hard-verdict floor no matter how long the text is.
    if (artTotal > 0) score = Math.max(score, 25.0);

    let verdict = "looks human";
    if (score >= 25) verdict = "reads as AI - needs a real rewrite";
    else if (score >= 10) verdict = "some AI tells - worth a pass";

    return {
      mode: "prose",
      words: wc,
      score_per_1k: score,
      verdict: verdict,
      language: code,
      language_source: source,
      buzzwords: buzz,
      phrases: phr,
      patterns: pat,
      ai_artifacts: artifacts,
      em_dashes: emdash,
      em_dash_excess: emdashExcess,
      emoji: emoji,
      header_emoji: headerEmoji,
      bold_label_bullets: boldBullets,
      bold_inline: boldInline,
      bold_inline_excess: boldInlineExcess,
      quote_mix: quoteMix,
      staccato_runs: staccatoRuns,
      question_hooks: questionHooks,
      question_hook_excess: questionHookExcess,
      connective_openers: connectiveOpeners,
      connective_excess: connectiveExcess,
      sentence_uniformity_cv: uniformity,
      paragraph_uniformity_cv: paragraphUniformity,
      opener_top_share: openerTopShare,
      copula_avoidance: copulaAvoidance,
      copula_avoidance_scored: copulaAvoidanceScored,
      scope_inflation: scopeInflation,
      generic_headings: genericHeadings,
      bare_bullets: bareBullets,
      punct_entropy: punctEnt,
      punct_entropy_low: punctEntropyLow,
      heading_level_skips: headingLevelSkips,
      paragraph_opener_repeat: paragraphOpenerRepeat,
      paragraph_opener_repeat_text: paragraphOpenerRepeatText,
      windowed_ttr: windowedTtr,
      function_word_ratio: functionWordRatio,
      density_crutch: densityCrutchTotal,
      density_crutch_excess: densityCrutchExcess,
    };
  }

  // ---- highlight spans for the web UI (char ranges, not in the CLI JSON) ----
  //
  // Returns a flat, non-overlapping, left-to-right list of
  //   { start, end, category, key, hint }
  // ready to paint over the source text. Categories, highest priority first:
  //   phrase > buzzword > construction > hedge > emoji > emdash > bold-bullet
  // A buzzword sitting inside a construction is kept; the construction is
  // trimmed around it so every character belongs to at most one mark.

  const CATEGORY_META = {
    artifact: { label: "chat-UI residue" },
    phrase: { label: "filler phrase" },
    buzzword: { label: "LLM buzzword" },
    construction: { label: "construction" },
    hedge: { label: "hedge (not scored)" },
    copula: { label: "copula-avoidance phrase" },
    scope: { label: "scope-inflation phrase" },
    emoji: { label: "emoji" },
    emdash: { label: "em dash" },
    "bold-bullet": { label: "**Term:** bullet" },
    "bare-bullet": { label: "bare bullet glyph" },
  };
  const PRIORITY = ["artifact", "phrase", "buzzword", "construction", "copula", "scope", "hedge", "emoji", "emdash", "bold-bullet", "bare-bullet"];

  function highlight(text, opts) {
    opts = opts || {};
    const [, , pack] = resolvePack(text, opts);
    const buzzwords = opts.buzzwords || pack.buzzwords;
    const phrases = opts.phrases || pack.phrases;
    // Same normalization as analyze(). Every replacement is one-to-one,
    // so the returned spans still index the caller's original string
    // wherever that string could actually reach this code (textarea
    // values never contain \r).
    text = text.replace(/\r\n?|[\x1c-\x1f\x85\u2028\u2029]/g, "\n").replace(/\ufeff/g, " ");
    const lower = text.toLowerCase().replace(/’/g, "'");
    const raw = [];

    // Chat-UI residue first - merged the same way analyze() merges it, so
    // a pasted citation block paints as one mark. Includes the chatbot
    // disclaimer phrases promoted to this tier in 0.9.0.
    const artSpans = [];
    for (const [label, needle] of AI_ARTIFACTS) {
      let i = lower.indexOf(needle);
      while (i !== -1) {
        artSpans.push([i, i + needle.length, label]);
        i = lower.indexOf(needle, i + 1);
      }
    }
    for (const [label, needle] of AI_ARTIFACT_PHRASES) {
      for (const [s, e] of findAll(lower, needle)) artSpans.push([s, e, label]);
    }
    for (const [label, needle] of (pack.artifactPhrases || [])) {
      for (const [s, e] of findAll(lower, needle)) artSpans.push([s, e, label]);
    }
    artSpans.sort((a, b) => (a[0] - b[0]) || (a[1] - b[1]));
    let artStart = -1;
    let artEnd = -2;
    let artLabel = null;
    const flushArt = () => {
      if (artStart !== -1) raw.push({ start: artStart, end: artEnd, category: "artifact", key: artLabel });
    };
    for (const [s, e, label] of artSpans) {
      if (s > artEnd + 1) {
        flushArt();
        artStart = s;
        artLabel = label;
      }
      artEnd = Math.max(artEnd, e);
    }
    flushArt();

    // buzz + phrase, resolved to the same non-overlapping set analyze() uses
    const spans = [];
    for (const w of buzzwords) for (const [s, e] of findAll(lower, w)) spans.push([s, e, "buzzword", w]);
    for (const p of phrases) for (const [s, e] of findAll(lower, p)) spans.push([s, e, "phrase", p]);
    for (const w of (pack.copulaAvoidance || [])) for (const [s, e] of findAll(lower, w)) spans.push([s, e, "copula", w]);
    for (const w of (pack.scopeInflation || [])) for (const [s, e] of findAll(lower, w)) spans.push([s, e, "scope", w]);
    spans.sort((a, b) => (a[0] - b[0]) || (b[1] - a[1]));
    let lastEnd = -1;
    for (const [s, e, cat, key] of spans) {
      if (s >= lastEnd) { raw.push({ start: s, end: e, category: cat, key: key }); lastEnd = e; }
    }

    for (const [label, rx, weight, hint] of pack.patterns) {
      rx.lastIndex = 0;
      let m;
      while ((m = rx.exec(text)) !== null) {
        const cat = weight === 0 ? "hedge" : "construction";
        raw.push({ start: m.index, end: m.index + m[0].length, category: cat, key: label, hint: hint });
        if (m.index === rx.lastIndex) rx.lastIndex++;
      }
    }
    EMOJI.lastIndex = 0;
    let em;
    while ((em = EMOJI.exec(text)) !== null) {
      raw.push({ start: em.index, end: em.index + em[0].length, category: "emoji", key: em[0] });
      if (em.index === EMOJI.lastIndex) EMOJI.lastIndex++;
    }
    EMDASH_RE.lastIndex = 0;
    let ed;
    while ((ed = EMDASH_RE.exec(text)) !== null) {
      raw.push({ start: ed.index, end: ed.index + 1, category: "emdash", key: "—" });
    }
    BOLD_BULLET.lastIndex = 0;
    let bb;
    while ((bb = BOLD_BULLET.exec(text)) !== null) {
      raw.push({ start: bb.index, end: bb.index + bb[0].length, category: "bold-bullet", key: "**Term:**" });
      if (bb.index === BOLD_BULLET.lastIndex) BOLD_BULLET.lastIndex++;
    }
    BARE_BULLET_RE.lastIndex = 0;
    let bu;
    while ((bu = BARE_BULLET_RE.exec(text)) !== null) {
      raw.push({ start: bu.index, end: bu.index + bu[0].length, category: "bare-bullet", key: bu[0].trim() });
      if (bu.index === BARE_BULLET_RE.lastIndex) BARE_BULLET_RE.lastIndex++;
    }

    // Resolve overlaps by category priority, then flatten to non-overlapping.
    const rank = (c) => PRIORITY.indexOf(c.category);
    raw.sort((a, b) => (a.start - b.start) || (rank(a) - rank(b)) || (b.end - a.end));
    const out = [];
    let cursor = 0;
    for (const span of raw) {
      const start = Math.max(span.start, cursor);
      if (start >= span.end) continue; // fully covered by a higher-priority mark
      out.push({ start: start, end: span.end, category: span.category, key: span.key, hint: span.hint });
      cursor = span.end;
    }
    return out;
  }

  return {
    analyze: analyze,
    highlight: highlight,
    detectLanguage: detectLanguage,
    LANGUAGES: LANGUAGES,
    BUZZWORDS: BUZZWORDS,
    PHRASES: PHRASES,
    PATTERNS: PATTERNS,
    CATEGORY_META: CATEGORY_META,
  };
});
