/*
 * unslop detector - browser/Node port of the analyze() core in unslop.py.
 *
 * This is a faithful reimplementation of the Python scorer so the web app
 * gives the exact same number the CLI does. web/parity.js checks that against
 * `py unslop.py --json` on every commit; if you touch the word lists, the
 * language packs, or the math here, update unslop.py to match (or the parity
 * job goes red).
 *
 * Loads two ways with no build step:
 *   - browser:  <script src="detector.js"></script>  ->  window.Unslop
 *   - Node:     const Unslop = require("./detector.js")
 * No imports, no network, no dependencies - same promise as the CLI.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.Unslop = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  // ---- English lists (kept in lockstep with unslop.py) ----

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
  ];

  const PHRASES = [
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
  ];

  // [label, regex (on original-case text), weight, hint]
  const PATTERNS = [
    ["'not just X but Y' construction",
      /\bnot (?:just|only)\b[^.?!\n]{1,70}?\bbut\b/g, 3,
      "state it plainly instead of the contrast frame"],
    ["'it isn't X, it's Y' flip",
      /\bis(?:n't| not)\b[^.?!\n]{1,45}?\bit(?:'s| is)\b/g, 2,
      "just say what it is"],
    ["rhetorical question opener",
      /^\s*(?:ever wondered|have you ever|what if|imagine (?:a|if|that)|picture this)\b/gim, 2,
      "open with the point, not a hook"],
    ["hedge stack (may/can/often/typically)",
      /\b(?:may|might|can|could|often|typically|generally|usually|arguably)\b/g, 0,
      "too many hedges reads evasive - commit or cut"],
  ];

  // ---- language packs (kept in lockstep with LANGUAGES in unslop.py) ----
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
        "gran pregunta", "excelente pregunta", "como modelo de lenguaje",
        "como inteligencia artificial", "desbloquea todo tu potencial",
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
        "en tant que modèle de langage",
        "en tant qu'intelligence artificielle",
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
        "es ist wichtig zu beachten", "es ist wichtig zu betonen",
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
        "como modelo de linguagem", "como inteligência artificial",
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
        "come modello linguistico", "come intelligenza artificiale",
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
        "uitstekende vraag", "als taalmodel", "als ai-model",
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
      stopwords: new Set([
        "de", "het", "een", "en", "van", "is", "dat", "niet", "met",
        "voor", "op", "zijn", "aan", "ook", "maar", "naar", "deze",
        "wordt", "uit", "bij", "dan", "te",
      ]),
      marks: "",
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
    /^\s*(?:[-*+]|\d{1,3}[.)])\s+\*\*[^*\n]{1,45}?(?::\*\*|\*\*:)/gm;

  // Letters in any script, not [A-Za-z] - mirrors the Python tokenizer's
  // [^\W\d_] classes so accented and non-Latin words count as words. Two
  // letters minimum for the word count, same as the tokenizer always was.
  // (Python's class also matches bare combining marks; for the NFC text
  // both sides see in practice, the two are equivalent.)
  const WORD_RE = /\p{L}(?:\p{L}|['\-])+/gu;   // for word count
  const SENT_WORD_RE = /(?:\p{L}|['\-])+/gu;   // for per-sentence length
  const EMDASH_RE = /—/g;
  const DETECT_TOKEN_RE = /\p{L}+/gu;

  // How much text detection reads - mirrors _DETECT_SAMPLE in unslop.py.
  const DETECT_SAMPLE = 4000;

  // ---- helpers ----

  function escapeToken(tok) {
    return tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Reproduces unslop.py find_all(): a word-bounded match that tolerates the
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

  // Python round(x, 1): round-half-to-even on the same IEEE-754 double JS
  // produces, so the per-1k score lands on the CLI's value.
  function pyRound(x, nd) {
    if (!isFinite(x)) return x;
    const m = Math.pow(10, nd);
    const scaled = x * m;
    const floor = Math.floor(scaled);
    const diff = scaled - floor;
    let r;
    if (Math.abs(diff - 0.5) < 1e-9) {
      r = floor % 2 === 0 ? floor : floor + 1;   // banker's rounding
    } else {
      r = Math.round(scaled);
    }
    return r / m;
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

  // ---- language detection: mirrors detect_language() in unslop.py ----

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

  // ---- core: mirrors analyze() in unslop.py ----

  function analyze(text, opts) {
    opts = opts || {};
    const [code, source, pack] = resolvePack(text, opts);
    const buzzwords = opts.buzzwords || pack.buzzwords;
    const phrases = opts.phrases || pack.phrases;
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

    const pat = [];
    for (const [label, rx, weight, hint] of pack.patterns) {
      rx.lastIndex = 0;
      const lines = [];
      let count = 0;
      let m;
      while ((m = rx.exec(text)) !== null) {
        if (count < 5) lines.push(lineOf(text, m.index));
        count++;
        if (m.index === rx.lastIndex) rx.lastIndex++;
      }
      if (count > 0) pat.push([label, count, weight, hint, lines]);
    }

    const emdash = countMatches(text, EMDASH_RE);
    const emoji = countMatches(text, EMOJI);

    const sentences = text.trim().split(/(?<=[.!?])\s+/).filter((s) => s.trim());
    const slens = sentences.filter((s) => s.trim()).map((s) => (s.match(SENT_WORD_RE) || []).length);
    let uniformity = null;
    if (slens.length >= 5) {
      const mean = slens.reduce((a, b) => a + b, 0) / slens.length;
      const sd = Math.sqrt(slens.reduce((a, x) => a + (x - mean) ** 2, 0) / slens.length);
      uniformity = pyRound(mean ? sd / mean : 0, 2);
    }

    let raw = buzzTotal * 3 + phrTotal * 3;
    for (const [, n, weight] of pat) raw += n * weight;
    // Dialogue-dash languages get a wider allowance (emDashFactor) - an
    // em-dash budget tuned for English prose would flag ordinary Spanish
    // or French dialogue punctuation.
    const emdashExcess = Math.max(0, emdash - Math.floor(Math.max(2, Math.floor(wc / 90)) * pack.emDashFactor));
    raw += emdashExcess;
    raw += emoji * 2;
    const boldBullets = countMatches(text, BOLD_BULLET);
    if (boldBullets >= 3) raw += (boldBullets - 2) * 2;

    let score = per1k(raw);
    if (uniformity !== null && uniformity < 0.35) score += 8;

    let verdict = "looks human";
    if (score >= 25) verdict = "reads as AI - needs a real rewrite";
    else if (score >= 10) verdict = "some AI tells - worth a pass";

    return {
      words: wc,
      score_per_1k: score,
      verdict: verdict,
      language: code,
      language_source: source,
      buzzwords: buzz,
      phrases: phr,
      patterns: pat,
      em_dashes: emdash,
      em_dash_excess: emdashExcess,
      emoji: emoji,
      bold_label_bullets: boldBullets,
      sentence_uniformity_cv: uniformity,
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
    phrase: { label: "filler phrase" },
    buzzword: { label: "LLM buzzword" },
    construction: { label: "construction" },
    hedge: { label: "hedge (not scored)" },
    emoji: { label: "emoji" },
    emdash: { label: "em dash" },
    "bold-bullet": { label: "**Term:** bullet" },
  };
  const PRIORITY = ["phrase", "buzzword", "construction", "hedge", "emoji", "emdash", "bold-bullet"];

  function highlight(text, opts) {
    opts = opts || {};
    const [, , pack] = resolvePack(text, opts);
    const buzzwords = opts.buzzwords || pack.buzzwords;
    const phrases = opts.phrases || pack.phrases;
    const lower = text.toLowerCase().replace(/’/g, "'");
    const raw = [];

    // buzz + phrase, resolved to the same non-overlapping set analyze() uses
    const spans = [];
    for (const w of buzzwords) for (const [s, e] of findAll(lower, w)) spans.push([s, e, "buzzword", w]);
    for (const p of phrases) for (const [s, e] of findAll(lower, p)) spans.push([s, e, "phrase", p]);
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
