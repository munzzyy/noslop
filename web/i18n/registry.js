/*
 * unslop UI-language registry + runtime.
 *
 * Classic script on purpose (no `export`/`import`) - file:// pages can't load
 * ES modules (CORS blocks them), the same constraint app.js documents at its
 * own top. Every web/i18n/<code>.js catalog is ALSO a classic script; each
 * one attaches its dictionary to window.UnslopI18N.catalogs[code]. Load every
 * catalog, then this file, then app.js.
 *
 * This is the UI-CHROME language (what the app's own labels/buttons read in),
 * completely separate from the TEXT language control in app.js (what the
 * pasted writing is scored as). Don't conflate the two - see app.js.
 *
 * API surface (mirrors liftmath's web/js/i18n/index.js, adapted for a global
 * namespace instead of ES module exports):
 *   UnslopI18N.LOCALES            - ordered [{code, autonym}] for the picker
 *   UnslopI18N.DEFAULT_LOCALE      - "en"
 *   UnslopI18N.isSupported(code)
 *   UnslopI18N.isRtl(code)
 *   UnslopI18N.detectLocale()      - URL ?uilang= > localStorage > navigator
 *   UnslopI18N.getLocale()
 *   UnslopI18N.setLocale(code, {onChange, persist=true})
 *   UnslopI18N.initLocale({onChange}) - first-load detect, does not persist
 *   UnslopI18N.t(key, params)          - {placeholder} interpolation, falls
 *                                        back to English then the raw key
 *   UnslopI18N.tCount(key, count, params) - key + "." + Intl.PluralRules
 *                                        category, falls back to ".other"
 *   UnslopI18N.formatNumber(n, options)   - Intl.NumberFormat, Western
 *                                        digits always (see note below)
 */
