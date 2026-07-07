/*
 * unslop web app — wires the DOM to window.Unslop (detector.js).
 * Classic script on purpose: file:// pages can't use ES module imports
 * (CORS blocks them), so no `import`/`export` here. Everything below reads
 * from the global `Unslop` object detector.js attaches to `window`.
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

  var btnSampleHeavy = document.getElementById("btn-sample-heavy");
  var btnSampleSubtle = document.getElementById("btn-sample-subtle");
  var btnClear = document.getElementById("btn-clear");
  var btnCopy = document.getElementById("btn-copy");

  // ---------- sample texts ----------
  // Maximal-slop sample lands well into the red band; the subtle one sits in
  // the amber "worth a pass" range. Both are original text written for this
  // tool, not lifted from anywhere.

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

  initTheme();

  // ---------- html escaping for the backdrop ----------

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
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
  // is enough.
  function buildBackdropHtml(text, ranges) {
    if (!ranges.length) return escapeHtml(text);
    var out = [];
    var cursor = 0;
    for (var i = 0; i < ranges.length; i++) {
      var r = ranges[i];
      if (r.start > cursor) out.push(escapeHtml(text.slice(cursor, r.start)));
      var cls = CATEGORY_CLASS[r.category] || "m-buzzword";
      var meta = (window.Unslop.CATEGORY_META && window.Unslop.CATEGORY_META[r.category]) || { label: r.category };
      var title = meta.label + (r.hint ? " — " + r.hint : "");
      out.push(
        '<mark class="' + cls + '" tabindex="0" data-label="' + escapeHtml(meta.label) + '"' +
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
    if (hint) tooltip.querySelector(".tt-hint").textContent = "Fix: " + hint;

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

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var scoreRaf = null;
  var displayedScore = 0;

  function animateScoreTo(target) {
    if (scoreRaf) cancelAnimationFrame(scoreRaf);
    if (reduceMotion) {
      displayedScore = target;
      scoreNumberEl.textContent = target.toFixed(1);
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
      scoreNumberEl.textContent = value.toFixed(1);
      if (t < 1) {
        scoreRaf = requestAnimationFrame(tick);
      } else {
        displayedScore = target;
        scoreNumberEl.textContent = target.toFixed(1);
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

  // ---------- breakdown rendering ----------

  function pluralize(n, word) {
    return n + " " + word + (n === 1 ? "" : "s");
  }

  function linesLabel(lines) {
    if (!lines || !lines.length) return "";
    return "line " + lines.join(", ");
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
    countEl.textContent = pluralize(count, "hit");
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
        var term = label + (weight === 0 ? " (style, not scored)" : "");
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
        '<span><strong>Reads clean.</strong>' +
        (result.words < 30
          ? " Not much text to judge yet. Paste a bit more for a confident read."
          : " None of unslop's checks fired on this text.") +
        "</span>";
      breakdownBody.appendChild(clean);
      return;
    }

    if (hasBuzz) breakdownBody.appendChild(buildSection("Buzzwords", "swatch-buzzword", result.buzzwords, "buzz"));
    if (hasPhrase) breakdownBody.appendChild(buildSection("Filler phrases", "swatch-phrase", result.phrases, "phrase"));
    if (hasPattern) breakdownBody.appendChild(buildSection("Constructions", "swatch-construction", result.patterns, "pattern"));

    // Rhythm & surface — always show the section once anything in it is
    // non-zero/flagged, as a set of small stat tiles rather than a list.
    if (hasSurfaceFlag) {
      var section = document.createElement("div");
      section.className = "breakdown-section";
      var title = document.createElement("p");
      title.className = "breakdown-section-title";
      title.innerHTML = '<span class="swatch swatch-emdash" aria-hidden="true"></span>Rhythm &amp; surface';
      section.appendChild(title);

      var grid = document.createElement("div");
      grid.className = "surface-stats";

      function tile(value, label, flagged) {
        var t = document.createElement("div");
        t.className = "stat-tile";
        if (flagged) t.setAttribute("data-flag", "true");
        var v = document.createElement("div");
        v.className = "stat-tile-value";
        v.textContent = value;
        var l = document.createElement("div");
        l.className = "stat-tile-label";
        l.textContent = label;
        t.appendChild(v);
        t.appendChild(l);
        return t;
      }

      if (result.em_dashes > 0) {
        grid.appendChild(tile(
          result.em_dashes,
          result.em_dash_excess > 0 ? "em dashes (" + result.em_dash_excess + " past normal density)" : "em dashes",
          result.em_dash_excess > 0
        ));
      }
      if (result.emoji > 0) {
        grid.appendChild(tile(result.emoji, pluralize(result.emoji, "emoji"), true));
      }
      if (result.bold_label_bullets > 0) {
        grid.appendChild(tile(
          result.bold_label_bullets,
          "**Term:** bullets" + (result.bold_label_bullets >= 3 ? " (template run)" : ""),
          result.bold_label_bullets >= 3
        ));
      }
      if (result.sentence_uniformity_cv !== null) {
        grid.appendChild(tile(
          result.sentence_uniformity_cv.toFixed(2),
          "sentence-length variation" + (result.sentence_uniformity_cv < 0.35 ? " (suspiciously even)" : ""),
          result.sentence_uniformity_cv < 0.35
        ));
      }
      section.appendChild(grid);
      breakdownBody.appendChild(section);
    }
  }

  // ---------- main run loop ----------

  function runAnalysis() {
    var text = textarea.value;
    var result = window.Unslop.analyze(text);
    var ranges = window.Unslop.highlight(text);

    backdrop.innerHTML = buildBackdropHtml(text, ranges);
    syncScroll();

    wordCountEl.textContent = pluralize(result.words, "word");

    var band = verdictBand(result.score_per_1k);
    scoreCard.setAttribute("data-verdict", band);
    verdictTextEl.textContent = result.verdict;
    verdictIconEl.innerHTML = VERDICT_ICONS[band];
    animateScoreTo(result.score_per_1k);

    metaWords.textContent = result.words;
    metaEmdash.textContent = result.em_dashes;
    metaEmoji.textContent = result.emoji;
    metaRhythm.textContent = result.sentence_uniformity_cv === null
      ? "not enough sentences"
      : result.sentence_uniformity_cv.toFixed(2) + (result.sentence_uniformity_cv < 0.35 ? " (even)" : "");

    scoreLiveEl.textContent =
      "Score " + result.score_per_1k.toFixed(1) + " per thousand words. " + result.verdict + ".";

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
  btnClear.addEventListener("click", function () { setText(""); });

  var copyResetTimer = null;
  var btnCopyOriginalHtml = btnCopy.innerHTML; // captured once, before any "Copied" swap
  function flashCopyButton() {
    btnCopy.innerHTML = btnCopyOriginalHtml.replace("Copy text", "Copied");
    if (copyResetTimer) clearTimeout(copyResetTimer);
    copyResetTimer = setTimeout(function () {
      btnCopy.innerHTML = btnCopyOriginalHtml;
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
  // ?sample=heavy|subtle preloads an example and ?theme=<id>|auto forces a
  // theme (any id from THEMES, e.g. ?theme=solarized-dark), so a link can
  // drop someone straight onto the tool already showing what it does.
  // Falls back silently if the URL can't be parsed.
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
  })();

  // ---------- initial paint ----------

  runAnalysis();
})();
