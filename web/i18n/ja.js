// Japanese (ja). Same key set as en.js - see web/i18n/en.js for the rules
// (do-not-translate list, {placeholder} discipline, plural categories).
// Plural categories used here: one, other, both given the same text -
// Japanese doesn't mark grammatical number at all (verified via
// Intl.PluralRules("ja").resolvedOptions().pluralCategories -> only
// "other" is ever reported; "one" is kept identical for robustness).

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs.ja = {
  "meta.title": "unslop — 文章からAIらしさの正体を見つける",
  "meta.description": "文章を貼り付けると、ロボットっぽく聞こえる原因がわかるので、送る前に直せます。すべてブラウザ内で完結し、どこにもアップロードされません。",

  "skipToEditor": "編集エリアへスキップ",
  "theme.switcherLabel": "テーマ",
  "theme.auto": "自動",
  "uilang.switcherLabel": "言語",

  "hero.heading": "文章がロボットっぽく聞こえる原因を見てみましょう。",
  "hero.tagline": "下に下書きを貼り付けてください。unslopが、その原因になっている言葉や癖をピンポイントで示すので、送る前に直せます。",
  "privacy.strong": "すべてブラウザ内で処理されます。",
  "privacy.rest": "貼り付けた内容がアップロードされたり、保存されたり、どこかへ送信されたりすることはありません。",

  "toolbar.ariaLabel": "エディター操作",
  "toolbar.sampleHeavy": "かなり不自然な例を試す",
  "toolbar.sampleSubtle": "控えめな例を試す",
  "toolbar.sampleSpanish": "スペイン語の例を試す",
  "toolbar.clear": "クリア",
  "toolbar.copy": "テキストをコピー",
  "toolbar.copied": "コピーしました",
  "toolbar.wordCount.one": "{count} 語",
  "toolbar.wordCount.other": "{count} 語",

  "textlang.selectLabel": "この言語として文章をチェック",
  "textlang.autoOption": "自動",
  "textlang.autoDetected": "自動 — 検出: {name}",
  "textlang.autoFallback": "自動 — 該当なし",
  "textlang.fallbackHint": "この文章に一致する言語パックが見つかりませんでした。構造的なチェックと英語の単語リストのみが実行されました。",

  "editor.textareaLabel": "あなたの文章 — ここに貼り付けるか入力して、AIらしさをチェックします",
  "editor.placeholder": "ここに文章を貼り付けるか入力してください...",
  "editor.hintMarks": "マークはunslopが検出した箇所を示します。マークにマウスを乗せるかTabキーで移動すると詳細が見られます。",
  "editor.hintTabbing": "{tab} キーでテキストに入り、もう一度 {tab} キーでマーク間を移動します。",

  "results.ariaLabel": "結果",
  "score.eyebrow": "AIらしさスコア",
  "score.unit": "/1000語",
  "score.meta.words": "単語数",
  "score.meta.emdash": "ダッシュ記号",
  "score.meta.emoji": "絵文字",
  "score.meta.rhythm": "文のリズム",
  "score.rhythm.notEnough": "文が少なすぎます",
  "score.rhythm.evenSuffix": "(非常に均一)",
  "score.liveAnnouncement": "1000語あたりのスコアは{score}。{verdict}。",

  "verdict.good": "人間らしい文章です",
  "verdict.warn": "AIらしさの兆候が少しあります - 見直す価値があります",
  "verdict.bad": "AIらしい文章です - 本格的な書き直しが必要です",

  "breakdown.heading": "内訳",
  "category.phrase": "定型フレーズ",
  "category.buzzword": "流行り言葉",
  "category.construction": "構文パターン",
  "category.hedge": "曖昧表現",
  "category.emoji": "絵文字",
  "category.emdash": "ダッシュ記号",
  "category.bold-bullet": "太字の箇条書き",
  "breakdown.section.buzzword": "流行り言葉",
  "breakdown.section.phrase": "定型フレーズ",
  "breakdown.section.construction": "構文パターン",
  "breakdown.rhythmSurface": "リズムと表面的な特徴",
  "breakdown.clean.heading": "きれいな文章です。",
  "breakdown.clean.notEnoughText": "まだ判断するには文章が少なすぎます。信頼できる結果を得るには、もう少し貼り付けてください。",
  "breakdown.clean.noneFired": "この文章では、unslopのチェックは何も引っかかりませんでした。",
  "finding.hitCount.one": "{count} 回",
  "finding.hitCount.other": "{count} 回",
  "finding.linesLabel": "{lines} 行目",
  "finding.styleNotScored": "(スタイルのため、スコアには影響しません)",
  "finding.fixPrefix": "改善案: ",

  "surface.emdashLabel": "ダッシュ記号",
  "surface.emdashExcess": "ダッシュ記号(通常より{excess}個多い)",
  "surface.emojiCount.one": "{count} 個の絵文字",
  "surface.emojiCount.other": "{count} 個の絵文字",
  "surface.boldBullet": "**太字**の箇条書き",
  "surface.boldBulletTemplateRun": "(テンプレートのように見えます)",
  "surface.sentenceVariation": "文の長さのばらつき",
  "surface.suspiciouslyEven": "(不自然なほど均一)",

  "explainer.summary": "チェック内容",
  "explainer.buzzword.term": "流行り言葉",
  "explainer.buzzword.def": "特定の単語は、機械が書いた文章では通常の会話よりずっと高い頻度で出てきます。1つだけなら何の意味もありません。同じ段落にまとまって出てくることこそが、その兆候です。",
  "explainer.phrase.term": "定型フレーズ",
  "explainer.phrase.def": "モデルが頼りがちな決まり文句の始まりと終わり方です。ただ喉の調子を整えるだけの前置き、最後に添える陽気な手伝いの申し出、話題に入る前のわざとらしい前置き。これらは何も足さずに文字数だけを増やします。",
  "explainer.construction.term": "構文パターン",
  "explainer.construction.def": "単語ではなく文の形です。2つのものの対比をわざわざ作っておいて、結局2つ目に落ち着かせる言い方、まず反対のことを否定してから事実を言い直す言い方、要点にすぐ入らず、フックとしてだけ質問で始める言い方などです。",
  "explainer.hedge.term": "曖昧表現",
  "explainer.hedge.def": "できる、しばしば、通常、といった言葉が同じ箇所に積み重なっているものです。単独ではスコアに影響しませんが、見ておく価値はあります。曖昧表現が連続しすぎると、はっきりしない印象になります。",
  "explainer.emdash.term": "ダッシュ記号",
  "explainer.emdash.def": "たまに使うダッシュ記号は普通の句読点です。ほぼすべての文にあるのは、直す価値のある癖です。",
  "explainer.emoji.term": "文章中の絵文字",
  "explainer.emoji.def": "チャットのメッセージなら問題ありませんが、レポートやREADME、志望動機書には場違いです。",
  "explainer.boldBullet.term": "太字の箇条書き",
  "explainer.boldBullet.def": "すべて同じ形式に従う長い箇条書きの列です。太字の単語、コロン、そして短い説明。1つか2つなら普通のリストですが、4つや5つ連続するとテンプレートです。",
  "explainer.rhythm.term": "文のリズム",
  "explainer.rhythm.def": "本物の文章は、意識せずとも文の長さが自然にばらつきます。どの文もほぼ同じ長さに揃っているなら、その均一さ自体がその兆候です。",

  "footer.license": "非営利目的なら無料。商用利用にはライセンスが必要です。",
  "footer.sourceLinkText": "GitHubでソースコードを見る",
  "footer.cliPrefix": "ターミナルの方が好みですか? ",
  "footer.cliSuffix": " はpre-commitやCIに組み込めて、このページと同じスコアリングエンジンを使います。",
  "footer.licenseLinkText": "ライセンス",
};
