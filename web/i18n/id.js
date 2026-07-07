// Indonesian (id). Same key set as en.js - see web/i18n/en.js for the rules
// (do-not-translate list, {placeholder} discipline, plural categories).
// Plural categories used here: one, other, both given the same text -
// Indonesian doesn't mark grammatical number at all (verified via
// Intl.PluralRules("id").resolvedOptions().pluralCategories -> only
// "other" is ever reported; "one" is kept identical for robustness).

window.UnslopI18N = window.UnslopI18N || {};
window.UnslopI18N.catalogs = window.UnslopI18N.catalogs || {};
window.UnslopI18N.catalogs.id = {
  "meta.title": "unslop — temukan yang membocorkan AI dalam tulisanmu",
  "meta.description": "Tempel tulisanmu dan lihat apa yang membuatnya terdengar seperti robot, supaya bisa diperbaiki sebelum dikirim. Berjalan sepenuhnya di browser kamu — tidak ada yang diunggah.",

  "skipToEditor": "Lompat ke editor",
  "theme.switcherLabel": "Tema",
  "theme.auto": "Otomatis",
  "uilang.switcherLabel": "Bahasa",

  "hero.heading": "Lihat apa yang membuat tulisanmu terdengar seperti robot.",
  "hero.tagline": "Tempel draf di bawah ini. unslop menunjukkan tepat kata dan kebiasaan yang membocorkannya, supaya kamu bisa memperbaikinya sebelum mengirim.",
  "privacy.strong": "Semuanya berjalan di browser kamu.",
  "privacy.rest": "Tidak ada yang kamu tempel yang diunggah, disimpan, atau dikirim ke mana pun.",

  "toolbar.ariaLabel": "Aksi editor",
  "toolbar.sampleHeavy": "Coba contoh yang sangat artifisial",
  "toolbar.sampleSubtle": "Coba contoh yang halus",
  "toolbar.sampleSpanish": "Coba contoh berbahasa Spanyol",
  "toolbar.clear": "Bersihkan",
  "toolbar.copy": "Salin teks",
  "toolbar.copied": "Tersalin",
  "toolbar.wordCount.one": "{count} kata",
  "toolbar.wordCount.other": "{count} kata",

  "textlang.selectLabel": "Periksa teks sebagai",
  "textlang.autoOption": "Otomatis",
  "textlang.autoDetected": "Otomatis — terdeteksi: {name}",
  "textlang.autoFallback": "Otomatis — tidak ada yang cocok",
  "textlang.fallbackHint": "Tidak ada paket bahasa yang cocok dengan teks ini. Hanya pemeriksaan struktural dan daftar kata bahasa Inggris yang dijalankan.",

  "editor.textareaLabel": "Tulisanmu — tempel atau ketik di sini untuk memeriksa apakah terdengar seperti AI",
  "editor.placeholder": "Tempel atau ketik tulisanmu di sini...",
  "editor.hintMarks": "Tanda menunjukkan apa yang ditemukan unslop. Arahkan kursor atau gunakan Tab ke sebuah tanda untuk melihat detailnya.",
  "editor.hintTabbing": "Tekan {tab} untuk masuk ke teks, lalu {tab} lagi untuk berpindah antar tanda.",

  "results.ariaLabel": "Hasil",
  "score.eyebrow": "Skor AI",
  "score.unit": "/1000 kata",
  "score.meta.words": "Kata",
  "score.meta.emdash": "Tanda pisah panjang",
  "score.meta.emoji": "Emoji",
  "score.meta.rhythm": "Ritme kalimat",
  "score.rhythm.notEnough": "kalimat terlalu sedikit",
  "score.rhythm.evenSuffix": " (sangat rata)",
  "score.liveAnnouncement": "Skor {score} per seribu kata. {verdict}.",

  "verdict.good": "terdengar seperti manusia",
  "verdict.warn": "ada beberapa tanda AI - sebaiknya diperiksa lagi",
  "verdict.bad": "terdengar seperti AI - perlu ditulis ulang sepenuhnya",

  "breakdown.heading": "Rincian",
  "category.phrase": "Frasa pengisi",
  "category.buzzword": "Kata kunci tren",
  "category.construction": "Konstruksi",
  "category.hedge": "Kata pelunak",
  "category.emoji": "Emoji",
  "category.emdash": "Tanda pisah panjang",
  "category.bold-bullet": "Poin bercetak tebal",
  "breakdown.section.buzzword": "Kata kunci tren",
  "breakdown.section.phrase": "Frasa pengisi",
  "breakdown.section.construction": "Konstruksi",
  "breakdown.rhythmSurface": "Ritme & ciri permukaan",
  "breakdown.clean.heading": "Terbaca bersih.",
  "breakdown.clean.notEnoughText": "Teksnya masih terlalu sedikit untuk dinilai. Tempel lebih banyak lagi untuk hasil yang bisa diandalkan.",
  "breakdown.clean.noneFired": "Tidak ada pemeriksaan unslop yang terpicu pada teks ini.",
  "finding.hitCount.one": "{count} kali",
  "finding.hitCount.other": "{count} kali",
  "finding.linesLabel": "baris {lines}",
  "finding.styleNotScored": " (gaya, tidak dinilai)",
  "finding.fixPrefix": "Perbaikan: ",

  "surface.emdashLabel": "tanda pisah panjang",
  "surface.emdashExcess": "tanda pisah panjang ({excess} di atas normal)",
  "surface.emojiCount.one": "{count} emoji",
  "surface.emojiCount.other": "{count} emoji",
  "surface.boldBullet": "poin **bercetak tebal**",
  "surface.boldBulletTemplateRun": " (terlihat seperti templat)",
  "surface.sentenceVariation": "variasi panjang kalimat",
  "surface.suspiciouslyEven": " (mencurigakan karena terlalu rata)",

  "explainer.summary": "Apa yang diperiksa",
  "explainer.buzzword.term": "Kata kunci tren",
  "explainer.buzzword.def": "Kata-kata tertentu muncul dalam tulisan mesin jauh lebih sering dibanding percakapan biasa. Satu saja tidak berarti apa-apa. Kumpulan kata itu dalam satu paragraf adalah tandanya.",
  "explainer.phrase.term": "Frasa pengisi",
  "explainer.phrase.def": "Pembuka dan penutup baku yang sering dipakai model: kalimat pembuka yang cuma basa-basi, tawaran bantuan yang ceria di akhir, pengumuman sebelum benar-benar masuk ke topik. Menambah jumlah kata tanpa menambah isi.",
  "explainer.construction.term": "Konstruksi",
  "explainer.construction.def": "Bentuk kalimat, bukan kata tunggal: membangun kontras antara dua hal hanya untuk berhenti di yang kedua, menegaskan sebuah fakta dengan menyangkal kebalikannya lebih dulu, dan membuka dengan pertanyaan hanya sebagai pemancing alih-alih langsung ke inti.",
  "explainer.hedge.term": "Kata pelunak",
  "explainer.hedge.def": "Kata seperti bisa, sering, dan biasanya, menumpuk dalam satu bagian teks. Tidak dinilai sendiri, tapi patut diperhatikan. Terlalu banyak pelunak berturut-turut terdengar tidak tegas.",
  "explainer.emdash.term": "Tanda pisah panjang",
  "explainer.emdash.def": "Sesekali memakai tanda pisah panjang itu tanda baca yang wajar. Satu di hampir setiap kalimat adalah kebiasaan yang layak dihentikan.",
  "explainer.emoji.term": "Emoji dalam tulisan",
  "explainer.emoji.def": "Wajar dalam pesan chat, tapi tidak pas dalam laporan, README, atau surat lamaran.",
  "explainer.boldBullet.term": "Poin bercetak tebal",
  "explainer.boldBullet.def": "Deretan poin panjang yang semuanya mengikuti bentuk yang sama: kata dicetak tebal, titik dua, lalu penjelasan singkat. Satu atau dua itu daftar biasa. Empat atau lima berturut-turut itu templat.",
  "explainer.rhythm.term": "Ritme kalimat",
  "explainer.rhythm.def": "Tulisan asli memvariasikan panjang kalimat tanpa berusaha. Kalau setiap kalimat panjangnya hampir sama persis, keseragaman itu sendiri sudah jadi tandanya.",

  "footer.license": "Gratis untuk penggunaan nonkomersial; penggunaan komersial perlu lisensi.",
  "footer.sourceLinkText": "Kode sumber di GitHub",
  "footer.cliPrefix": "Lebih suka terminal? ",
  "footer.cliSuffix": " bisa dipakai di pre-commit atau CI, dengan mesin penilai yang sama seperti halaman ini.",
  "footer.licenseLinkText": "Lisensi",
};
