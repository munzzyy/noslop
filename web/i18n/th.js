// Thai (th). Same key set as en.js - see web/i18n/en.js for the rules
// (do-not-translate list, {placeholder} discipline, plural categories).
// Plural categories used here: one, other, both given the same text - Thai
// doesn't mark grammatical number at all (verified via
// Intl.PluralRules("th").resolvedOptions().pluralCategories -> only
// "other" is ever reported; "one" is kept identical for robustness).

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs.th = {
  "meta.title": "unslop — หาจุดที่บ่งบอกว่าเป็น AI ในงานเขียนของคุณ",
  "meta.description": "วางข้อความของคุณแล้วดูว่าอะไรทำให้มันฟังดูเหมือนหุ่นยนต์ จะได้แก้ไขก่อนส่ง ทำงานในเบราว์เซอร์ของคุณทั้งหมด — ไม่มีอะไรถูกอัปโหลดไปที่ไหน",

  "skipToEditor": "ข้ามไปที่ช่องแก้ไข",
  "theme.switcherLabel": "ธีม",
  "theme.auto": "อัตโนมัติ",
  "uilang.switcherLabel": "ภาษา",

  "hero.heading": "ดูว่าอะไรทำให้งานเขียนของคุณฟังดูเหมือนหุ่นยนต์",
  "hero.tagline": "วางร่างข้อความไว้ด้านล่าง unslop จะชี้ตรงจุดคำและความเคยชินที่บ่งบอกให้เห็น เพื่อให้คุณแก้ไขได้ก่อนส่ง",
  "privacy.strong": "ทุกอย่างทำงานในเบราว์เซอร์ของคุณ",
  "privacy.rest": "ข้อความที่คุณวางจะไม่ถูกอัปโหลด บันทึก หรือส่งไปที่ไหนทั้งสิ้น",

  "toolbar.ariaLabel": "การทำงานของช่องแก้ไข",
  "toolbar.sampleHeavy": "ลองตัวอย่างที่ดูปลอมมาก",
  "toolbar.sampleSubtle": "ลองตัวอย่างที่แนบเนียน",
  "toolbar.sampleSpanish": "ลองตัวอย่างภาษาสเปน",
  "toolbar.clear": "ล้าง",
  "toolbar.copy": "คัดลอกข้อความ",
  "toolbar.copied": "คัดลอกแล้ว",
  "toolbar.wordCount.one": "{count} คำ",
  "toolbar.wordCount.other": "{count} คำ",

  "textlang.selectLabel": "ตรวจข้อความเป็นภาษา",
  "textlang.autoOption": "อัตโนมัติ",
  "textlang.autoDetected": "อัตโนมัติ — ตรวจพบ: {name}",
  "textlang.autoFallback": "อัตโนมัติ — ไม่พบภาษาที่ตรงกัน",
  "textlang.fallbackHint": "ไม่มีชุดภาษาใดตรงกับข้อความนี้ มีเพียงการตรวจโครงสร้างและรายการคำภาษาอังกฤษที่ทำงาน",

  "editor.textareaLabel": "งานเขียนของคุณ — วางหรือพิมพ์ที่นี่เพื่อตรวจว่าฟังดูเหมือน AI หรือไม่",
  "editor.placeholder": "วางหรือพิมพ์ข้อความของคุณที่นี่...",
  "editor.hintMarks": "เครื่องหมายแสดงสิ่งที่ unslop พบ วางเมาส์หรือกด Tab ไปที่เครื่องหมายเพื่อดูรายละเอียด",
  "editor.hintTabbing": "กด {tab} เพื่อเข้าไปในข้อความ จากนั้นกด {tab} อีกครั้งเพื่อย้ายไปมาระหว่างเครื่องหมาย",

  "results.ariaLabel": "ผลลัพธ์",
  "score.eyebrow": "คะแนนความเป็น AI",
  "score.unit": "/1,000 คำ",
  "score.meta.words": "จำนวนคำ",
  "score.meta.emdash": "เครื่องหมายขีดยาว",
  "score.meta.emoji": "อีโมจิ",
  "score.meta.rhythm": "จังหวะประโยค",
  "score.rhythm.notEnough": "ประโยคน้อยเกินไป",
  "score.rhythm.evenSuffix": " (สม่ำเสมอมากเกินไป)",
  "score.liveAnnouncement": "คะแนน {score} ต่อพันคำ {verdict}",

  "verdict.good": "ฟังดูเหมือนคนเขียน",
  "verdict.warn": "มีร่องรอย AI อยู่บ้าง - ควรลองทบทวนดู",
  "verdict.bad": "ฟังดูเหมือน AI เขียน - ต้องเขียนใหม่จริงจัง",

  "breakdown.heading": "รายละเอียด",
  "category.phrase": "วลีเติมเต็ม",
  "category.buzzword": "คำฮิต",
  "category.construction": "โครงสร้างประโยค",
  "category.hedge": "คำกั๊ก",
  "category.emoji": "อีโมจิ",
  "category.emdash": "เครื่องหมายขีดยาว",
  "category.bold-bullet": "หัวข้อตัวหนา",
  "breakdown.section.buzzword": "คำฮิต",
  "breakdown.section.phrase": "วลีเติมเต็ม",
  "breakdown.section.construction": "โครงสร้างประโยค",
  "breakdown.rhythmSurface": "จังหวะและลักษณะพื้นผิว",
  "breakdown.clean.heading": "อ่านแล้วดูสะอาด",
  "breakdown.clean.notEnoughText": "ข้อความยังน้อยเกินกว่าจะประเมินได้ วางเพิ่มอีกหน่อยเพื่อผลลัพธ์ที่น่าเชื่อถือ",
  "breakdown.clean.noneFired": "ไม่มีการตรวจสอบใดของ unslop ทำงานกับข้อความนี้",
  "finding.hitCount.one": "{count} ครั้ง",
  "finding.hitCount.other": "{count} ครั้ง",
  "finding.linesLabel": "บรรทัดที่ {lines}",
  "finding.styleNotScored": " (สไตล์ ไม่นับคะแนน)",
  "finding.fixPrefix": "วิธีแก้: ",

  "surface.emdashLabel": "เครื่องหมายขีดยาว",
  "surface.emdashExcess": "เครื่องหมายขีดยาว (เกินปกติ {excess} ครั้ง)",
  "surface.emojiCount.one": "อีโมจิ {count} ตัว",
  "surface.emojiCount.other": "อีโมจิ {count} ตัว",
  "surface.boldBullet": "หัวข้อ**ตัวหนา**",
  "surface.boldBulletTemplateRun": " (ดูเหมือนแม่แบบ)",
  "surface.sentenceVariation": "ความหลากหลายของความยาวประโยค",
  "surface.suspiciouslyEven": " (สม่ำเสมอผิดสังเกต)",

  "explainer.summary": "สิ่งที่ตรวจสอบ",
  "explainer.buzzword.term": "คำฮิต",
  "explainer.buzzword.def": "คำบางคำปรากฏในข้อความที่เครื่องเขียนบ่อยกว่าการพูดปกติมาก คำเดียวโดดๆ ไม่มีความหมายอะไร แต่ถ้ามารวมกันเป็นกลุ่มในย่อหน้าเดียวกัน นั่นคือร่องรอยที่บ่งบอก",
  "explainer.phrase.term": "วลีเติมเต็ม",
  "explainer.phrase.def": "การเปิดและปิดแบบสำเร็จรูปที่โมเดลมักใช้: คำนำที่แค่กระแอมกระไอ ข้อเสนอช่วยเหลือแบบร่าเริงตอนท้าย การประกาศก่อนที่จะเข้าเรื่องจริง สิ่งเหล่านี้เพิ่มจำนวนคำโดยไม่ได้เพิ่มเนื้อหาอะไรเลย",
  "explainer.construction.term": "โครงสร้างประโยค",
  "explainer.construction.def": "นี่คือรูปแบบประโยค ไม่ใช่คำเดี่ยวๆ: การสร้างความขัดแย้งระหว่างสองสิ่งเพียงเพื่อจะไปลงเอยที่สิ่งที่สอง การย้ำข้อเท็จจริงด้วยการปฏิเสธสิ่งตรงข้ามก่อน และการเปิดด้วยคำถามเพียงเพื่อดึงความสนใจแทนที่จะเข้าประเด็นตรงๆ",
  "explainer.hedge.term": "คำกั๊ก",
  "explainer.hedge.def": "คำอย่างอาจจะ บ่อยครั้ง และโดยทั่วไป ที่มากองรวมกันในข้อความช่วงเดียว คำเหล่านี้ไม่มีผลต่อคะแนนโดยตัวมันเอง แต่ก็ควรสังเกตไว้ คำกั๊กมากเกินไปติดต่อกันฟังดูเหมือนหลบเลี่ยง",
  "explainer.emdash.term": "เครื่องหมายขีดยาว",
  "explainer.emdash.def": "เครื่องหมายขีดยาวที่ใช้เป็นครั้งคราวถือเป็นเครื่องหมายวรรคตอนปกติ แต่ถ้ามีเกือบทุกประโยค นั่นคือความเคยชินที่ควรเลิก",
  "explainer.emoji.term": "อีโมจิในเนื้อความ",
  "explainer.emoji.def": "ใช้ได้ในข้อความแชท แต่ไม่เหมาะในรายงาน README หรือจดหมายสมัครงาน",
  "explainer.boldBullet.term": "หัวข้อตัวหนา",
  "explainer.boldBullet.def": "หัวข้อจำนวนมากที่เรียงกันเป็นรูปแบบเดียวกันทั้งหมด: คำตัวหนา เครื่องหมายโคลอน แล้วตามด้วยคำอธิบายสั้นๆ หนึ่งหรือสองหัวข้อถือเป็นรายการปกติ แต่สี่หรือห้าหัวข้อติดกันคือแม่แบบสำเร็จรูป",
  "explainer.rhythm.term": "จังหวะประโยค",
  "explainer.rhythm.def": "งานเขียนจริงจะมีความยาวประโยคที่หลากหลายไปเองโดยไม่ต้องพยายาม เมื่อทุกประโยคยาวใกล้เคียงกันเกือบทั้งหมด ความสม่ำเสมอนั้นเองคือร่องรอยที่บ่งบอก",

  "footer.license": "ใช้ฟรีสำหรับการใช้งานที่ไม่ใช่เชิงพาณิชย์ การใช้งานเชิงพาณิชย์ต้องมีใบอนุญาต",
  "footer.sourceLinkText": "ซอร์สโค้ดบน GitHub",
  "footer.cliPrefix": "ชอบใช้เทอร์มินัลมากกว่าไหม? ",
  "footer.cliSuffix": " ใช้ร่วมกับ pre-commit หรือ CI ได้ ด้วยเอนจินให้คะแนนตัวเดียวกับหน้านี้",
  "footer.licenseLinkText": "ใบอนุญาต",
};
