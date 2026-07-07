// Vietnamese (vi). Same key set as en.js - see web/i18n/en.js for the rules
// (do-not-translate list, {placeholder} discipline, plural categories).
// Plural categories used here: one, other, both given the same text -
// Vietnamese doesn't mark grammatical number at all (verified via
// Intl.PluralRules("vi").resolvedOptions().pluralCategories -> only
// "other" is ever reported; "one" is kept identical for robustness).

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs.vi = {
  "meta.title": "unslop — tìm ra điều tố cáo AI trong bài viết của bạn",
  "meta.description": "Dán bài viết của bạn vào và xem điều gì khiến nó nghe như robot, để sửa trước khi gửi đi. Chạy hoàn toàn trong trình duyệt của bạn — không có gì được tải lên đâu cả.",

  "skipToEditor": "Chuyển đến khung soạn thảo",
  "theme.switcherLabel": "Giao diện",
  "theme.auto": "Tự động",
  "uilang.switcherLabel": "Ngôn ngữ",

  "hero.heading": "Xem điều gì khiến bài viết của bạn nghe như robot.",
  "hero.tagline": "Dán một bản nháp bên dưới. unslop chỉ ra chính xác những từ ngữ và thói quen tố cáo điều đó, để bạn sửa trước khi gửi đi.",
  "privacy.strong": "Mọi thứ đều chạy trong trình duyệt của bạn.",
  "privacy.rest": "Không có gì bạn dán vào bị tải lên, lưu trữ hay gửi đi bất cứ đâu.",

  "toolbar.ariaLabel": "Thao tác soạn thảo",
  "toolbar.sampleHeavy": "Thử một ví dụ rất máy móc",
  "toolbar.sampleSubtle": "Thử một ví dụ tinh tế",
  "toolbar.sampleSpanish": "Thử một ví dụ bằng tiếng Tây Ban Nha",
  "toolbar.clear": "Xóa",
  "toolbar.copy": "Sao chép văn bản",
  "toolbar.copied": "Đã sao chép",
  "toolbar.wordCount.one": "{count} từ",
  "toolbar.wordCount.other": "{count} từ",

  "textlang.selectLabel": "Kiểm tra văn bản theo ngôn ngữ",
  "textlang.autoOption": "Tự động",
  "textlang.autoDetected": "Tự động — đã nhận diện: {name}",
  "textlang.autoFallback": "Tự động — không khớp",
  "textlang.fallbackHint": "Không có gói ngôn ngữ nào khớp với văn bản này. Chỉ các kiểm tra cấu trúc và danh sách từ tiếng Anh được chạy.",

  "editor.textareaLabel": "Bài viết của bạn — dán hoặc gõ vào đây để kiểm tra xem có nghe như AI không",
  "editor.placeholder": "Dán hoặc gõ bài viết của bạn vào đây...",
  "editor.hintMarks": "Các dấu đánh dấu cho thấy điều unslop đã phát hiện. Di chuột hoặc dùng Tab đến một dấu để xem chi tiết.",
  "editor.hintTabbing": "Nhấn {tab} để vào văn bản, rồi nhấn {tab} lần nữa để di chuyển giữa các dấu đánh dấu.",

  "results.ariaLabel": "Kết quả",
  "score.eyebrow": "Điểm AI",
  "score.unit": "/1000 từ",
  "score.meta.words": "Số từ",
  "score.meta.emdash": "Gạch ngang dài",
  "score.meta.emoji": "Emoji",
  "score.meta.rhythm": "Nhịp điệu câu",
  "score.rhythm.notEnough": "chưa đủ câu",
  "score.rhythm.evenSuffix": " (quá đều)",
  "score.liveAnnouncement": "Điểm {score} trên mỗi nghìn từ. {verdict}.",

  "verdict.good": "nghe giống con người",
  "verdict.warn": "có vài dấu hiệu AI - nên xem lại",
  "verdict.bad": "nghe giống AI - cần viết lại thật sự",

  "breakdown.heading": "Phân tích chi tiết",
  "category.phrase": "Cụm từ đệm",
  "category.buzzword": "Từ thời thượng",
  "category.construction": "Cấu trúc câu",
  "category.hedge": "Từ giảm nhẹ",
  "category.emoji": "Emoji",
  "category.emdash": "Gạch ngang dài",
  "category.bold-bullet": "Gạch đầu dòng in đậm",
  "breakdown.section.buzzword": "Từ thời thượng",
  "breakdown.section.phrase": "Cụm từ đệm",
  "breakdown.section.construction": "Cấu trúc câu",
  "breakdown.rhythmSurface": "Nhịp điệu & đặc điểm bề mặt",
  "breakdown.clean.heading": "Đọc lên sạch sẽ.",
  "breakdown.clean.notEnoughText": "Vẫn còn quá ít văn bản để đánh giá. Dán thêm một chút để có kết quả đáng tin cậy.",
  "breakdown.clean.noneFired": "Không có kiểm tra nào của unslop được kích hoạt trên văn bản này.",
  "finding.hitCount.one": "{count} lần",
  "finding.hitCount.other": "{count} lần",
  "finding.linesLabel": "dòng {lines}",
  "finding.styleNotScored": " (văn phong, không tính điểm)",
  "finding.fixPrefix": "Cách sửa: ",

  "surface.emdashLabel": "gạch ngang dài",
  "surface.emdashExcess": "gạch ngang dài (vượt {excess} so với mức bình thường)",
  "surface.emojiCount.one": "{count} emoji",
  "surface.emojiCount.other": "{count} emoji",
  "surface.boldBullet": "gạch đầu dòng **in đậm**",
  "surface.boldBulletTemplateRun": " (trông giống mẫu dựng sẵn)",
  "surface.sentenceVariation": "độ biến thiên độ dài câu",
  "surface.suspiciouslyEven": " (đều đến mức đáng ngờ)",

  "explainer.summary": "Những gì được kiểm tra",
  "explainer.buzzword.term": "Từ thời thượng",
  "explainer.buzzword.def": "Một số từ xuất hiện trong văn bản do máy viết với tần suất vượt xa lời nói bình thường. Một từ đơn lẻ không nói lên điều gì. Một cụm từ như vậy trong cùng một đoạn văn mới là dấu hiệu tố cáo.",
  "explainer.phrase.term": "Cụm từ đệm",
  "explainer.phrase.def": "Những câu mở đầu và kết thúc rập khuôn mà mô hình hay dùng: một câu dẫn chỉ để đằng hắng, một lời đề nghị giúp đỡ vui vẻ ở cuối, một lời thông báo trước khi thật sự đi vào chủ đề. Chúng làm tăng số từ mà không thêm được gì.",
  "explainer.construction.term": "Cấu trúc câu",
  "explainer.construction.def": "Đây là kiểu câu, không phải từ đơn lẻ: dựng lên sự tương phản giữa hai điều chỉ để dừng lại ở điều thứ hai, khẳng định một sự thật bằng cách phủ định điều ngược lại trước, và mở đầu bằng câu hỏi chỉ để câu kéo thay vì đi thẳng vào vấn đề.",
  "explainer.hedge.term": "Từ giảm nhẹ",
  "explainer.hedge.def": "Những từ như có thể, thường, và hay, chất chồng trong cùng một đoạn văn bản. Bản thân chúng không tính vào điểm, nhưng đáng để xem qua. Quá nhiều từ giảm nhẹ liên tiếp nghe có vẻ né tránh.",
  "explainer.emdash.term": "Gạch ngang dài",
  "explainer.emdash.def": "Thỉnh thoảng dùng một gạch ngang dài là dấu câu bình thường. Có một cái trong gần như mọi câu là thói quen đáng bỏ.",
  "explainer.emoji.term": "Emoji trong bài viết",
  "explainer.emoji.def": "Bình thường trong tin nhắn trò chuyện, nhưng lạc lõng trong báo cáo, tệp README hay thư xin việc.",
  "explainer.boldBullet.term": "Gạch đầu dòng in đậm",
  "explainer.boldBullet.def": "Một chuỗi dài các gạch đầu dòng đều theo cùng một khuôn mẫu: một từ in đậm, dấu hai chấm, rồi một lời giải thích ngắn. Một hoặc hai cái là danh sách bình thường. Bốn hoặc năm cái liên tiếp là một khuôn mẫu dựng sẵn.",
  "explainer.rhythm.term": "Nhịp điệu câu",
  "explainer.rhythm.def": "Văn bản thật sự biến đổi độ dài câu một cách tự nhiên. Khi mọi câu đều có độ dài gần như giống hệt nhau, chính sự đều đặn đó đã là dấu hiệu tố cáo.",

  "footer.license": "Miễn phí cho mục đích phi thương mại; sử dụng thương mại cần có giấy phép.",
  "footer.sourceLinkText": "Mã nguồn trên GitHub",
  "footer.cliPrefix": "Thích dùng terminal hơn? ",
  "footer.cliSuffix": " tích hợp vào pre-commit hoặc CI, dùng cùng bộ máy chấm điểm như trang này.",
  "footer.licenseLinkText": "Giấy phép",
};
