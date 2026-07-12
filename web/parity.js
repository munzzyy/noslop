/*
 * parity.js - prove web/detector.js scores a piece of text identically to the
 * noslop.py CLI. Runs the JS analyze() and `py/python noslop.py --json` on the
 * same fixtures and diffs the results. Any drift between the browser scorer and
 * the CLI shows up here (and in CI) instead of as a silent lie in the web app.
 *
 *   node web/parity.js
 *
 * Exit 0 = every fixture matches, 1 = a mismatch (or the CLI wouldn't run).
 */
"use strict";
const { execFileSync } = require("child_process");
const path = require("path");
const Noslop = require("./detector.js");

const CLI = path.join(__dirname, "..", "noslop.py");

// Pick whatever Python launcher exists: `python` on most machines, `py` on a
// default Windows install where `python` is the Store stub.
function pyRunner() {
  for (const cand of [["python3"], ["python"], ["py", "-3"]]) {
    try {
      execFileSync(cand[0], cand.slice(1).concat(["--version"]), { stdio: "ignore" });
      return cand;
    } catch (_) { /* try next */ }
  }
  throw new Error("no python interpreter found (tried python3, python, py -3)");
}
const RUNNER = pyRunner();

function cliAnalyze(text, lang) {
  // --threshold 1e12 so the CLI always exits 0: it exits 1 on a high score by
  // design, which execFileSync would otherwise throw on. The score in --json
  // output is the same either way.
  const args = RUNNER.slice(1).concat([CLI, "--json", "--no-config", "--threshold", "1e12"]);
  if (lang) args.push("--lang", lang);
  const out = execFileSync(RUNNER[0], args, { input: Buffer.from(text, "utf8") });
  return JSON.parse(out.toString("utf8"));
}

// Deep compare; numbers within a tiny epsilon (float score / cv), everything
// else strict. Returns null when equal, else a human-readable path+diff.
function diff(a, b, at) {
  at = at || "$";
  if (typeof a === "number" && typeof b === "number") {
    return Math.abs(a - b) < 1e-6 ? null : `${at}: ${a} != ${b}`;
  }
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b)) return `${at}: array vs non-array`;
    if (a.length !== b.length) return `${at}: length ${a.length} != ${b.length}\n  js=${JSON.stringify(a)}\n  py=${JSON.stringify(b)}`;
    for (let i = 0; i < a.length; i++) {
      const d = diff(a[i], b[i], `${at}[${i}]`);
      if (d) return d;
    }
    return null;
  }
  if (a && b && typeof a === "object" && typeof b === "object") {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const k of keys) {
      const d = diff(a[k], b[k], `${at}.${k}`);
      if (d) return d;
    }
    return null;
  }
  return a === b ? null : `${at}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`;
}

