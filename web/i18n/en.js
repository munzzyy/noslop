// English (en) - the canonical UI-chrome catalog. Every other locale file
// mirrors this key set (a `.other` fallback always exists so a partial
// catalog never renders blank - see registry.js's t()/tCount()).
//
// ---------------------------------------------------------------------------
// TRANSLATION RULES (binding for every locale file, not just this one):
//
// 1. Do NOT translate - these stay byte-identical everywhere, or aren't in
//    this catalog at all:
//      - The brand name "unslop" (never wrapped in a translatable string).
//      - Theme names in index.html's <option> list (Paper, Ink, Terminal,
//        Sepia, Newsprint, Midnight, Solarized Light, Solarized Dark, High
//        Contrast) - treated like liftmath's theme names (iron, chalk, rust,
//        neon...): evocative palette names, not descriptive UI text, kept
//        English-only in every locale. Only "theme.auto" and
//        "theme.switcherLabel" are real translated strings.
//      - Each text-language pack's own name (Español, Français, Deutsch...) -
//        sourced live from Unslop.LANGUAGES[code].name at runtime, which is
//        already that language's own autonym. Never re-translate a language's
//        name into a third language.
//      - "GitHub" (proper noun, footer link).
//      - The `pipx install ...` command and the "Tab" key name (kept as real
//        DOM elements around a {token} placeholder - see app.js's
//        renderWithToken()).
//
// 2. Placeholders use {named} interpolation. Keep every {placeholder} token
//    byte-identical (same name, same braces) in a translated string - only
//    the surrounding words move.
//
// 3. Pluralized keys (three families: toolbar.wordCount, finding.hitCount,
//    surface.emojiCount) are named `key.<category>` where <category> is
//    whatever Intl.PluralRules(locale).resolvedOptions().pluralCategories
//    actually reports for that locale (verified directly, not guessed - see
//    the node -e check in the commit that added this file). English only
//    needs one/other; ship exactly the categories your locale's grammar
//    needs (Arabic needs all six; Japanese/Vietnamese/Thai/Chinese/Indonesian
//    need only "other" since they don't mark plural at all - give "one" the
//    same text as "other" in that case, that's correct, not a shortcut).
//    registry.js's tCount() always falls back to `.other` if a specific
//    category is missing, so it's safe to under-provide rather than guess.
//
// 4. Numbers are formatted by the runtime via UnslopI18N.formatNumber(),
//    not hardcoded here - a placeholder like {excess} arrives already
//    locale-formatted (grouping/decimal separator), just place it correctly.
//
// 5. House voice: plain and direct, the way a person actually talks about
//    their own writing - never stiff or machine-translated. This is a
//    slop-detector; its own UI reading like AI slop would be the whole
//    joke, so keep every string clean of buzzwords/hedges/"not just X but
//    Y" framing in every language, not just English.
// ---------------------------------------------------------------------------

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs.en = {
  // ---- Meta / SEO ---------------------------------------------------------
  "meta.title": "unslop — flag the AI tells in your writing",
  "meta.description":
    "Paste your writing and see what makes it read like a robot, so you can fix it before you send it. Runs entirely in your browser — nothing is uploaded.",

  // ---- Header / global controls --------------------------------------------
  "skipToEditor": "Skip to editor",
  "theme.switcherLabel": "Theme",
  "theme.auto": "Auto",
  "uilang.switcherLabel": "Language",

  // ---- Hero -----------------------------------------------------------------
  "hero.heading": "See what makes your writing sound like a robot.",
  "hero.tagline": "Paste a draft below. unslop points at the exact words and habits that give it away, so you can fix them before you hit send.",
  "privacy.strong": "Everything runs in your browser.",
  "privacy.rest": "Nothing you paste is uploaded, stored, or sent anywhere.",

  // ---- Toolbar --------------------------------------------------------------
  "toolbar.ariaLabel": "Editor actions",
  "toolbar.sampleHeavy": "Try a heavy-slop sample",
  "toolbar.sampleSubtle": "Try a subtle sample",
  "toolbar.sampleSpanish": "Try a Spanish sample",
  "toolbar.clear": "Clear",
  "toolbar.copy": "Copy text",
  "toolbar.copied": "Copied",
  "toolbar.wordCount.one": "{count} word",
  "toolbar.wordCount.other": "{count} words",

  // ---- Text-language control (forces the pasted TEXT's scoring pack) --------
  "textlang.selectLabel": "Check text as",
  "textlang.autoOption": "Auto",
  "textlang.autoDetected": "Auto — detected: {name}",
  "textlang.autoFallback": "Auto — no pack matched",
  "textlang.fallbackHint": "No language pack matched this text. Only structural checks and the English word lists ran.",

  // ---- Editor -----------------------------------------------------------------
  "editor.textareaLabel": "Your writing — paste or type here to check it for AI tells",
  "editor.placeholder": "Paste or type your writing here...",
  "editor.hintMarks": "Marks show what unslop flagged. Hover or tab to a mark for details.",
  "editor.hintTabbing": "Press {tab} to enter the text, then {tab} again to move between marks.",

  // ---- Score card -------------------------------------------------------------
  "results.ariaLabel": "Results",
  "score.eyebrow": "AI-tell score",
  "score.unit": "/1k words",
  "score.meta.words": "Words",
  "score.meta.emdash": "Em dashes",
  "score.meta.emoji": "Emoji",
  "score.meta.rhythm": "Sentence rhythm",
  "score.rhythm.notEnough": "not enough sentences",
  "score.rhythm.evenSuffix": " (even)",
  "score.liveAnnouncement": "Score {score} per thousand words. {verdict}.",

  // ---- Verdicts (map detector.js's three stable English strings) -----------
  "verdict.good": "looks human",
  "verdict.warn": "some AI tells - worth a pass",
  "verdict.bad": "reads as AI - needs a real rewrite",

  // ---- Breakdown ----------------------------------------------------------
  // "category.*" keys mirror Unslop.CATEGORY_META's own category ids and
  // cover every mark the highlighter can produce (used for tooltip/aria
  // labels on individual marks). "breakdown.section.*" are the section
  // headings above a LIST of findings for that category - a separate,
  // usually-plural phrasing, only needed for the four categories that ever
  // get their own breakdown section (artifact/buzzword/phrase/construction;
  // hedge/emoji/emdash/bold-bullet only ever appear as per-mark labels).
  "breakdown.heading": "Breakdown",
  "category.artifact": "Chat-UI residue",
  "category.phrase": "Filler phrase",
  "category.buzzword": "Buzzword",
  "category.construction": "Construction",
  "category.hedge": "Hedge",
  "category.emoji": "Emoji",
  "category.emdash": "Em dash",
  "category.bold-bullet": "Bold-label bullet",
  "breakdown.section.artifact": "Chat-UI residue (direct paste evidence)",
  "breakdown.section.buzzword": "Buzzwords",
  "breakdown.section.phrase": "Filler phrases",
  "breakdown.section.construction": "Constructions",
  "breakdown.rhythmSurface": "Rhythm & surface",
  "breakdown.clean.heading": "Reads clean.",
  "breakdown.clean.notEnoughText": "Not much text to judge yet. Paste a bit more for a confident read.",
  "breakdown.clean.noneFired": "None of unslop's checks fired on this text.",
  "finding.hitCount.one": "{count} hit",
  "finding.hitCount.other": "{count} hits",
  "finding.linesLabel": "line {lines}",
  "finding.styleNotScored": " (style, not scored)",
  "finding.fixPrefix": "Fix: ",

  // ---- Surface stat tiles --------------------------------------------------
  "surface.emdashLabel": "em dashes",
  "surface.emdashExcess": "em dashes ({excess} past normal density)",
  "surface.emojiCount.one": "{count} emoji",
  "surface.emojiCount.other": "{count} emojis",
  "surface.boldBullet": "**Term:** bullets",
  "surface.boldBulletTemplateRun": " (template run)",
  "surface.sentenceVariation": "sentence-length variation",
  "surface.suspiciouslyEven": " (suspiciously even)",
  // New in 0.7.0 - English-only for now; every other locale falls back to
  // these strings at runtime until its catalog gets a native pass.
  "surface.headerEmoji": "emoji decorating headings/bullets",
  "surface.staccato": "runs of 3+ tiny sentences",
  "surface.quoteMix": "curly + straight quotes mixed",
  "surface.questionHooks": "mid-sentence question hooks",
  "surface.connectives": "sentences opening on a connective",
  "surface.boldInline": "bold spans in running prose",
  "surface.paragraphVariation": "paragraph-length variation (suspiciously even)",
  "surface.openerShare": "sentences opening with the same word (not scored)",
  "explainer.artifact.term": "Chat-UI residue",
  "explainer.artifact.def": "Leftover chatbot markup: citation markers like oaicite, or a link that still carries utm_source=chatgpt.com. Nobody types these by hand, so one is direct paste evidence and scores the hard verdict on its own.",

  // ---- Explainer ("What it checks") ----------------------------------------
  "explainer.summary": "What it checks",
  "explainer.buzzword.term": "Buzzwords",
  "explainer.buzzword.def": "Certain words show up in machine writing at a rate way past normal speech. One on its own means nothing. A cluster of them in one paragraph is the tell.",
  "explainer.phrase.term": "Filler phrases",
  "explainer.phrase.def": "Stock openers and closers a model falls back on: a throat-clearing lead-in, a chipper offer to help at the end, an announcement before diving into the topic. They pad the word count without adding anything.",
  "explainer.construction.term": "Constructions",
  "explainer.construction.def": "Sentence shapes, not single words: setting up a contrast between two things just to land on the second one, restating a fact by first denying its opposite, and opening with a question purely as a hook instead of getting to the point.",
  "explainer.hedge.term": "Hedges",
  "explainer.hedge.def": "Words like can, often, and typically, stacked up in one stretch of text. Not scored on its own, but worth a look. Too many hedges in a row reads evasive.",
  "explainer.emdash.term": "Em dashes",
  "explainer.emdash.def": "An occasional dash is normal punctuation. A pileup of them, one in nearly every sentence, is a habit worth breaking.",
  "explainer.emoji.term": "Emoji in prose",
  "explainer.emoji.def": "Fine in a text message, out of place in a report, a README, or a cover letter.",
  "explainer.boldBullet.term": "Bold-label bullets",
  "explainer.boldBullet.def": "A long run of bullets that all follow the same shape: a bolded word, a colon, then a short explanation. One or two is a normal list. Four or five in a row is a template.",
  "explainer.rhythm.term": "Sentence rhythm",
  "explainer.rhythm.def": "Real writing varies its sentence length without trying to. When every sentence lands within a word or two of the same length, that evenness is its own tell.",

  // ---- Footer ---------------------------------------------------------------
  "footer.license": "Free for noncommercial use; commercial use needs a license.",
  "footer.sourceLinkText": "Source on GitHub",
  "footer.cliPrefix": "Prefer the terminal? ",
  "footer.cliSuffix": " drops into pre-commit or CI, same scoring engine as this page.",
  "footer.licenseLinkText": "License",
};
