// Traditional Chinese (zh-Hant). Same key set as en.js - see web/i18n/en.js
// for the rules (do-not-translate list, {placeholder} discipline, plural
// categories). Plural categories used here: one, other, both given the
// same text - Chinese doesn't mark grammatical number at all (verified via
// Intl.PluralRules("zh-Hant").resolvedOptions().pluralCategories -> only
// "other" is ever reported; "one" is kept identical for robustness).

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs["zh-Hant"] = {
  "meta.title": "unslop — 找出文字裡洩露 AI 痕跡的地方",
  "meta.description": "貼上你的文字,看看是什麼讓它聽起來像機器人寫的,傳送前先改一改。全部在瀏覽器裡執行——什麼都不會上傳。",

  "skipToEditor": "跳到編輯區",
  "theme.switcherLabel": "主題",
  "theme.auto": "自動",
  "uilang.switcherLabel": "語言",

  "hero.heading": "看看是什麼讓你的文字聽起來像機器人。",
  "hero.tagline": "把草稿貼到下面。unslop 會準確指出洩露痕跡的那些字詞和習慣,方便你在傳送前改掉。",
  "privacy.strong": "一切都在你的瀏覽器裡執行。",
  "privacy.rest": "你貼上的任何內容都不會被上傳、儲存或傳送到任何地方。",

  "toolbar.ariaLabel": "編輯操作",
  "toolbar.sampleHeavy": "試試一個很機器味的範例",
  "toolbar.sampleSubtle": "試試一個不太明顯的範例",
  "toolbar.sampleSpanish": "試試一個西班牙文範例",
  "toolbar.clear": "清空",
  "toolbar.copy": "複製文字",
  "toolbar.copied": "已複製",
  "toolbar.wordCount.one": "{count} 個字",
  "toolbar.wordCount.other": "{count} 個字",

  "textlang.selectLabel": "以此語言檢查文字",
  "textlang.autoOption": "自動",
  "textlang.autoDetected": "自動 — 偵測到:{name}",
  "textlang.autoFallback": "自動 — 沒有匹配",
  "textlang.fallbackHint": "沒有語言包與這段文字匹配,只執行了結構檢查和英文詞表。",

  "editor.textareaLabel": "你的文字 — 貼上或輸入到這裡,檢查是否聽起來像 AI",
  "editor.placeholder": "在這裡貼上或輸入你的文字...",
  "editor.hintMarks": "標記顯示 unslop 發現的問題。將滑鼠移到標記上或用 Tab 鍵切換過去查看詳情。",
  "editor.hintTabbing": "按 {tab} 進入文字區,再按一次 {tab} 可以在各個標記之間移動。",

  "results.ariaLabel": "結果",
  "score.eyebrow": "AI 痕跡分數",
  "score.unit": "/千字",
  "score.meta.words": "字數",
  "score.meta.emdash": "破折號",
  "score.meta.emoji": "表情符號",
  "score.meta.rhythm": "句子節奏",
  "score.rhythm.notEnough": "句子太少",
  "score.rhythm.evenSuffix": "(過於平均)",
  "score.liveAnnouncement": "每千字得分 {score}。{verdict}。",

  "verdict.good": "讀起來像真人寫的",
  "verdict.warn": "有一些 AI 痕跡 - 值得再看一遍",
  "verdict.bad": "讀起來像 AI 寫的 - 需要認真重寫",

  "breakdown.heading": "詳細分析",
  "category.phrase": "套話",
  "category.buzzword": "流行詞",
  "category.construction": "句式套路",
  "category.hedge": "模糊限定詞",
  "category.emoji": "表情符號",
  "category.emdash": "破折號",
  "category.bold-bullet": "加粗要點",
  "breakdown.section.buzzword": "流行詞",
  "breakdown.section.phrase": "套話",
  "breakdown.section.construction": "句式套路",
  "breakdown.rhythmSurface": "節奏與表面特徵",
  "breakdown.clean.heading": "讀起來很乾淨。",
  "breakdown.clean.notEnoughText": "文字還太少,不足以判斷。多貼一些以取得可靠的結果。",
  "breakdown.clean.noneFired": "這段文字沒有觸發 unslop 的任何檢查項目。",
  "finding.hitCount.one": "{count} 次",
  "finding.hitCount.other": "{count} 次",
  "finding.linesLabel": "第 {lines} 行",
  "finding.styleNotScored": "(屬於風格,不計分)",
  "finding.fixPrefix": "修改建議:",

  "surface.emdashLabel": "破折號",
  "surface.emdashExcess": "破折號(比正常水準多出 {excess} 個)",
  "surface.emojiCount.one": "{count} 個表情符號",
  "surface.emojiCount.other": "{count} 個表情符號",
  "surface.boldBullet": "**加粗**要點",
  "surface.boldBulletTemplateRun": "(像是套模板)",
  "surface.sentenceVariation": "句長變化程度",
  "surface.suspiciouslyEven": "(平均得可疑)",

  "explainer.summary": "會檢查哪些內容",
  "explainer.buzzword.term": "流行詞",
  "explainer.buzzword.def": "某些詞在機器寫的文字裡出現的頻率遠高於日常說話。單獨出現一次說明不了什麼,但如果同一段裡扎堆出現,那就是破綻。",
  "explainer.phrase.term": "套話",
  "explainer.phrase.def": "模型愛用的那些老套開頭和結尾:只是清清嗓子的引言,結尾時熱情地表示願意幫忙,還沒進入主題就先做個預告。這些話只是湊字數,沒有實際內容。",
  "explainer.construction.term": "句式套路",
  "explainer.construction.def": "指的是句子結構,不是單一詞語:先製造兩件事之間的對比,只為了落在第二件事上;先否定反面,再重申一次事實;開頭拋出一個問題只是為了吸引注意,而不是直接說重點。",
  "explainer.hedge.term": "模糊限定詞",
  "explainer.hedge.def": "像可能、經常、通常這類詞,如果在一段文字裡堆得很密集。單獨出現不計分,但值得留意。連續出現太多模糊限定詞,讀起來會很含糊其辭。",
  "explainer.emdash.term": "破折號",
  "explainer.emdash.def": "偶爾用一個破折號是正常的標點用法。但如果幾乎每句話都有一個,那就是該改掉的習慣了。",
  "explainer.emoji.term": "內文裡的表情符號",
  "explainer.emoji.def": "傳訊息聊天時沒問題,但出現在報告、README 或求職信裡就顯得不合適。",
  "explainer.boldBullet.term": "加粗要點",
  "explainer.boldBullet.def": "一長串要點都是同一種格式:一個加粗的詞,一個冒號,然後是簡短說明。一兩條是正常的清單,連續四五條就是套模板了。",
  "explainer.rhythm.term": "句子節奏",
  "explainer.rhythm.def": "真實的文字會自然地變化句子長短,不是刻意為之。如果每句話的長度都幾乎一樣,這種整齊本身就是破綻。",

  "footer.license": "非商業用途免費;商業用途需要授權。",
  "footer.sourceLinkText": "在 GitHub 上查看原始碼",
  "footer.cliPrefix": "比較喜歡用終端機? ",
  "footer.cliSuffix": " 可以接入 pre-commit 或 CI,用的是和這個頁面一樣的評分引擎。",
  "footer.licenseLinkText": "授權",
};
