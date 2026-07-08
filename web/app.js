/*
 * unslop web app — wires the DOM to window.Unslop (detector.js) and
 * window.UnslopI18N (i18n/registry.js + i18n/<code>.js catalogs).
 * Classic script on purpose: file:// pages can't use ES module imports
 * (CORS blocks them), so no `import`/`export` here. Everything below reads
 * from the global `Unslop` and `UnslopI18N` objects.
 *
 * Two separate language controls live in this file - don't conflate them:
 *   - UI LANGUAGE (#uilang-select): what the app's own chrome reads in.
 *     Persisted (localStorage + URL), driven by UnslopI18N.
 *   - TEXT LANGUAGE (#text-lang-select): what the pasted writing is SCORED
 *     as. Session-only, never persisted - it's a per-text choice. Feeds
 *     {lang: code} into Unslop.analyze()/.highlight().
 *
 * Zero network activity: no fetch, no XHR, no external anything. Every byte
 * this page needs is already loaded from the local web/ folder.
 */
(function () {
  "use strict";

  var THEME_KEY = "unslop:theme";
  var DEBOUNCE_MS = 120;

  // ---------- DOM refs ----------

  var textarea = document.getElementById("editor-textarea");
  var backdrop = document.getElementById("editor-backdrop");
  var wordCountEl = document.getElementById("word-count");
  var scoreCard = document.getElementById("score-card");
  var scoreNumberEl = document.getElementById("score-number");
  var verdictTextEl = document.getElementById("verdict-text");
  var verdictIconEl = document.getElementById("verdict-icon");
  var scoreLiveEl = document.getElementById("score-live");
  var metaWords = document.getElementById("meta-words");
  var metaEmdash = document.getElementById("meta-emdash");
  var metaEmoji = document.getElementById("meta-emoji");
  var metaRhythm = document.getElementById("meta-rhythm");
  var breakdownBody = document.getElementById("breakdown-body");
  var tooltip = document.getElementById("mark-tooltip");
  var themeSelect = document.getElementById("theme-select");
  var themeColorMeta = document.getElementById("theme-color-meta");
  var metaDescriptionEl = document.getElementById("meta-description");
  var editorHintTabbing = document.getElementById("editor-hint-tabbing");

  var btnSampleHeavy = document.getElementById("btn-sample-heavy");
  var btnSampleSubtle = document.getElementById("btn-sample-subtle");
  var btnSampleSpanish = document.getElementById("btn-sample-spanish");
  var btnClear = document.getElementById("btn-clear");
  var btnCopy = document.getElementById("btn-copy");
  var btnCopyLabel = document.getElementById("btn-copy-label");

  var uilangSelect = document.getElementById("uilang-select");
  var textLangSelect = document.getElementById("text-lang-select");
  var textLangAutoOption = document.getElementById("text-lang-auto-option");
  var textLangFallbackHint = document.getElementById("text-lang-fallback-hint");

  // ---------- sample texts ----------
  // Maximal-slop sample lands well into the red band; the subtle one sits in
  // the amber "worth a pass" range. All three are original text written for
  // this tool, not lifted from anywhere. Samples stay in their own language
  // regardless of the UI language picked above - they're demo content, and
  // the Spanish one exists specifically so the multilingual scoring is
  // discoverable without the user needing to paste their own Spanish text.

  var SAMPLE_HEAVY =
    "In today's fast-paced digital landscape, it's important to note that " +
    "businesses must leverage cutting-edge AI to stay competitive 🚀. " +
    "Our comprehensive, robust platform will delve into a rich tapestry of " +
    "possibilities, unlocking a seamless, transformative experience for every " +
    "user ✅. This isn't just a tool — it's a paradigm shift. It isn't a " +
    "product, it's a movement. We don't just build software — we build " +
    "the future — one pivotal release at a time — every single day — " +
    "without exception.\n\n" +
    "Ever wondered what it would feel like to finally unlock your full " +
    "potential? Picture this: a workflow so effortless, so intuitive, that " +
    "you'll wonder how you ever lived without it. Let's dive into the myriad " +
    "ways our holistic, ever-evolving ecosystem empowers you to navigate the " +
    "complexities of modern work. At the end of the day, it's not about " +
    "working harder — it's about working smarter.\n\n" +
    "Here's what sets us apart:\n" +
    "- **Speed:** we move faster than anyone in the space\n" +
    "- **Quality:** every release meets the highest bar\n" +
    "- **Scale:** built to grow with your ambitions\n" +
    "- **Trust:** a partner you can rely on\n" +
    "- **Support:** we're here for you around the clock\n\n" +
    "Whether you're a seasoned professional or just starting out, this " +
    "game-changing solution boasts everything you need to supercharge your " +
    "results. I hope this helps! Feel free to reach out with any questions " +
    "— happy to help ❤️. Gone are the days of settling for less. Look no " +
    "further: the future is here, and it's waiting for you.";

  var SAMPLE_SUBTLE =
    "Quarterly planning wrapped up this week. I wanted to share where things " +
    "landed before the offsite, since a few things moved. The roadmap shifted " +
    "after the customer calls we ran in March. The feedback was consistent " +
    "across almost every call: people want fewer settings, not more. That " +
    "surprised a couple of us on the product side. We had been assuming the " +
    "opposite for two quarters straight.\n\n" +
    "It's worth noting that we're going to reuse the existing infrastructure " +
    "instead of rebuilding it. That alone should save a few weeks. The " +
    "migration still needs real coordination between the two teams, and I " +
    "don't want to understate that part, because the last handoff like this " +
    "took twice as long as planned. Rather than commit to an optimistic date " +
    "and slip twice, I'd rather give engineering the extra week now.\n\n" +
    "A few things worth flagging before Thursday. The design review pushed " +
    "to next Tuesday. The API contract is close to final. We still need a " +
    "decision on the pricing tiers before billing can wrap its half, and " +
    "that's the one piece that's actually on the critical path. It's worth " +
    "getting in front of the exec team early rather than surfacing it the " +
    "week of launch, since last time that conversation ran long.\n\n" +
    "Happy to walk through any of this live if the doc isn't enough context. " +
    "Just grab fifteen minutes.";

  var SAMPLE_SPANISH =
    "En el mundo actual de la tecnología, es importante destacar que las " +
    "pequeñas empresas necesitan una plataforma robusta para no quedarse " +
    "atrás. Nuestra solución integral es tu invitación a hacer más: " +
    "sumérgete en un vasto abanico de posibilidades, con una experiencia " +
    "fluida y sin fisuras pensada para cada equipo. No es solo un programa, " +
    "es un cambio de paradigma que impulsa la innovación en tu negocio.\n\n" +
    "¿Alguna vez te has preguntado cómo sería llevar a tu equipo al " +
    "siguiente nivel sin complicaciones? Profundicemos en las formas en que " +
    "nuestro enfoque holístico empodera a cada persona del equipo para " +
    "navegar la complejidad del trabajo diario.\n\n" +
    "Esto es lo que nos distingue:\n" +
    "- **Velocidad:** entregamos más rápido que la competencia\n" +
    "- **Confianza:** un socio en el que puedes confiar\n" +
    "- **Innovación:** siempre a la vanguardia del sector\n\n" +
    "Ya seas una startup o una empresa consolidada, esta solución " +
    "revolucionaria tiene todo lo que necesitas para crecer. Espero que " +
    "esto te ayude. Siéntete libre de escribirnos si tienes alguna " +
    "pregunta. Atrás quedaron los días de gestionar todo a mano.";

  // ---------- theme ----------
  // "auto" (no data-theme attribute) follows prefers-color-scheme between
  // Paper and Ink, same as before. Every other id names a fixed palette in
  // styles.css; THEMES is the allow-list so a stale/mistyped value (an old
  // bookmark, a hand-edited URL) falls back to auto instead of applying no
  // styling at all.
  var THEMES = [
    "light", "dark", "terminal", "sepia", "newsprint", "midnight",
    "solarized-light", "solarized-dark", "contrast"
  ];

  function applyTheme(mode) {
    var root = document.documentElement;
    if (THEMES.indexOf(mode) !== -1) {
      root.setAttribute("data-theme", mode);
    } else {
      mode = "auto";
      root.removeAttribute("data-theme");
    }
    themeSelect.value = mode;
    // Keep the browser-chrome color (address bar, task switcher) tracking
    // whichever theme just took effect. Reading the custom property back
    // after setting the attribute picks up the auto/media-query case too.
    if (themeColorMeta) {
      var paper = getComputedStyle(root).getPropertyValue("--paper").trim();
      if (paper) themeColorMeta.setAttribute("content", paper);
    }
  }

  function initTheme() {
    var saved = null;
    try {
      saved = localStorage.getItem(THEME_KEY);
    } catch (_e) {
      // localStorage can throw in locked-down contexts; fall back to system.
    }
    applyTheme(saved);
  }

  themeSelect.addEventListener("change", function () {
    var next = themeSelect.value;
    applyTheme(next);
    try {
      if (next === "auto") localStorage.removeItem(THEME_KEY);
      else localStorage.setItem(THEME_KEY, next);
    } catch (_e) {
      /* ignore */
    }
  });

  // Auto mode should keep tracking the OS if it flips light/dark mid-session.
  if (window.matchMedia) {
    var systemSchemeQuery = window.matchMedia("(prefers-color-scheme: dark)");
    var resyncIfAuto = function () {
      if (!document.documentElement.hasAttribute("data-theme")) applyTheme(null);
    };
    if (systemSchemeQuery.addEventListener) systemSchemeQuery.addEventListener("change", resyncIfAuto);
    else if (systemSchemeQuery.addListener) systemSchemeQuery.addListener(resyncIfAuto); // Safari < 14
  }

  // ---------- UI language ----------

  function populateUilangSelect() {
    var locales = window.UnslopI18N.LOCALES;
    for (var i = 0; i < locales.length; i++) {
      var opt = document.createElement("option");
      opt.value = locales[i].code;
      opt.textContent = locales[i].autonym;
      uilangSelect.appendChild(opt);
    }
  }

  function buildTabKbd() {
    var kbd = document.createElement("kbd");
    kbd.textContent = "Tab";
    return kbd;
  }

  // Rebuilds `container` from `template`, splitting on the literal `token`
  // substring (e.g. "{tab}") and inserting a fresh DOM node (never raw HTML)
  // at each split point. Lets a translated sentence place a real <kbd>
  // element wherever its own word order needs it, any number of times,
  // without ever putting HTML markup inside a translation string.
  function renderTokenTemplate(container, template, token, buildNode) {
    container.textContent = "";
    var parts = template.split(token);
    for (var i = 0; i < parts.length; i++) {
      if (parts[i]) container.appendChild(document.createTextNode(parts[i]));
      if (i < parts.length - 1) container.appendChild(buildNode());
    }
  }

  function renderTabbingHint() {
    renderTokenTemplate(editorHintTabbing, window.UnslopI18N.t("editor.hintTabbing"), "{tab}", buildTabKbd);
  }

  // Applies every static (text-independent) translated string to the DOM:
  // document title/meta, [data-i18n] textContent, [data-i18n-aria] labels,
  // [data-i18n-placeholder] placeholders, and the token-rendered tab hint.
  // Called once at load and again every time the UI language changes.
  function applyStaticI18n() {
    var t = window.UnslopI18N.t;
    document.title = t("meta.title");
    if (metaDescriptionEl) metaDescriptionEl.setAttribute("content", t("meta.description"));

    var textNodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < textNodes.length; i++) {
      textNodes[i].textContent = t(textNodes[i].getAttribute("data-i18n"));
    }
    var ariaNodes = document.querySelectorAll("[data-i18n-aria]");
    for (var j = 0; j < ariaNodes.length; j++) {
      ariaNodes[j].setAttribute("aria-label", t(ariaNodes[j].getAttribute("data-i18n-aria")));
    }
    var placeholderNodes = document.querySelectorAll("[data-i18n-placeholder]");
    for (var k = 0; k < placeholderNodes.length; k++) {
      placeholderNodes[k].setAttribute("placeholder", t(placeholderNodes[k].getAttribute("data-i18n-placeholder")));
    }
    renderTabbingHint();
    uilangSelect.value = window.UnslopI18N.getLocale();
  }

  function onUiLanguageChange() {
    applyStaticI18n();
    runAnalysis();
  }

  uilangSelect.addEventListener("change", function () {
    window.UnslopI18N.setLocale(uilangSelect.value, { onChange: onUiLanguageChange });
  });

  // ---------- text language (forces the pasted TEXT's scoring pack) ----------
  // Session-only by design: never written to localStorage or the URL, so a
  // reload always comes back to "auto". This is a per-text choice, not a
  // sticky preference like the UI language above.

  var forcedTextLang = "auto";

  function populateTextLangSelect() {
    var langs = window.Unslop.LANGUAGES;
    var codes = Object.keys(langs);
    for (var i = 0; i < codes.length; i++) {
      var code = codes[i];
      var opt = document.createElement("option");
      opt.value = code;
      opt.textContent = langs[code].name;
      textLangSelect.appendChild(opt);
    }
  }

  textLangSelect.addEventListener("change", function () {
    forcedTextLang = textLangSelect.value;
    runAnalysis();
  });

  // Keeps the "Auto" option's own label live ("Auto — detected: Español"),
  // and shows an honest hint when auto-detect couldn't match any pack.
  // language_source is only ever "fallback" while forcedTextLang is "auto"
  // (a forced pack always resolves with source "forced" - see detector.js's
  // resolvePack()), so no extra guard against a forced pack is needed here.
  function updateTextLangStatus(text, result) {
    var t = window.UnslopI18N.t;
    if (!text.trim()) {
      textLangAutoOption.textContent = t("textlang.autoOption");
      textLangFallbackHint.hidden = true;
      return;
    }
    if (result.language_source === "fallback") {
      textLangAutoOption.textContent = t("textlang.autoFallback");
      textLangFallbackHint.textContent = t("textlang.fallbackHint");
      textLangFallbackHint.hidden = false;
    } else {
      var pack = window.Unslop.LANGUAGES[result.language];
      textLangAutoOption.textContent = t("textlang.autoDetected", { name: pack ? pack.name : result.language });
      textLangFallbackHint.hidden = true;
    }
  }

  // ---------- html escaping for the backdrop ----------

  // Used for both HTML content (text nodes) and attribute values
  // (data-label/data-hint/aria-label in buildBackdropHtml below) - the
  // quote escape only matters for the latter, but escaping it unconditionally
  // costs nothing and means a translated label/hint string is never one
  // stray `"` away from breaking out of an attribute.
  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var CATEGORY_CLASS = {
    phrase: "m-phrase",
    buzzword: "m-buzzword",
    construction: "m-construction",
    hedge: "m-hedge",
    emoji: "m-emoji",
    emdash: "m-emdash",
    "bold-bullet": "m-bold-bullet",
  };

  // Build the backdrop's inner HTML: escaped text with <mark> spans dropped
  // in at the ranges highlight() returned. Ranges are flat and
  // non-overlapping (detector.js guarantees this), so a single linear walk
  // is enough. The category label shown in data-label/aria-label is the UI
  // language's own translation (keyed off Unslop.CATEGORY_META's category
  // ids); the per-mark `hint` text is whatever the matched TEXT-language
  // pack produced it in, and is never re-translated here.
  function buildBackdropHtml(text, ranges) {
    if (!ranges.length) return escapeHtml(text);
    var t = window.UnslopI18N.t;
    var out = [];
    var cursor = 0;
    for (var i = 0; i < ranges.length; i++) {
      var r = ranges[i];
      if (r.start > cursor) out.push(escapeHtml(text.slice(cursor, r.start)));
      var cls = CATEGORY_CLASS[r.category] || "m-buzzword";
      var label = t("category." + r.category);
      var title = label + (r.hint ? " — " + r.hint : "");
      out.push(
        '<mark class="' + cls + '" tabindex="0" data-label="' + escapeHtml(label) + '"' +
        (r.hint ? ' data-hint="' + escapeHtml(r.hint) + '"' : "") +
        ' aria-label="' + escapeHtml(title) + '">' +
        escapeHtml(text.slice(r.start, r.end)) +
        "</mark>"
      );
      cursor = r.end;
    }
    if (cursor < text.length) out.push(escapeHtml(text.slice(cursor)));
    return out.join("");
  }

  // ---------- scroll sync ----------

  function syncScroll() {
    backdrop.scrollTop = textarea.scrollTop;
    backdrop.scrollLeft = textarea.scrollLeft;
  }
  textarea.addEventListener("scroll", syncScroll, { passive: true });

  // ---------- tooltip on hover/focus of a mark ----------

  var activeMark = null;

  function showTooltip(mark) {
    var label = mark.getAttribute("data-label") || "";
    var hint = mark.getAttribute("data-hint");
    tooltip.innerHTML =
      '<span class="tt-label"></span>' + (hint ? '<span class="tt-hint"></span>' : "");
    tooltip.querySelector(".tt-label").textContent = label;
    if (hint) tooltip.querySelector(".tt-hint").textContent = window.UnslopI18N.t("finding.fixPrefix") + hint;

    var rect = mark.getBoundingClientRect();
    var top = rect.top - 10;
    var center = rect.left + rect.width / 2;
    // Tooltip is horizontally centered on the mark via translateX(-50%), so
    // clamp the center point itself (not just the eventual box) to keep it
    // on-screen for marks near the left/right edge on a narrow viewport.
    var halfWidth = tooltip.offsetWidth / 2;
    var minCenter = 8 + halfWidth;
    var maxCenter = window.innerWidth - 8 - halfWidth;
    var left = Math.min(Math.max(center, minCenter), maxCenter);
    tooltip.style.top = Math.max(8, top) + "px";
    tooltip.style.left = left + "px";
    tooltip.style.transform = "translate(-50%, -100%)";
    tooltip.classList.add("visible");
  }

  function hideTooltip() {
    tooltip.classList.remove("visible");
  }

  backdrop.addEventListener("mouseover", function (e) {
    var mark = e.target.closest ? e.target.closest("mark") : null;
    if (mark && mark !== activeMark) {
      activeMark = mark;
      showTooltip(mark);
    }
  });
  backdrop.addEventListener("mouseout", function (e) {
    var mark = e.target.closest ? e.target.closest("mark") : null;
    if (mark) {
      activeMark = null;
      hideTooltip();
    }
  });
  backdrop.addEventListener("focusin", function (e) {
    var mark = e.target.closest ? e.target.closest("mark") : null;
    if (mark) {
      activeMark = mark;
      showTooltip(mark);
    }
  });
  backdrop.addEventListener("focusout", function () {
    activeMark = null;
    hideTooltip();
  });
  window.addEventListener("scroll", hideTooltip, { passive: true, capture: true });

  // ---------- score animation (respects reduced motion) ----------

  var SCORE_FRACTION_OPTS = { minimumFractionDigits: 1, maximumFractionDigits: 1 };
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var scoreRaf = null;
  var displayedScore = 0;

  function animateScoreTo(target) {
    if (scoreRaf) cancelAnimationFrame(scoreRaf);
    if (reduceMotion) {
      displayedScore = target;
      scoreNumberEl.textContent = window.UnslopI18N.formatNumber(target, SCORE_FRACTION_OPTS);
      return;
    }
    var start = displayedScore;
    var startTime = null;
    var DURATION = 380;
    function tick(ts) {
      if (startTime === null) startTime = ts;
      var elapsed = ts - startTime;
      var t = Math.min(1, elapsed / DURATION);
      // ease-out cubic
      var eased = 1 - Math.pow(1 - t, 3);
      var value = start + (target - start) * eased;
      displayedScore = value;
      scoreNumberEl.textContent = window.UnslopI18N.formatNumber(value, SCORE_FRACTION_OPTS);
      if (t < 1) {
        scoreRaf = requestAnimationFrame(tick);
      } else {
        displayedScore = target;
        scoreNumberEl.textContent = window.UnslopI18N.formatNumber(target, SCORE_FRACTION_OPTS);
      }
    }
    scoreRaf = requestAnimationFrame(tick);
  }

  var VERDICT_ICONS = {
    good: '<path d="M4 12.5l5 5L20 6.5"/>',
    warn: '<path d="M12 3.5v9.2M12 17.5h.01" /><path d="M10.6 3.9L2.9 18.3c-.5.9.2 2 1.2 2h15.8c1 0 1.7-1.1 1.2-2L13.4 3.9c-.5-.9-1.8-.9-2.3 0Z"/>',
    bad: '<path d="M18.5 5.5l-13 13M5.5 5.5l13 13"/>',
  };

  function verdictBand(score) {
    if (score >= 25) return "bad";
    if (score >= 10) return "warn";
    return "good";
  }

  // Maps detector.js's three stable English verdict strings (the JSON
  // contract - never localized on the wire) to this catalog's display keys.
  // An unrecognized string (a future detector.js verdict app.js hasn't
  // caught up with yet) falls back to showing the raw English string rather
  // than crashing or going blank.
  var VERDICT_KEY_BY_STRING = {
    "looks human": "verdict.good",
    "some AI tells - worth a pass": "verdict.warn",
    "reads as AI - needs a real rewrite": "verdict.bad",
  };

  function localizedVerdict(rawVerdict) {
    var key = VERDICT_KEY_BY_STRING[rawVerdict];
    return key ? window.UnslopI18N.t(key) : rawVerdict;
  }

  // ---------- breakdown rendering ----------

  function linesLabel(lines) {
    if (!lines || !lines.length) return "";
    return window.UnslopI18N.t("finding.linesLabel", { lines: lines.join(", ") });
  }

  function buildFindingItem(term, count, lines, hint) {
    var li = document.createElement("li");
    li.className = "finding-item";

    var termEl = document.createElement("span");
    termEl.className = "finding-term";
    termEl.textContent = term;
    li.appendChild(termEl);

    var countEl = document.createElement("span");
    countEl.className = "finding-count";
    countEl.textContent = window.UnslopI18N.tCount("finding.hitCount", count);
    li.appendChild(countEl);

    if (lines && lines.length) {
      var linesEl = document.createElement("span");
      linesEl.className = "finding-lines";
      linesEl.textContent = linesLabel(lines);
      li.appendChild(linesEl);
    }

    if (hint) {
      var hintEl = document.createElement("span");
      hintEl.className = "finding-hint";
      hintEl.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.4 10.9c.5.4.9 1 .9 1.6v.3h5v-.3c0-.6.4-1.2.9-1.6A6 6 0 0 0 12 3Z"/></svg>' +
        "<span></span>";
      hintEl.querySelector("span").textContent = hint;
      li.appendChild(hintEl);
    }
    return li;
  }

  function buildSection(titleText, swatchClass, rows, kind) {
    var section = document.createElement("div");
    section.className = "breakdown-section";

    var title = document.createElement("p");
    title.className = "breakdown-section-title";
    var sw = document.createElement("span");
    sw.className = "swatch " + swatchClass;
    sw.setAttribute("aria-hidden", "true");
    title.appendChild(sw);
    title.appendChild(document.createTextNode(titleText));
    section.appendChild(title);

    var list = document.createElement("ul");
    list.className = "finding-list";
    rows.forEach(function (row) {
      if (kind === "pattern") {
        var label = row[0], count = row[1], weight = row[2], hint = row[3], lines = row[4];
        var term = label + (weight === 0 ? window.UnslopI18N.t("finding.styleNotScored") : "");
        list.appendChild(buildFindingItem(term, count, lines, hint));
      } else {
        var key = row[0], cnt = row[1], ln = row[2];
        list.appendChild(buildFindingItem(kind === "phrase" ? '"' + key + '"' : key, cnt, ln, null));
      }
    });
    section.appendChild(list);
    return section;
  }

  function renderBreakdown(result) {
    var t = window.UnslopI18N.t;
    breakdownBody.innerHTML = "";

    var hasBuzz = result.buzzwords.length > 0;
    var hasPhrase = result.phrases.length > 0;
    var hasPattern = result.patterns.length > 0;
    var hasSurfaceFlag =
      result.em_dash_excess > 0 || result.emoji > 0 || result.bold_label_bullets >= 3 ||
      (result.sentence_uniformity_cv !== null && result.sentence_uniformity_cv < 0.35);

    if (!hasBuzz && !hasPhrase && !hasPattern && !hasSurfaceFlag) {
      var clean = document.createElement("div");
      clean.className = "clean-state";
      clean.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12.5l5 5L20 6.5"/></svg>' +
        '<span><strong></strong> <span></span></span>';
      clean.querySelector("strong").textContent = t("breakdown.clean.heading");
      clean.querySelector("span span").textContent = result.words < 30
        ? t("breakdown.clean.notEnoughText")
        : t("breakdown.clean.noneFired");
      breakdownBody.appendChild(clean);
      return;
    }

    if (hasBuzz) breakdownBody.appendChild(buildSection(t("breakdown.section.buzzword"), "swatch-buzzword", result.buzzwords, "buzz"));
    if (hasPhrase) breakdownBody.appendChild(buildSection(t("breakdown.section.phrase"), "swatch-phrase", result.phrases, "phrase"));
    if (hasPattern) breakdownBody.appendChild(buildSection(t("breakdown.section.construction"), "swatch-construction", result.patterns, "pattern"));

    // Rhythm & surface — always show the section once anything in it is
    // non-zero/flagged, as a set of small stat tiles rather than a list.
    if (hasSurfaceFlag) {
      var section = document.createElement("div");
      section.className = "breakdown-section";
      var title = document.createElement("p");
      title.className = "breakdown-section-title";
      var sw = document.createElement("span");
      sw.className = "swatch swatch-emdash";
      sw.setAttribute("aria-hidden", "true");
      title.appendChild(sw);
      title.appendChild(document.createTextNode(t("breakdown.rhythmSurface")));
      section.appendChild(title);

      var grid = document.createElement("div");
      grid.className = "surface-stats";

      function tile(value, label, flagged) {
        var tileEl = document.createElement("div");
        tileEl.className = "stat-tile";
        if (flagged) tileEl.setAttribute("data-flag", "true");
        var v = document.createElement("div");
        v.className = "stat-tile-value";
        v.textContent = value;
        var l = document.createElement("div");
        l.className = "stat-tile-label";
        l.textContent = label;
        tileEl.appendChild(v);
        tileEl.appendChild(l);
        return tileEl;
      }

      if (result.em_dashes > 0) {
        grid.appendChild(tile(
          window.UnslopI18N.formatNumber(result.em_dashes),
          result.em_dash_excess > 0
            ? t("surface.emdashExcess", { excess: window.UnslopI18N.formatNumber(result.em_dash_excess) })
            : t("surface.emdashLabel"),
          result.em_dash_excess > 0
        ));
      }
      if (result.emoji > 0) {
        grid.appendChild(tile(
          window.UnslopI18N.formatNumber(result.emoji),
          window.UnslopI18N.tCount("surface.emojiCount", result.emoji),
          true
        ));
      }
      if (result.bold_label_bullets > 0) {
        grid.appendChild(tile(
          window.UnslopI18N.formatNumber(result.bold_label_bullets),
          t("surface.boldBullet") + (result.bold_label_bullets >= 3 ? t("surface.boldBulletTemplateRun") : ""),
          result.bold_label_bullets >= 3
        ));
      }
      if (result.sentence_uniformity_cv !== null) {
        grid.appendChild(tile(
          window.UnslopI18N.formatNumber(result.sentence_uniformity_cv, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
          t("surface.sentenceVariation") + (result.sentence_uniformity_cv < 0.35 ? t("surface.suspiciouslyEven") : ""),
          result.sentence_uniformity_cv < 0.35
        ));
      }
      section.appendChild(grid);
      breakdownBody.appendChild(section);
    }
  }

  // ---------- main run loop ----------

  function runAnalysis() {
    var t = window.UnslopI18N.t;
    var text = textarea.value;
    var opts = { lang: forcedTextLang };
    var result = window.Unslop.analyze(text, opts);
    var ranges = window.Unslop.highlight(text, opts);

    backdrop.innerHTML = buildBackdropHtml(text, ranges);
    syncScroll();

    updateTextLangStatus(text, result);

    wordCountEl.textContent = window.UnslopI18N.tCount("toolbar.wordCount", result.words);

    var band = verdictBand(result.score_per_1k);
    var verdictDisplay = localizedVerdict(result.verdict);
    scoreCard.setAttribute("data-verdict", band);
    verdictTextEl.textContent = verdictDisplay;
    verdictIconEl.innerHTML = VERDICT_ICONS[band];
    animateScoreTo(result.score_per_1k);

    metaWords.textContent = window.UnslopI18N.formatNumber(result.words);
    metaEmdash.textContent = window.UnslopI18N.formatNumber(result.em_dashes);
    metaEmoji.textContent = window.UnslopI18N.formatNumber(result.emoji);
    metaRhythm.textContent = result.sentence_uniformity_cv === null
      ? t("score.rhythm.notEnough")
      : window.UnslopI18N.formatNumber(result.sentence_uniformity_cv, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) +
        (result.sentence_uniformity_cv < 0.35 ? t("score.rhythm.evenSuffix") : "");

    scoreLiveEl.textContent = t("score.liveAnnouncement", {
      score: window.UnslopI18N.formatNumber(result.score_per_1k, SCORE_FRACTION_OPTS),
      verdict: verdictDisplay,
    });

    renderBreakdown(result);
  }

  var debounceTimer = null;
  function scheduleAnalysis() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runAnalysis, DEBOUNCE_MS);
  }

  textarea.addEventListener("input", scheduleAnalysis);

  // ---------- toolbar actions ----------

  function setText(value) {
    textarea.value = value;
    textarea.focus();
    runAnalysis();
  }

  btnSampleHeavy.addEventListener("click", function () { setText(SAMPLE_HEAVY); });
  btnSampleSubtle.addEventListener("click", function () { setText(SAMPLE_SUBTLE); });
  btnSampleSpanish.addEventListener("click", function () { setText(SAMPLE_SPANISH); });
  btnClear.addEventListener("click", function () { setText(""); });

  var copyResetTimer = null;
  function flashCopyButton() {
    btnCopyLabel.textContent = window.UnslopI18N.t("toolbar.copied");
    if (copyResetTimer) clearTimeout(copyResetTimer);
    copyResetTimer = setTimeout(function () {
      btnCopyLabel.textContent = window.UnslopI18N.t("toolbar.copy");
    }, 1400);
  }

  btnCopy.addEventListener("click", function () {
    var text = textarea.value;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(flashCopyButton, function () {
        fallbackCopy(text);
        flashCopyButton();
      });
    } else {
      fallbackCopy(text);
      flashCopyButton();
    }
  });

  function fallbackCopy(text) {
    var temp = document.createElement("textarea");
    temp.value = text;
    temp.setAttribute("readonly", "");
    temp.style.position = "fixed";
    temp.style.opacity = "0";
    document.body.appendChild(temp);
    temp.select();
    try {
      document.execCommand("copy");
    } catch (_e) {
      /* clipboard unavailable; user can still select-all manually */
    }
    document.body.removeChild(temp);
  }

  // ---------- url-driven demo state (shareable / deep-linkable) ----------
  // ?sample=heavy|subtle|spanish preloads an example and ?theme=<id>|auto
  // forces a theme (any id from THEMES, e.g. ?theme=solarized-dark), so a
  // link can drop someone straight onto the tool already showing what it
  // does. ?uilang=<code> is handled separately, inside
  // UnslopI18N.detectLocale() (see i18n/registry.js) - it's the top-priority
  // source there, so it's already applied by the time this runs. Falls back
  // silently if the URL can't be parsed.
  (function applyUrlState() {
    var params;
    try { params = new URLSearchParams(window.location.search); } catch (_e) { return; }
    var theme = params.get("theme");
    if (theme === "auto" || THEMES.indexOf(theme) !== -1) {
      applyTheme(theme);
      try {
        if (theme === "auto") localStorage.removeItem(THEME_KEY);
        else localStorage.setItem(THEME_KEY, theme);
      } catch (_e2) { /* ignore */ }
    }
    var sample = params.get("sample");
    if (sample === "heavy") textarea.value = SAMPLE_HEAVY;
    else if (sample === "subtle") textarea.value = SAMPLE_SUBTLE;
    else if (sample === "spanish") textarea.value = SAMPLE_SPANISH;
  })();

  // ---------- initial paint ----------

  populateUilangSelect();
  window.UnslopI18N.initLocale();
  applyStaticI18n();
  initTheme();
  populateTextLangSelect();
  runAnalysis();
})();
