// Simplified Chinese (zh-Hans). Same key set as en.js - see web/i18n/en.js
// for the rules (do-not-translate list, {placeholder} discipline, plural
// categories). Plural categories used here: one, other, both given the
// same text - Chinese doesn't mark grammatical number at all (verified via
// Intl.PluralRules("zh-Hans").resolvedOptions().pluralCategories -> only
// "other" is ever reported; "one" is kept identical for robustness).

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs["zh-Hans"] = {
  "meta.title": "unslop —找出文字里暴露 AI 痕迹的地方",
  "meta.description": "粘贴你的文字,看看是什么让它听起来像机器人写的,发送前先改一改。全部在浏览器里运行——什么都不会上传。",

  "skipToEditor": "跳到编辑区",
  "theme.switcherLabel": "主题",
  "theme.auto": "自动",
  "uilang.switcherLabel": "语言",

  "hero.heading": "看看是什么让你的文字听起来像机器人。",
  "hero.tagline": "把草稿粘贴到下面。unslop 会准确指出暴露痕迹的那些词语和习惯,方便你在发送前改掉。",
  "privacy.strong": "一切都在你的浏览器里运行。",
  "privacy.rest": "你粘贴的任何内容都不会被上传、保存或发送到任何地方。",

  "toolbar.ariaLabel": "编辑操作",
  "toolbar.sampleHeavy": "试试一个很机器味的例子",
  "toolbar.sampleSubtle": "试试一个不太明显的例子",
  "toolbar.sampleSpanish": "试试一个西班牙语例子",
  "toolbar.clear": "清空",
  "toolbar.copy": "复制文字",
  "toolbar.copied": "已复制",
  "toolbar.wordCount.one": "{count} 个词",
  "toolbar.wordCount.other": "{count} 个词",

  "textlang.selectLabel": "按此语言检查文字",
  "textlang.autoOption": "自动",
  "textlang.autoDetected": "自动 — 检测到:{name}",
  "textlang.autoFallback": "自动 — 没有匹配",
  "textlang.fallbackHint": "没有语言包和这段文字匹配,只运行了结构检查和英文词表。",

  "editor.textareaLabel": "你的文字 — 粘贴或输入到这里,检查是否听起来像 AI",
  "editor.placeholder": "在这里粘贴或输入你的文字...",
  "editor.hintMarks": "标记显示 unslop 发现的问题。悬停鼠标或用 Tab 键切换到标记查看详情。",
  "editor.hintTabbing": "按 {tab} 进入文本区,再按一次 {tab} 可以在各个标记之间移动。",

  "results.ariaLabel": "结果",
  "score.eyebrow": "AI 痕迹分数",
  "score.unit": "/千词",
  "score.meta.words": "词数",
  "score.meta.emdash": "破折号",
  "score.meta.emoji": "表情符号",
  "score.meta.rhythm": "句子节奏",
  "score.rhythm.notEnough": "句子太少",
  "score.rhythm.evenSuffix": "(过于均匀)",
  "score.liveAnnouncement": "每千词得分 {score}。{verdict}。",

  "verdict.good": "读起来像真人写的",
  "verdict.warn": "有一些 AI 痕迹 - 值得再看一遍",
  "verdict.bad": "读起来像 AI 写的 - 需要认真重写",

  "breakdown.heading": "详细分析",
  "category.phrase": "套话",
  "category.buzzword": "流行词",
  "category.construction": "句式套路",
  "category.hedge": "模糊限定词",
  "category.emoji": "表情符号",
  "category.emdash": "破折号",
  "category.bold-bullet": "加粗要点",
  "breakdown.section.buzzword": "流行词",
  "breakdown.section.phrase": "套话",
  "breakdown.section.construction": "句式套路",
  "breakdown.rhythmSurface": "节奏与表面特征",
  "breakdown.clean.heading": "读起来很干净。",
  "breakdown.clean.notEnoughText": "文字还太少,不足以判断。多粘贴一些以获得可靠的结果。",
  "breakdown.clean.noneFired": "这段文字没有触发 unslop 的任何检查项。",
  "finding.hitCount.one": "{count} 次",
  "finding.hitCount.other": "{count} 次",
  "finding.linesLabel": "第 {lines} 行",
  "finding.styleNotScored": "(属于风格,不计分)",
  "finding.fixPrefix": "修改建议:",

  "surface.emdashLabel": "破折号",
  "surface.emdashExcess": "破折号(比正常水平多出 {excess} 个)",
  "surface.emojiCount.one": "{count} 个表情符号",
  "surface.emojiCount.other": "{count} 个表情符号",
  "surface.boldBullet": "**加粗**要点",
  "surface.boldBulletTemplateRun": "(像是套模板)",
  "surface.sentenceVariation": "句长变化程度",
  "surface.suspiciouslyEven": "(均匀得可疑)",

  "explainer.summary": "检测哪些内容",
  "explainer.buzzword.term": "流行词",
  "explainer.buzzword.def": "某些词在机器写的文字里出现的频率远高于日常说话。单独出现一次说明不了什么,但如果同一段里扎堆出现,那就是破绽。",
  "explainer.phrase.term": "套话",
  "explainer.phrase.def": "模型爱用的那些老套开头和结尾:只是清清嗓子的引子,结尾时热情地表示愿意帮忙,还没进入主题就先做个预告。这些话只是凑字数,没有实际内容。",
  "explainer.construction.term": "句式套路",
  "explainer.construction.def": "指的是句子结构,不是单个词:先制造两件事之间的对比,只为了落在第二件事上;先否定反面,再重申一遍事实;开头抛出一个问题只是为了吸引注意,而不是直接说重点。",
  "explainer.hedge.term": "模糊限定词",
  "explainer.hedge.def": "像可能、经常、通常这类词,如果在一段文字里堆得很密集。单独出现不计分,但值得留意。连续出现太多模糊限定词,读起来会很含糊其辞。",
  "explainer.emdash.term": "破折号",
  "explainer.emdash.def": "偶尔用一个破折号是正常的标点用法。但如果几乎每句话都有一个,那就是该改掉的习惯了。",
  "explainer.emoji.term": "正文里的表情符号",
  "explainer.emoji.def": "发消息聊天时没问题,但出现在报告、README 或求职信里就显得不合适。",
  "explainer.boldBullet.term": "加粗要点",
  "explainer.boldBullet.def": "一长串要点都是同一种格式:一个加粗的词,一个冒号,然后是简短说明。一两条是正常的列表,连续四五条就是套模板了。",
  "explainer.rhythm.term": "句子节奏",
  "explainer.rhythm.def": "真实的文字会自然地变化句子长短,不是刻意为之。如果每句话的长度都几乎一样,这种整齐本身就是破绽。",

  "footer.license": "非商业用途免费;商业用途需要许可证。",
  "footer.sourceLinkText": "在 GitHub 上查看源码",
  "footer.cliPrefix": "更喜欢用命令行? ",
  "footer.cliSuffix": " 可以接入 pre-commit 或 CI,用的是和这个页面一样的评分引擎。",
  "footer.licenseLinkText": "许可证",
};