(function (root) {
  "use strict";

  var ns = root.UnslopI18N || (root.UnslopI18N = {});
  ns.catalogs = ns.catalogs || {};

  // Ordered Western/Northern Europe, Central/Eastern Europe, Southeast Asia,
  // East/South Asia, then RTL - same grouping convention as liftmath's own
  // language picker, for a dropdown order that isn't alphabetical soup.
  var LOCALES = [
    { code: "en", autonym: "English" },
    { code: "es", autonym: "Español" },
    { code: "pt-BR", autonym: "Português (Brasil)" },
    { code: "fr", autonym: "Français" },
    { code: "it", autonym: "Italiano" },
    { code: "de", autonym: "Deutsch" },
    { code: "nl", autonym: "Nederlands" },
    { code: "sv", autonym: "Svenska" },
    { code: "nb", autonym: "Norsk bokmål" },
    { code: "da", autonym: "Dansk" },
    { code: "fi", autonym: "Suomi" },
    { code: "pl", autonym: "Polski" },
    { code: "cs", autonym: "Čeština" },
    { code: "hu", autonym: "Magyar" },
    { code: "ro", autonym: "Română" },
    { code: "uk", autonym: "Українська" },
    { code: "ru", autonym: "Русский" },
    { code: "el", autonym: "Ελληνικά" },
    { code: "tr", autonym: "Türkçe" },
    { code: "id", autonym: "Bahasa Indonesia" },
    { code: "vi", autonym: "Tiếng Việt" },
    { code: "tl", autonym: "Filipino" },
    { code: "zh-Hans", autonym: "简体中文" },
    { code: "zh-Hant", autonym: "繁體中文" },
    { code: "ja", autonym: "日本語" },
    { code: "ko", autonym: "한국어" },
    { code: "hi", autonym: "हिन्दी" },
    { code: "bn", autonym: "বাংলা" },
    { code: "th", autonym: "ไทย" },
    { code: "ar", autonym: "العربية" },
    { code: "he", autonym: "עברית" },
    { code: "fa", autonym: "فارسی" },
  ];
  var RTL_LOCALES = { ar: true, he: true, fa: true };
  var DEFAULT_LOCALE = "en";
  var STORAGE_KEY = "unslop:uilang";
  var URL_PARAM = "uilang";

  ns.LOCALES = LOCALES;
  ns.DEFAULT_LOCALE = DEFAULT_LOCALE;

  var CODES = [];
  for (var i = 0; i < LOCALES.length; i++) CODES.push(LOCALES[i].code);

  function isSupported(code) {
    return CODES.indexOf(code) !== -1;
  }
  ns.isSupported = isSupported;

  function isRtl(code) {
    return !!RTL_LOCALES[code];
  }
  ns.isRtl = isRtl;

  /** "zh-Hans-CN" -> "zh-Hans", "de-AT" -> "de", "fr-FR" -> null (unshipped). */
  function matchLocale(tag) {
    if (!tag) return null;
    var norm = String(tag).trim();
    if (isSupported(norm)) return norm;
    var parts = norm.split("-");
    while (parts.length > 1) {
      parts.pop();
      var candidate = parts.join("-");
      if (isSupported(candidate)) return candidate;
    }
    var lower = norm.toLowerCase();
    for (var i2 = 0; i2 < CODES.length; i2++) {
      var supported = CODES[i2];
      var supportedLower = supported.toLowerCase();
      if (supportedLower === lower || supportedLower.split("-")[0] === lower.split("-")[0]) {
        return supported;
      }
    }
    return null;
  }

  /** Priority order: URL ?uilang= > localStorage > navigator.language(s) > en. */
  function detectLocale(searchParams) {
    try {
      var params = searchParams || new URLSearchParams(location.search);
      var fromUrl = matchLocale(params.get(URL_PARAM));
      if (fromUrl) return fromUrl;
    } catch (_e) {
      // no `location` (non-browser context) - fall through
    }
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      var fromStorage = matchLocale(stored);
      if (fromStorage) return fromStorage;
    } catch (_e2) {
      // localStorage unavailable - fall through
    }
    try {
      var navLangs = (typeof navigator !== "undefined" && navigator.languages) || [];
      for (var i3 = 0; i3 < navLangs.length; i3++) {
        var match = matchLocale(navLangs[i3]);
        if (match) return match;
      }
      var single = typeof navigator !== "undefined" ? navigator.language : null;
      var fromNav = matchLocale(single);
      if (fromNav) return fromNav;
    } catch (_e3) {
      // no `navigator` - fall through
    }
    return DEFAULT_LOCALE;
  }
  ns.detectLocale = detectLocale;

  var currentLocale = DEFAULT_LOCALE;
  var currentDict = null;

  function interpolate(template, params) {
    if (!params) return template;
    return template.replace(/\{(\w+)\}/g, function (match, name) {
      return Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match;
    });
  }

  /** Dot-namespaced key lookup, {placeholder} interpolated, English fallback. */
  function t(key, params) {
    var enDict = ns.catalogs[DEFAULT_LOCALE];
    var dict = currentDict || enDict;
    var template = dict ? dict[key] : undefined;
    if (template === undefined && enDict) template = enDict[key];
    if (template === undefined) return key;
    return interpolate(template, params);
  }
  ns.t = t;

  var pluralRulesCache = {};
  function pluralRulesFor(locale) {
    if (!pluralRulesCache[locale]) {
      try {
        pluralRulesCache[locale] = new Intl.PluralRules(locale);
      } catch (_e) {
        pluralRulesCache[locale] = new Intl.PluralRules(DEFAULT_LOCALE);
      }
    }
    return pluralRulesCache[locale];
  }

  /**
   * Count-aware lookup: resolves `key + "." + category` where category comes
   * from Intl.PluralRules.select(count) for the active locale (e.g. "one",
   * "few", "many", "other" - whichever categories that locale's grammar
   * actually needs, per real CLDR data, not a guessed one/other split).
   * Falls back to `key + ".other"` if the active locale's catalog doesn't
   * carry that specific category, so a partial catalog never renders blank.
   * `{count}` is always available for interpolation alongside any `params`.
   */
  function tCount(key, count, params) {
    var category = pluralRulesFor(currentLocale).select(count);
    var enDict = ns.catalogs[DEFAULT_LOCALE];
    var dict = currentDict || enDict;
    var full = key + "." + category;
    var other = key + ".other";
    var template = dict ? dict[full] : undefined;
    if (template === undefined && dict) template = dict[other];
    if (template === undefined && enDict) template = enDict[full] || enDict[other];
    if (template === undefined) return key;
    var merged = {};
    if (params) {
      for (var k in params) if (Object.prototype.hasOwnProperty.call(params, k)) merged[k] = params[k];
    }
    // formatNumber() is declared further down (still hoisted - both are
    // plain function declarations in this same IIFE scope), pinned to
    // Western digits so a formatted count never breaks tabular-nums.
    merged.count = formatNumber(count);
    return interpolate(template, merged);
  }
  ns.tCount = tCount;

  var numberFormatterCache = {};
  /**
   * Locale-aware number formatting (grouping + decimal separator) via
   * Intl.NumberFormat. Numbering system is pinned to "latn" (Western digits)
   * in every locale on purpose: this app's numeric displays (score, word
   * count, stat tiles) rely on `font-variant-numeric: tabular-nums`, which is
   * a Latin-digit OpenType feature - swapping in Arabic-Indic/Persian/
   * Bengali digit glyphs would silently break that alignment, so grouping/
   * decimal conventions localize but the glyphs themselves stay consistent.
   */
  function formatNumber(n, options) {
    if (n === null || n === undefined || Number.isNaN(n)) return String(n);
    var cacheKey = currentLocale + "|" + JSON.stringify(options || {});
    var fmt = numberFormatterCache[cacheKey];
    if (!fmt) {
      var opts = { numberingSystem: "latn" };
      if (options) for (var k in options) if (Object.prototype.hasOwnProperty.call(options, k)) opts[k] = options[k];
      try {
        fmt = new Intl.NumberFormat(currentLocale, opts);
      } catch (_e) {
        fmt = new Intl.NumberFormat(DEFAULT_LOCALE, opts);
      }
      numberFormatterCache[cacheKey] = fmt;
    }
    return fmt.format(n);
  }
  ns.formatNumber = formatNumber;

  function applyHtmlAttrs(code) {
    if (typeof document === "undefined") return;
    document.documentElement.setAttribute("lang", code);
    document.documentElement.setAttribute("dir", isRtl(code) ? "rtl" : "ltr");
  }

  function persistLocale(code) {
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch (_e) {
      // best-effort only - locale choice just won't survive a reload
    }
  }

  function persistLocaleToUrl(code) {
    try {
      var params = new URLSearchParams(location.search);
      params.set(URL_PARAM, code);
      var next = location.pathname + "?" + params.toString() + location.hash;
      history.replaceState(history.state, "", next);
    } catch (_e) {
      // non-browser context - nothing to sync
    }
  }

  /**
   * Switch the active UI locale. Falls back to DEFAULT_LOCALE for an
   * unsupported/garbage code rather than throwing.
   * @param {object} [opts]
   * @param {() => void} [opts.onChange] - called once the swap completes.
   * @param {boolean} [opts.persist=true] - false skips localStorage/URL
   *   writes (used for the very first detect-and-apply on page load).
   */
  function setLocale(code, opts) {
    opts = opts || {};
    var resolved = isSupported(code) ? code : DEFAULT_LOCALE;
    currentDict = ns.catalogs[resolved] || ns.catalogs[DEFAULT_LOCALE];
    currentLocale = resolved;
    applyHtmlAttrs(resolved);
    if (opts.persist !== false) {
      persistLocale(resolved);
      persistLocaleToUrl(resolved);
    }
    if (opts.onChange) opts.onChange();
    return resolved;
  }
  ns.setLocale = setLocale;

  function getLocale() {
    return currentLocale;
  }
  ns.getLocale = getLocale;

  /** First-load detect + apply; doesn't rewrite localStorage/URL with a value it just read from one of those same sources. */
  function initLocale(opts) {
    opts = opts || {};
    var code = detectLocale();
    return setLocale(code, { onChange: opts.onChange, persist: false });
  }
  ns.initLocale = initLocale;
})(typeof globalThis !== "undefined" ? globalThis : this);