const FIXTURES = {
  "clean prose": "The pump broke on Tuesday. I drove over, pulled the housing, and found a cracked seal. New one cost nine dollars. It runs fine now, though the motor still whines a little when it starts cold.",

  "heavy slop": "It's important to note that this robust, seamless solution will leverage cutting-edge AI to elevate your workflow. Let's dive into how we can unlock a comprehensive, transformative experience. I hope this helps!",

  "not just X but Y": "This is not just a tool, but a whole new way of thinking. It isn't a feature, it's a paradigm. We don't merely build software.",

  "multiword buzzwords": "We delve into a rich tapestry of ideas, a treasure trove of insight. Take a deep dive and find peace of mind. Dive deep.",

  "overlap dive into": "Let's dive into the details. Then we dive into more. A deep dive into the realm of synergy.",

  "em dash spray": "The plan — the real plan — was simple. We moved fast — faster than anyone — and shipped it — twice — before lunch — somehow.",

  "emoji mix": "Great work team ✅ we shipped it 🚀 and the users love it ❤️. Ship it 🇺🇸 and celebrate ⭐️ today.",

  "bold bullets": "Here is the plan:\n- **Speed:** we go fast\n- **Quality:** we stay sharp\n- **Scale:** we grow\n- **Trust:** we deliver\nThat is the whole thing.",

  "uniform rhythm": "The cat sat down slowly today. The dog ran fast across there. The bird flew high above us. The fish swam deep below now. The mouse hid well behind that.",

  "isn't flip": "It isn't about the money, it's about the mission. This is not slow, it's deliberate.",

  "rhetorical opener": "Ever wondered how this works?\nHave you ever felt stuck?\nWhat if there was a better way?\nImagine a world without friction.",

  "hedge stack": "This may work, and it might not. You can try, but results can vary. Often it typically works, and usually it generally does.",

  "wrapped phrase": "It's important to\nnote that we should\nfeel free to\nreach out any time.",

  "apostrophes": "In today's world, at the end of the day, gone are the days when it was hard. In today's fast-paced landscape we thrive.",

  "mixed case": "ROBUST and Seamless and DELVE and Leverage and Comprehensive appear here in odd casing.",

  "long realistic": "In today's fast-paced digital landscape, it's important to note that businesses must leverage cutting-edge technology to stay competitive. This comprehensive guide will delve into the myriad ways you can unlock transformative growth. Whether you're a seasoned professional or just starting out, these robust strategies will empower you to navigate the ever-evolving market. Let's dive in and explore how to supercharge your results. At the end of the day, it's not just about working harder, but working smarter. I hope this helps you on your journey!",

  "empty-ish": "ok",

  "code-ish prose": "Run npm install then npm test. The build failed because the path was wrong. Fixed it by using an absolute path instead of a relative one.",

  "numbered bold bullets": "The steps:\n1. **Plan:** decide the scope\n2. **Build:** write the code\n3. **Ship:** push it out\n4. **Review:** check the result",

  "flag only": "Visit 🇯🇵 in spring and 🇫🇷 in fall. Two trips, one year.",

  "curly quotes": "It’s important to note that we’re here to help. Don’t worry, it’ll be fine.",

  "single sentence long": "The whole thing came down to a single decision made late one night by a tired engineer who had already been warned twice about the risk and chose to ship anyway because the deadline felt more real than the danger.",

  // ---- the 0.7.0 tells: every new check gets a fixture through both engines ----

  "chat artifact citation": "Prices rose in March according to the report :contentReference[oaicite:3]{index=3} and analysts expect further gains. The rest of the passage is deliberately plain so only the artifact fires.",

  "chat artifact tracking": "Read the announcement at https://example.com/news?utm_source=chatgpt.com and tell me what you think. Also see https://example.com/two?utm_source=openai for the other one.",

  "template placeholders are not artifacts": "Dear [Insert Name Here], thank you for your interest in the role. We will contact you at [insert your email] within five business days.",

  "artifact at offset zero": "oaicite residue opens this very text, and the rest of the passage is deliberately plain filler prose about nothing much at all.",

  "curly apostrophe split flip": "The problem isn’t the tooling. It’s the culture around the tooling that nobody wants to name. Here’s why that matters to us.",

  "accented boundary bute": "This design is not only rapide buté in every way we tried and tested here, and the rest reads plainly.",

  "accented anaphora cafe": "the café au lait, café con leche, café americano. the café au lait, café con leche, café americano.",

  "arabic digit list markers": "٣. ✨ item one\n٤. ✨ item two\n\nPlain closing sentence for balance here.",

  "dangling ing closer": "The bridge opened in 1932, highlighting the city's ambition. Attendance doubled that year, underscoring its importance. The park remains open, showcasing the region's beauty.",

  "split flip": "The problem isn't a lack of tools. It's that nobody reads the docs. The fix wasn't complicated. It's just tedious. This doesn't mean we stop. It's a pause.",

  "anaphora triads": "We came for the food, for the music, and for the company. It works where trust exists, where budgets allow, where teams commit. Success comes when you plan, when you test, when you ship.",

  "single anaphora triad is free": "It works where trust exists, where budgets allow, where teams commit. The rest of this passage is ordinary prose about a bicycle repair on a rainy Tuesday afternoon.",

  "ta-da openers": "Here's why this matters.\nSome content in between.\nHere's how it works.\nMore content here.\nHere's what to do next.",

  "fragment hooks": "We cut the budget in half. The result? Nothing broke. We asked users to pay more. The catch? They stayed. We shipped early. The best part? No bugs.",

  "sycophantic openers": "Great question! The answer is in the config file.\nAbsolutely! You can change that setting.\nOf course! Here is the command.",

  "despite arc": "Despite significant challenges in funding, the museum continues to attract visitors. Despite recent setbacks, the team continues to ship on schedule.",

  "staccato run": "We tried it. It broke. We fixed it. It broke again. Nobody panicked. The second attempt held, and the long weekend that followed gave everyone a chance to recover from the whole ordeal properly.",

  "bold inline spray": "The **key insight** here is that **most teams** never measure their **actual throughput** before making **sweeping changes** to process, and the **resulting chaos** gets blamed on the **wrong causes** entirely.",

  "bold paragraph leads": "**Speed.** We go fast and measure everything twice.\n\n**Quality.** We stay sharp and review every change.\n\n**Trust.** We deliver on the date we said.\n\n**Scale.** We grow without breaking what works.",

  "quote mixing": "She said “the deal is done” and then added ‘for now’ with a shrug. The contract says \"terminable at will\" in section 4, and the addendum uses 'ninety days' twice.",

  "header emoji": "# 🚀 Launch Plan\n\nThe plan is simple and boring on purpose.\n\n## 📚 Background\n\n- ✅ finish the docs\n- ✅ tag the release\n\nNothing else changes this week.",

  "question hooks": "We doubled the cache size. The gain? Four percent. We tripled it after that. The cost? Memory pressure everywhere. So we rolled it back to the old size.",

  "connective spray": "Moreover, the results were strong. Furthermore, costs fell. Additionally, the team grew. Notably, retention improved. Ultimately, the quarter closed well. Overall, a good year. The plain sentences continue here. They balance the count out. Nothing else is wrong with them.",

  "paragraph uniformity": "The first paragraph runs about twenty words when you count them all the way through to the end here.\n\nThe second paragraph also runs about twenty words when you count it all the way through to the end.\n\nThe third paragraph again runs about twenty words when you count it all the way through to the end.\n\nThe fourth paragraph still runs about twenty words when you count it all the way through to the end.\n\nThe fifth paragraph too runs about twenty words when you count it all the way through to the end now.",

  "opener repetition": "The server restarted at nine. The logs showed nothing unusual. The disk was half full. The network held steady all night. The backup completed on time. The monitoring stayed quiet. The morning shift found no issues. The incident was closed by noon.",

  "new buzzwords 2025": "This groundbreaking work garnered praise for its advancements, surpassing every benchmark. The design resonates with users and aligns with the roadmap, a diverse array of features bolstered by valuable insights that solidify its enduring legacy.",

  "significance inflation": "The building stands as a testament to the city's past, a pivotal moment in its history. The festival continues to thrive, setting the stage for future growth and paving the way for a new generation, cements its legacy among locals.",

  // ---- language packs: one slop + one clean fixture per pack, all of them
  // exercising detection, the per-language lists, and the em-dash factor
  // through both implementations at once ----

  "es slop": "En el vasto mundo del desarrollo de software, es importante destacar que nuestra plataforma integral aprovecha tecnología de vanguardia para ofrecer una experiencia fluida y sin fisuras. Sumérgete en un rico tapiz de posibilidades que te permitirá desbloquear todo tu potencial. No es solo una herramienta, es un cambio de paradigma que fomenta la innovación en el panorama digital actual. Cabe destacar que nuestro enfoque holístico transforma la manera en que navegas por las complejidades del trabajo moderno. ¡Espero que esto te ayude!",

  "es clean": "Ayer se me rompió la cadena de la bici a mitad del camino al trabajo. La arreglé con el tronchacadenas que llevo desde hace años y nunca había usado. Tardé veinte minutos y llegué con las manos negras de grasa, pero llegué. El mecánico del barrio me dijo después que la cadena ya tenía más de cinco mil kilómetros. Le compré una nueva ahí mismo.",

  "fr slop": "Dans le monde en constante évolution du numérique, il est important de noter que notre solution complète exploite une technologie de pointe pour offrir une expérience fluide et transparente. Plongez dans une riche tapisserie de possibilités qui vous permettra de libérer tout votre potentiel. Ce n'est pas seulement un outil, c'est un véritable changement de paradigme. Il convient de souligner que notre approche holistique transforme votre façon de travailler. N'hésitez pas à nous contacter !",

  "fr clean": "La boulangerie du coin a changé de propriétaire le mois dernier. Le nouveau fait le pain au levain lui-même, et franchement ça se sent. Par contre il ouvre à sept heures au lieu de six, ce qui m'a valu deux matins sans baguette avant que je comprenne. Le prix a pris dix centimes mais personne ne se plaint.",

  "de slop": "In der heutigen schnelllebigen digitalen Landschaft ist es wichtig zu beachten, dass unsere umfassende Plattform modernste Technologie nutzt, um ein nahtloses Erlebnis zu bieten. Tauchen Sie ein in ein reiches Geflecht von Möglichkeiten, das Ihnen ermöglicht, Ihr volles Potenzial zu entfesseln. Es ist nicht nur ein Werkzeug, sondern ein Paradigmenwechsel, der Innovation fördert. Ich hoffe, das hilft Ihnen weiter!",

  "de clean": "Der Aufzug im Haus ist seit Dienstag wieder kaputt. Diesmal ist es wohl die Steuerung, nicht die Tür wie im März. Die Hausverwaltung hat einen Zettel aufgehängt, auf dem steht, das Ersatzteil komme voraussichtlich nächste Woche. Ich nehme die Treppe und rede mir ein, das sei gut fürs Knie.",

  "pt slop": "No cenário digital em constante evolução de hoje, é importante ressaltar que nossa plataforma abrangente aproveita tecnologia de ponta para oferecer uma experiência fluida e perfeita. Mergulhe em uma rica tapeçaria de possibilidades que permitirá desbloquear todo o seu potencial. Não é apenas uma ferramenta, é uma mudança de paradigma que fomenta a inovação. Espero que isso ajude!",

  "pt clean": "O ônibus da linha 47 mudou de itinerário sem aviso nenhum. Descobri na segunda-feira, esperando vinte minutos num ponto onde ele não passa mais. Uma senhora que esperava comigo já sabia e me explicou o desvio novo, pela avenida do mercado. No fim o trajeto novo até que é melhor pra mim, mas podiam ter avisado antes.",

  "it slop": "Nel panorama digitale in continua evoluzione di oggi, è importante sottolineare che la nostra piattaforma completa sfrutta una tecnologia all'avanguardia per offrire un'esperienza fluida e senza soluzione di continuità. Immergiti in un ricco arazzo di possibilità che ti permetterà di sbloccare tutto il tuo potenziale. Non è solo uno strumento, è un cambio di paradigma. Spero che questo ti sia utile!",

  "it clean": "Il bar sotto casa ha finalmente sistemato la macchina del caffè. Erano due settimane che faceva un rumore strano, tipo un trapano, e il caffè veniva fuori tiepido. Il tecnico ha trovato una guarnizione andata, dieci euro di pezzo e mezz'ora di lavoro. Adesso il caffè è tornato quello di prima.",

  "nl slop": "In het snel veranderende digitale landschap van vandaag is het belangrijk om op te merken dat ons alomvattende platform geavanceerde technologie benut om een naadloze ervaring te bieden. Duik in een rijk tapijt van mogelijkheden waarmee je je volledige potentieel kunt ontgrendelen. Het is niet zomaar een hulpmiddel, het is een paradigmaverschuiving. Ik hoop dat dit helpt!",

  "nl clean": "De buurman heeft eindelijk zijn schutting gerepareerd, die sinds die storm in februari scheef hing. Hij heeft er drie zaterdagen over gedaan en twee keer nieuwe planken moeten halen omdat hij verkeerd gemeten had. Gisteren stond het ding recht en vanmorgen zat er alweer een kat bovenop.",

  // Greek has no pack (see the drop rationale in noslop.py's language notes)
  // so it's a clean, honest stand-in for "a real language this tool has
  // never heard of" - disjoint script from every pack here, ordinary
  // space-separated words so the word count still comes out sane.
  "greek fallback": "Χθες το βράδυ έσπασε η αλυσίδα του ποδηλάτου στον δρόμο για τη δουλειά. Το επισκεύασα με το εργαλείο που κουβαλάω εδώ και χρόνια αλλά δεν είχα ποτέ χρησιμοποιήσει. Μου πήρε είκοσι λεπτά και έφτασα με τα χέρια μαύρα από το λάδι, αλλά στην ώρα μου.",

  "french curly apostrophes": "Ce n’est pas seulement un outil, c’est un changement de paradigme. Il est important de noter que vous êtes entre de bonnes mains. N’hésitez pas à explorer toutes les options disponibles pour votre projet.",

  // ---- nine more language packs: ru, uk, pl, cs, tr, sv, ro, hu, fi ----

  "ru slop": "В современном мире важно отметить, что наша комплексная платформа использует передовые технологии, чтобы обеспечить поистине бесшовный опыт. Давайте погрузимся в мир безграничных возможностей, которые помогут раскрыть потенциал каждой команды. Это не только инструмент, но и полноценная экосистема, которая играет ключевую роль в трансформации бизнеса. Надеюсь, это поможет!",

  "ru clean": "Вчера вечером сломался холодильник на кухне. Компрессор гудел все громче, а потом затих совсем. Вызвал мастера, он приехал через два часа и сказал, что дело в реле. Заменили деталь, обошлось в полторы тысячи рублей. Теперь молоко снова холодное, а то я уже начал переживать за продукты в морозилке.",

  "uk slop": "У сучасному світі важливо зазначити, що наша комплексна платформа використовує передові технології, щоб забезпечити по-справжньому безшовний досвід. Давайте зануримося у світ, де на команди чекають безмежні можливості, які допоможуть розкрити потенціал кожного співробітника. Це не тільки інструмент, а й повноцінна екосистема, яка відіграє ключову роль у трансформації бізнесу. Сподіваюся, це допоможе!",

  "uk clean": "Учора ввечері зламався холодильник на кухні. Компресор гудів усе голосніше, а потім затих зовсім. Викликав майстра, він приїхав за дві години і сказав, що справа в реле. Замінили деталь, вийшло десь на півтори тисячі гривень. Тепер молоко знову холодне, а то я вже почав хвилюватися за продукти в морозилці.",

  "pl slop": "W dzisiejszym dynamicznie zmieniającym się świecie warto zauważyć, że nasza platforma jest kompleksowa, solidna i przełomowa. Zanurzmy się w świat możliwości i pomóżmy odblokować potencjał każdego zespołu. Szeroka gama nowych funkcji otwiera nowe możliwości dla każdego działu. To nie tylko narzędzie, ale i prawdziwy kamień węgielny naszej strategii cyfrowej. Dzięki temu jesteśmy na czele branży. Mam nadzieję, że to pomoże!",

  "pl clean": "Sąsiad w końcu naprawił płot, który krzywił się od tamtej burzy w lutym. Zajęło mu to trzy soboty i musiał dwa razy kupować nowe deski, bo źle zmierzył za pierwszym razem. Wczoraj płot stał już prosto, a dziś rano na górze siedział kot.",

  "cs slop": "V dnešním uspěchaném světě je důležité poznamenat, že naše platforma je komplexní, robustní a průlomová. Pojďme prozkoumat, co digitální krajina plná možností nabízí, a pomozme odemknout potenciál každého týmu. Nejen že šetří čas, ale i otevírá nové možnosti pro celou firmu. Hraje to klíčovou roli v naší strategii a nabízí nekonečné možnosti růstu. Doufám, že to pomůže!",

  "cs clean": "Včera večer se mi na kole přetrhl řetěz cestou domů z práce. Opravil jsem ho sponou, kterou vozím v brašně už roky a nikdy jsem ji nepoužil. Trvalo to dvacet minut a domů jsem dorazil s rukama od mazadla, ale včas. Později jsem zjistil, že řetěz měl najeto přes pět tisíc kilometrů, takže jsem si rovnou koupil nový.",

  "tr slop": "Günümüzün hızlı dünyasında önemle belirtmek gerekir ki platformumuz kapsamlı, sorunsuz ve bütünsel bir deneyim sunuyor. Hadi dalalım ve potansiyelinizi ortaya çıkarın! Bu sadece bir araç değil, aynı zamanda güçlü bir araç. Ekibinizi bir sonraki seviyeye taşıyın ve muhtemelen sonuçları hemen fark edeceksiniz. Yardımcı olması umarım!",

  "tr clean": "Dün akşam işe giderken bisikletin zinciri koptu. Bu, yıllardır çantamda taşıdığım ama hiç kullanmadığım bir pensle tamir edilebilecek bir sorundu. Yirmi dakika kadar sürdü ve ellerim yağdan simsiyah bir halde ofise vardım, ama yine de zamanında yetiştim. Ustaya sorduğumda zincirin beş bin kilometreden fazla yol yaptığını söyledi, ben de hemen yenisini aldım.",

  "sv slop": "Det är viktigt att notera att vår plattform, i dagens snabbrörliga värld, är omfattande, robust och banbrytande. Dyk djupare och frigör din potential! Detta är inte bara ett verktyg utan också en hörnsten i er digitala strategi. Det kan ofta kännas överväldigande, men det spelar en avgörande roll för att ta er till nästa nivå. Jag hoppas att detta hjälper!",

  "sv clean": "Igår kväll gick cykelkedjan av på väg hem från jobbet. Jag lagade den med verktyget jag haft i väskan i flera år men aldrig använt. Det tog tjugo minuter och jag kom hem med händerna svarta av fett, men i tid. Cykelverkstaden sa efteråt att kedjan redan hade gått över fem tusen kilometer, så jag köpte en ny på en gång.",

  "ro slop": "În lumea de azi în ritm alert, este important de menționat că platforma noastră este cuprinzătoare și revoluționară. Scufundă-te în oceanul de posibilități nelimitate și deblochează-ți potențialul! Nu doar că economisești timp, ci și deschizi noi orizonturi pentru echipa ta. O gamă largă de instrumente joacă un rol esențial în strategia noastră și reprezintă o piatră de temelie pentru viitor. Sper că te ajută!",

  "ro clean": "Aseară mi s-a rupt lanțul de la bicicletă pe drum spre casă de la serviciu. L-am reparat cu scula pe care o car de ani de zile și n-am folosit-o niciodată. Mi-a luat douăzeci de minute și am ajuns acasă cu mâinile negre de unsoare, dar la timp. Mecanicul mi-a spus apoi că lanțul avea deja peste cinci mii de kilometri, așa că mi-am cumpărat unul nou pe loc.",

  "hu slop": "Napjaink rohanó világában fontos megjegyezni, hogy platformunk átfogó, robusztus és forradalmi. Merülj el és szabadítsd fel a benned rejlő potenciált! Ez nem csak egy eszköz, hanem valódi mérföldkő a stratégiánkban. Kulcsszerepet játszik abban, hogy csapatod eljusson a következő szintre. Remélem, ez segít!",

  "hu clean": "Tegnap este elszakadt a bicikli lánca hazafelé menet a munkából. Megjavítottam azzal a szerszámmal, amit évek óta magamnál hordok, de sosem használtam. Húsz percig tartott, és olajos kézzel érkeztem haza, de időben. A szerelő később elmondta, hogy a lánc már több mint ötezer kilométert futott, úgyhogy rögtön vettem egy újat.",

  "fi slop": "Nykypäivän nopeatempoisessa maailmassa on tärkeää huomioida, että alustamme on kattava, saumaton ja mullistava. Sukella syvemmälle ja vapauta potentiaalisi! Tämä ei ole vain työkalu, vaan korvaamaton kulmakivi strategiassamme. Se on avainasemassa, kun viemme tiimisi seuraavalle tasolle. Toivottavasti tästä on apua!",

  "fi clean": "Eilen illalla polkupyörän ketju katkesi matkalla kotiin töistä. Korjasin sen työkalulla, jota olen kantanut mukana vuosia mutta en ollut koskaan käyttänyt. Se kesti kaksikymmentä minuuttia, ja pääsin kotiin kädet mustana rasvasta, mutta ajoissa. Korjaaja kertoi myöhemmin, että ketju oli jo ajanut yli viisi tuhatta kilometriä, joten ostin heti uuden.",

  // ---- the 0.9.0 tells: every new check gets a fixture through both engines ----

  "as an ai artifact": "As an AI, I don't have personal opinions on this, but here is what the report's numbers suggest about the quarter overall.",

  "knowledge cutoff artifact": "As of my last update, the population figure was around eight million, though that may well have shifted by now given how fast the city keeps growing year over year.",

  "no browsing artifact": "I don't have real-time access to the news, so I can't confirm today's headline directly, but here is how you'd check it yourself in under a minute.",

  "spanish ai self reference artifact": "Ayer se me rompió la cadena de la bici a mitad del camino al trabajo. Como modelo de lenguaje, no puedo verificar esto, pero la arreglé con el tronchacadenas que llevo desde hace años.",

  "german ai self reference artifact": "Der Aufzug im Haus ist seit Dienstag wieder kaputt. Als KI-Modell kann ich das nicht bestätigen, aber die Hausverwaltung hat einen Zettel mit dem Ersatzteil-Termin aufgehängt.",

  "low punctuation entropy": "this, ".repeat(35) + "and that is the end of it.",

  "varied punctuation entropy": "The plan: ship it. Then what? We'll see (probably fine) - but \"careful\" is the word; nothing's certain, not yet.",

  "single generic heading is free": "# Conclusion\n\nOne last plain paragraph about nothing in particular, long enough to read fine on its own.",

  "repeated generic headings score": "# Introduction\n\nSome plain opening text about the topic at hand.\n\n# Key Takeaways\n\nA few plain points about the topic.\n\n# Conclusion\n\nA plain closing paragraph about the topic.\n",

  "bold and colon stripped from heading": "## **Conclusion:**\n\nPlain text follows here in this paragraph.\n\n## Overview\n\nMore plain text follows this line here too.",

  "bare bullet glyphs": "Here is the plan:\n• Ship the fix\n• Write the test\n• Tell the team\n",

  "dash bullets are not bare bullets": "Here is the plan:\n- Ship the fix\n- Write the test\n- Tell the team\n",

  "copula avoidance below density gate": "The bridge serves as a crossing for the rail line, and it has done that job well for almost a century now without a single major structural repair.",

  "copula avoidance past density gate": "The report serves as a summary of the quarter. The chart stands as a record of the trend. The footnote functions as a caveat for the reader, and the appendix acts as a testament to how much detail was cut.",

  "stands as a testament not double counted": "The building stands as a testament to a century of the city's civic ambition and careful upkeep.",

  "scope inflation phrases": "Her contribution to the launch cannot be overstated, and the team felt it from the moment she joined the project full time.",

  "heading level skip": "# Title\n\n## Section\n\n#### Deep subsection\n\nPlain text follows this heading structure.",

  "no heading level skip": "# Title\n\n## Section\n\n### Subsection\n\nPlain text follows this heading structure fine.",

  "repeated paragraph openers": "Best for people who want speed above everything else in a tool.\n\nBest for people who want a simple setup with no configuration.\n\nBest for people who want to run this entirely offline and local.\n\nA closing paragraph that opens differently from the three above.\n\nOne more paragraph included just to clear the five-paragraph floor.",

  "varied paragraph openers": "The first paragraph opens with its own distinct sentence here.\n\nA second paragraph starts on a completely different note today.\n\nThen a third one takes yet another angle on the same subject.\n\nThe fourth continues without repeating any earlier opening words.\n\nAnd the fifth wraps up without echoing the others at all here.",

  "windowed ttr and function word ratio never score": ("word ".repeat(220)).trim() + ".",

  // A line-anchored opener regex used to let \s* cross newlines, so a run
  // of blank lines retried the same span at every line start (quadratic,
  // cubic for the ta-da opener) - see the noslop.py test of the same name.
  // Both engines have to be fast AND agree on the score.
  "line anchored openers do not blow up on blank lines": "\n".repeat(20000),

  // noslop.py's word tokenizer counts Nl/No characters (vulgar fractions,
  // superscripts, circled digits, Roman numerals) as word chars via
  // [^\W\d_] - detector.js only matched \p{L}, so the same text got a
  // smaller word count in JS and a different (sometimes verdict-flipping)
  // per-1k score for identical raw hits.
  "fraction and roman numeral glyphs count as words (Nl/No parity)":
    "This robust little recipe card still uses ½¼ ²③ Ⅻ½ ¼² ⅓⅔ ⅛⅜ ⅝⅞ ⅕⅖ ⅗⅘ ⅙⅚ ①② ③④ ⑤⑥ " +
    "notation from an old engineering table my grandmother kept in the drawer. " +
    "The oven ran a little warm that day. ".repeat(20),
};

