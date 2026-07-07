// Korean (ko). Same key set as en.js - see web/i18n/en.js for the rules
// (do-not-translate list, {placeholder} discipline, plural categories).
// Plural categories used here: one, other, both given the same text -
// Korean doesn't mark grammatical number at all (verified via
// Intl.PluralRules("ko").resolvedOptions().pluralCategories -> only
// "other" is ever reported; "one" is kept identical for robustness).

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs.ko = {
  "meta.title": "unslop — 글에서 AI 티가 나는 부분을 찾아드립니다",
  "meta.description": "글을 붙여넣으면 로봇처럼 들리게 만드는 요소를 보여드립니다. 보내기 전에 고쳐보세요. 모든 처리는 브라우저 안에서만 이루어지며 아무것도 업로드되지 않습니다.",

  "skipToEditor": "편집기로 건너뛰기",
  "theme.switcherLabel": "테마",
  "theme.auto": "자동",
  "uilang.switcherLabel": "언어",

  "hero.heading": "글이 로봇처럼 들리게 만드는 요소를 확인해보세요.",
  "hero.tagline": "아래에 초안을 붙여넣어 보세요. unslop이 그 원인이 되는 단어와 습관을 정확히 짚어드리니, 보내기 전에 고칠 수 있습니다.",
  "privacy.strong": "모든 처리는 브라우저 안에서 이루어집니다.",
  "privacy.rest": "붙여넣은 내용은 업로드되거나 저장되거나 어디로도 전송되지 않습니다.",

  "toolbar.ariaLabel": "편집 작업",
  "toolbar.sampleHeavy": "매우 인위적인 예시 써보기",
  "toolbar.sampleSubtle": "미묘한 예시 써보기",
  "toolbar.sampleSpanish": "스페인어 예시 써보기",
  "toolbar.clear": "지우기",
  "toolbar.copy": "텍스트 복사",
  "toolbar.copied": "복사됨",
  "toolbar.wordCount.one": "{count}개 단어",
  "toolbar.wordCount.other": "{count}개 단어",

  "textlang.selectLabel": "다음 언어로 텍스트 확인",
  "textlang.autoOption": "자동",
  "textlang.autoDetected": "자동 — 감지됨: {name}",
  "textlang.autoFallback": "자동 — 일치하는 언어 없음",
  "textlang.fallbackHint": "이 텍스트와 일치하는 언어 팩이 없습니다. 구조적 검사와 영어 단어 목록만 실행되었습니다.",

  "editor.textareaLabel": "당신의 글 — AI처럼 들리는지 확인하려면 여기에 붙여넣거나 입력하세요",
  "editor.placeholder": "여기에 글을 붙여넣거나 입력하세요...",
  "editor.hintMarks": "표시는 unslop이 찾아낸 부분을 보여줍니다. 마우스를 올리거나 Tab으로 이동하면 자세한 내용을 볼 수 있습니다.",
  "editor.hintTabbing": "{tab} 키를 눌러 텍스트로 들어간 다음, 다시 {tab} 키를 눌러 표시 사이를 이동하세요.",

  "results.ariaLabel": "결과",
  "score.eyebrow": "AI 티 점수",
  "score.unit": "/1000단어",
  "score.meta.words": "단어 수",
  "score.meta.emdash": "줄표",
  "score.meta.emoji": "이모지",
  "score.meta.rhythm": "문장 리듬",
  "score.rhythm.notEnough": "문장이 너무 적음",
  "score.rhythm.evenSuffix": " (지나치게 균일함)",
  "score.liveAnnouncement": "천 단어당 점수 {score}. {verdict}.",

  "verdict.good": "사람이 쓴 것처럼 보입니다",
  "verdict.warn": "AI 티가 조금 있습니다 - 한 번 다듬어볼 만합니다",
  "verdict.bad": "AI가 쓴 것처럼 보입니다 - 제대로 다시 써야 합니다",

  "breakdown.heading": "세부 분석",
  "category.phrase": "상투적 표현",
  "category.buzzword": "유행어",
  "category.construction": "문장 구조",
  "category.hedge": "완곡 표현",
  "category.emoji": "이모지",
  "category.emdash": "줄표",
  "category.bold-bullet": "굵게 표시된 항목",
  "breakdown.section.buzzword": "유행어",
  "breakdown.section.phrase": "상투적 표현",
  "breakdown.section.construction": "문장 구조",
  "breakdown.rhythmSurface": "리듬 및 표면적 특징",
  "breakdown.clean.heading": "깔끔하게 읽힙니다.",
  "breakdown.clean.notEnoughText": "판단하기에는 아직 텍스트가 부족합니다. 더 붙여넣으면 신뢰할 수 있는 결과를 얻을 수 있습니다.",
  "breakdown.clean.noneFired": "이 텍스트에서는 unslop의 검사 항목이 하나도 감지되지 않았습니다.",
  "finding.hitCount.one": "{count}회",
  "finding.hitCount.other": "{count}회",
  "finding.linesLabel": "{lines}번째 줄",
  "finding.styleNotScored": " (스타일이라 점수에는 포함되지 않음)",
  "finding.fixPrefix": "수정 방법: ",

  "surface.emdashLabel": "줄표",
  "surface.emdashExcess": "줄표 (정상보다 {excess}개 많음)",
  "surface.emojiCount.one": "이모지 {count}개",
  "surface.emojiCount.other": "이모지 {count}개",
  "surface.boldBullet": "**굵게** 표시된 항목",
  "surface.boldBulletTemplateRun": " (템플릿처럼 보임)",
  "surface.sentenceVariation": "문장 길이 변화 정도",
  "surface.suspiciouslyEven": " (의심스러울 정도로 균일함)",

  "explainer.summary": "무엇을 검사하나요",
  "explainer.buzzword.term": "유행어",
  "explainer.buzzword.def": "특정 단어들은 기계가 쓴 텍스트에서 일상 대화보다 훨씬 자주 등장합니다. 하나만 있으면 아무 의미가 없습니다. 같은 문단에 뭉쳐서 나오는 것이 바로 그 신호입니다.",
  "explainer.phrase.term": "상투적 표현",
  "explainer.phrase.def": "모델이 자주 의지하는 뻔한 도입부와 마무리 표현입니다. 그저 목을 가다듬는 것 같은 서두, 마지막에 붙이는 명랑한 도움 제안, 본론에 들어가기도 전에 미리 알리는 예고 같은 것들입니다. 아무것도 더하지 않으면서 글자 수만 늘립니다.",
  "explainer.construction.term": "문장 구조",
  "explainer.construction.def": "단어가 아니라 문장의 형태를 말합니다. 두 가지를 대비시켜 놓고 결국 두 번째 것에만 초점을 맞추는 방식, 반대되는 것을 먼저 부정한 다음 사실을 다시 말하는 방식, 본론으로 바로 들어가지 않고 질문으로 시선만 끌며 시작하는 방식 등입니다.",
  "explainer.hedge.term": "완곡 표현",
  "explainer.hedge.def": "할 수 있다, 종종, 보통 같은 단어들이 같은 구간에 겹겹이 쌓인 것을 말합니다. 그 자체로는 점수에 영향을 주지 않지만 살펴볼 가치는 있습니다. 완곡 표현이 연달아 너무 많으면 회피하는 느낌을 줍니다.",
  "explainer.emdash.term": "줄표",
  "explainer.emdash.def": "가끔 쓰는 줄표는 정상적인 문장 부호입니다. 거의 모든 문장에 하나씩 있다면 고칠 만한 습관입니다.",
  "explainer.emoji.term": "본문 속 이모지",
  "explainer.emoji.def": "채팅 메시지에서는 괜찮지만, 보고서나 README, 자기소개서에는 어울리지 않습니다.",
  "explainer.boldBullet.term": "굵게 표시된 항목",
  "explainer.boldBullet.def": "모두 같은 형태를 따르는 긴 항목 나열입니다. 굵게 표시된 단어, 콜론, 그다음 짧은 설명. 한두 개는 평범한 목록이지만, 네다섯 개가 연달아 나오면 틀에 박힌 것입니다.",
  "explainer.rhythm.term": "문장 리듬",
  "explainer.rhythm.def": "진짜 글은 애쓰지 않아도 문장 길이가 자연스럽게 달라집니다. 모든 문장이 거의 똑같은 길이라면, 그 균일함 자체가 신호입니다.",

  "footer.license": "비상업적 용도로는 무료입니다. 상업적 용도로는 라이선스가 필요합니다.",
  "footer.sourceLinkText": "GitHub에서 소스 코드 보기",
  "footer.cliPrefix": "터미널을 더 선호하시나요? ",
  "footer.cliSuffix": " 는 pre-commit이나 CI에 붙일 수 있으며, 이 페이지와 같은 채점 엔진을 사용합니다.",
  "footer.licenseLinkText": "라이선스",
};
