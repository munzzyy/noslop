// Hebrew (he), RTL. Same key set as en.js - see web/i18n/en.js for the
// rules (do-not-translate list, {placeholder} discipline, plural
// categories). Plural categories used here: one, two, other (verified via
// Intl.PluralRules("he").resolvedOptions().pluralCategories - one=1,
// two=2, other=0/3+/fractional; Hebrew count nouns don't take a separate
// dual noun form the way Arabic does, so "two" and "other" share the same
// plural noun spelling here by design, not by omission).
// dir="rtl" is applied automatically by i18n/registry.js's RTL_LOCALES set.

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs.he = {
  "meta.title": "unslop — גלה מה מסגיר בינה מלאכותית בכתיבה שלך",
  "meta.description": "הדבק את הטקסט שלך ותראה מה גורם לו להישמע כמו רובוט, כדי לתקן לפני שאתה שולח. הכול פועל בתוך הדפדפן שלך — שום דבר לא מועלה לשום מקום.",

  "skipToEditor": "דלג לעורך",
  "theme.switcherLabel": "ערכת נושא",
  "theme.auto": "אוטומטי",
  "uilang.switcherLabel": "שפה",

  "hero.heading": "תראה מה גורם לכתיבה שלך להישמע כמו רובוט.",
  "hero.tagline": "הדבק טיוטה למטה. unslop מצביע בדיוק על המילים וההרגלים שמסגירים את זה, כדי שתוכל לתקן אותם לפני שאתה שולח.",
  "privacy.strong": "הכול פועל בתוך הדפדפן שלך.",
  "privacy.rest": "שום דבר שאתה מדביק לא מועלה, נשמר או נשלח לשום מקום.",

  "toolbar.ariaLabel": "פעולות העורך",
  "toolbar.sampleHeavy": "נסה דוגמה מלאכותית במיוחד",
  "toolbar.sampleSubtle": "נסה דוגמה עדינה",
  "toolbar.sampleSpanish": "נסה דוגמה בספרדית",
  "toolbar.clear": "נקה",
  "toolbar.copy": "העתק טקסט",
  "toolbar.copied": "הועתק",
  "toolbar.wordCount.one": "מילה {count}",
  "toolbar.wordCount.two": "{count} מילים",
  "toolbar.wordCount.other": "{count} מילים",

  "textlang.selectLabel": "בדוק את הטקסט כ",
  "textlang.autoOption": "אוטומטי",
  "textlang.autoDetected": "אוטומטי — זוהתה: {name}",
  "textlang.autoFallback": "אוטומטי — אין התאמה",
  "textlang.fallbackHint": "אף חבילת שפה לא התאימה לטקסט הזה. רק הבדיקות המבניות ורשימות המילים באנגלית פעלו.",

  "editor.textareaLabel": "הכתיבה שלך — הדבק או הקלד כאן כדי לבדוק אם היא נשמעת כמו בינה מלאכותית",
  "editor.placeholder": "הדבק או הקלד את הטקסט שלך כאן...",
  "editor.hintMarks": "הסימונים מראים מה unslop מצא. העבר עכבר או עבור עם Tab לסימון כדי לראות פרטים.",
  "editor.hintTabbing": "לחץ על {tab} כדי להיכנס לטקסט, ואז שוב על {tab} כדי לנוע בין הסימונים.",

  "results.ariaLabel": "תוצאות",
  "score.eyebrow": "ציון בינה מלאכותית",
  "score.unit": "/1000 מילים",
  "score.meta.words": "מילים",
  "score.meta.emdash": "מקפים ארוכים",
  "score.meta.emoji": "אימוג'י",
  "score.meta.rhythm": "קצב המשפטים",
  "score.rhythm.notEnough": "אין מספיק משפטים",
  "score.rhythm.evenSuffix": " (אחיד מדי)",
  "score.liveAnnouncement": "ציון {score} לכל אלף מילים. {verdict}.",

  "verdict.good": "נשמע אנושי",
  "verdict.warn": "יש כמה סימנים של בינה מלאכותית - כדאי לעבור עליו",
  "verdict.bad": "נשמע כמו בינה מלאכותית - צריך שכתוב אמיתי",

  "breakdown.heading": "פירוט",
  "category.phrase": "ביטוי מילוי",
  "category.buzzword": "מילת אופנה",
  "category.construction": "מבנה",
  "category.hedge": "ניסוח מסויג",
  "category.emoji": "אימוג'י",
  "category.emdash": "מקף ארוך",
  "category.bold-bullet": "תבליט מודגש",
  "breakdown.section.buzzword": "מילות אופנה",
  "breakdown.section.phrase": "ביטויי מילוי",
  "breakdown.section.construction": "מבנים",
  "breakdown.rhythmSurface": "קצב ומאפיינים חיצוניים",
  "breakdown.clean.heading": "נקרא נקי.",
  "breakdown.clean.notEnoughText": "עדיין יש מעט מדי טקסט כדי לשפוט. הדבק עוד קצת לתוצאה אמינה.",
  "breakdown.clean.noneFired": "אף אחת מהבדיקות של unslop לא הופעלה בטקסט הזה.",
  "finding.hitCount.one": "פעם {count}",
  "finding.hitCount.two": "{count} פעמים",
  "finding.hitCount.other": "{count} פעמים",
  "finding.linesLabel": "שורה {lines}",
  "finding.styleNotScored": " (סגנון, לא נספר בציון)",
  "finding.fixPrefix": "תיקון: ",

  "surface.emdashLabel": "מקפים ארוכים",
  "surface.emdashExcess": "מקפים ארוכים ({excess} מעבר לרגיל)",
  "surface.emojiCount.one": "אימוג'י {count}",
  "surface.emojiCount.two": "{count} אימוג'י",
  "surface.emojiCount.other": "{count} אימוג'י",
  "surface.boldBullet": "תבליטים **מודגשים**",
  "surface.boldBulletTemplateRun": " (נראה כמו תבנית קבועה)",
  "surface.sentenceVariation": "שונות באורך המשפטים",
  "surface.suspiciouslyEven": " (אחיד באופן חשוד)",

  "explainer.summary": "מה נבדק",
  "explainer.buzzword.term": "מילות אופנה",
  "explainer.buzzword.def": "מילים מסוימות מופיעות בטקסט שנכתב על ידי מכונה בקצב הרבה מעבר לדיבור רגיל. מילה אחת בפני עצמה לא אומרת כלום. צביר שלהן באותה פסקה הוא הסימן המסגיר.",
  "explainer.phrase.term": "ביטויי מילוי",
  "explainer.phrase.def": "פתיחות וסיומים שגרתיים שמודל נשען עליהם: פתיחה שרק מנקה גרון, הצעת עזרה עליזה בסוף, הכרזה עוד לפני שמגיעים בכלל לנושא. הם מנפחים את מספר המילים בלי להוסיף שום דבר.",
  "explainer.construction.term": "מבנים",
  "explainer.construction.def": "צורות משפט, לא מילים בודדות: בניית ניגוד בין שני דברים רק כדי לנחות על השני, חיזוק עובדה על ידי שלילת ההפך שלה קודם, ופתיחה בשאלה רק כווו למשוך תשומת לב במקום לגשת ישר לעניין.",
  "explainer.hedge.term": "ניסוחים מסויגים",
  "explainer.hedge.def": "מילים כמו יכול, לעיתים קרובות ובדרך כלל, ערומות זו על זו באותו קטע טקסט. הן לא נספרות בציון בעצמן, אבל שווה להסתכל עליהן. יותר מדי ניסוחים מסויגים ברצף נשמעים מתחמקים.",
  "explainer.emdash.term": "מקפים ארוכים",
  "explainer.emdash.def": "מקף ארוך מדי פעם הוא סימן פיסוק רגיל. אחד כמעט בכל משפט הוא הרגל ששווה לשבור.",
  "explainer.emoji.term": "אימוג'י בתוך הטקסט",
  "explainer.emoji.def": "מתאים בהודעת צ'אט, אבל לא במקומו בדוח, בקובץ README או במכתב מקדים.",
  "explainer.boldBullet.term": "תבליטים מודגשים",
  "explainer.boldBullet.def": "רצף ארוך של תבליטים שכולם באותה צורה: מילה מודגשת, נקודתיים, ואז הסבר קצר. אחד או שניים זו רשימה רגילה. ארבעה או חמישה ברצף זו תבנית קבועה.",
  "explainer.rhythm.term": "קצב המשפטים",
  "explainer.rhythm.def": "טקסט אמיתי משנה את אורך המשפטים מעצמו, בלי מאמץ. כשכל משפט כמעט באותו אורך בדיוק, האחידות הזו עצמה היא הסימן המסגיר.",

  "footer.license": "חינם לשימוש שאינו מסחרי; שימוש מסחרי דורש רישיון.",
  "footer.sourceLinkText": "קוד המקור ב-GitHub",
  "footer.cliPrefix": "מעדיף את הטרמינל? ",
  "footer.cliSuffix": " משתלב בתוך pre-commit או CI, עם אותו מנוע ניקוד כמו הדף הזה.",
  "footer.licenseLinkText": "רישיון",
};