// [text, lang] pairs: same diff, but with --lang forced on both sides.
const FORCED = {
  "forced es on english": ["The quick brown fox jumps over the lazy dog and keeps going for a while.", "es"],
  "forced en on spanish": ["El zorro marrón salta sobre el perro perezoso y sigue corriendo un buen rato más.", "en"],
  "forced de on german": ["In der heutigen schnelllebigen Welt ist es wichtig zu beachten, dass nahtlose Synergien entscheidend sind.", "de"],

  // Short single/two-sentence Russian fixtures below the auto-detector's
  // confidence floor (see detect_language() in noslop.py) - forced so the
  // fixture tests the intended pack instead of the English fallback.
  "russian bureaucratic determiner buzzword": ["Данный отчёт содержит краткое изложение результатов работы команды за прошедший квартал целиком и полностью.", "ru"],
  "russian opener cliche phrase": ["В эпоху цифровизации компании пересматривают свои процессы, чтобы оставаться конкурентоспособными на рынке услуг.", "ru"],
  "yavlyaetsya has an allowance": ["Совет является главным органом управления. Устав является основным документом организации в целом.", "ru"],
  "yavlyaetsya excess scores": [("Это является важным фактом, который является ключевым. ").repeat(6), "ru"],
  "yavlyayutsya plural not matched as singular crutch": ["Участниками этих отношений являются граждане и юридические лица, если иное не предусмотрено законом или уставом организации в целом.", "ru"],
  "russian ai self reference artifact": ["Как языковая модель, я не могу дать точный прогноз, но вот что показывают доступные данные по этой теме на сегодня.", "ru"],
};

let pass = 0, fail = 0;
const failures = [];
const cases = [];
for (const [name, text] of Object.entries(FIXTURES)) cases.push([name, text, null]);
for (const [name, [text, lang]] of Object.entries(FORCED)) cases.push([name, text, lang]);
for (const [name, text, lang] of cases) {
  let py, js, err = null;
  try {
    py = cliAnalyze(text, lang);
    js = Noslop.analyze(text, lang ? { lang: lang } : undefined);
  } catch (e) {
    err = e.message;
  }
  const d = err ? `error: ${err}` : diff(js, py);
  if (d) {
    fail++;
    failures.push({ name, d, js, py });
    console.log(`FAIL  ${name}`);
    console.log(`      ${d}`);
  } else {
    pass++;
    console.log(`ok    ${name}  (score ${js.score_per_1k}, ${js.verdict})`);
  }
}

console.log(`\n${pass} passed, ${fail} failed  (python: ${RUNNER.join(" ")})`);
if (fail) {
  console.log("\n--- first failure detail ---");
  const f = failures[0];
  console.log("js:", JSON.stringify(f.js, null, 2));
  console.log("py:", JSON.stringify(f.py, null, 2));
  process.exit(1);
}
