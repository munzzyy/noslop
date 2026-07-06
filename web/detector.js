/*
 * unslop detector - browser/Node port of the analyze() core in unslop.py.
 *
 * This is a faithful reimplementation of the Python scorer so the web app
 * gives the exact same number the CLI does. web/parity.js checks that against
 * `py unslop.py --json` on every commit; if you touch the word lists or the
 * math here, update unslop.py to match (or the parity job goes red).
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

  // ---- word / phrase / pattern lists (kept in lockstep with unslop.py) ----

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

  const WORD_RE = /[A-Za-z][A-Za-z'\-]+/g;      // for word count
  const SENT_WORD_RE = /[A-Za-z'\-]+/g;          // for per-sentence length
  const EMDASH_RE = /—/g;

  // ---- helpers ----

  function escapeToken(tok) {
    return tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Reproduces unslop.py find_all(): a word-bounded match that tolerates the
  // line wraps editors insert mid-phrase (single spaces -> \s+). Runs on the
  // lowercased text, so matching is case-insensitive like the CLI.
  function needleRegex(needle) {
    const parts = needle.split(/\s+/).map(escapeToken);
    return new RegExp("\\b" + parts.join("\\s+") + "\\b", "g");
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

  // ---- core: mirrors analyze() in unslop.py ----

  function analyze(text, opts) {
    opts = opts || {};
    const buzzwords = opts.buzzwords || BUZZWORDS;
    const phrases = opts.phrases || PHRASES;
    const lower = text.toLowerCase();

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
    for (const [label, rx, weight, hint] of PATTERNS) {
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
    const emdashExcess = Math.max(0, emdash - Math.max(2, Math.floor(wc / 90)));
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
    const buzzwords = opts.buzzwords || BUZZWORDS;
    const phrases = opts.phrases || PHRASES;
    const lower = text.toLowerCase();
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

    for (const [label, rx, weight, hint] of PATTERNS) {
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
    BUZZWORDS: BUZZWORDS,
    PHRASES: PHRASES,
    PATTERNS: PATTERNS,
    CATEGORY_META: CATEGORY_META,
  };
});
