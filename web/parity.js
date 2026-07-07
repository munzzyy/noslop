/*
 * parity.js - prove web/detector.js scores a piece of text identically to the
 * unslop.py CLI. Runs the JS analyze() and `py/python unslop.py --json` on the
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
const Unslop = require("./detector.js");

const CLI = path.join(__dirname, "..", "unslop.py");

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

  "cyrillic fallback": "Вчера сломалась цепь на велосипеде по дороге на работу. Починил её выжимкой, которую вожу с собой уже много лет и ни разу не использовал. Потратил двадцать минут и приехал с чёрными от смазки руками, но приехал вовремя.",

  "french curly apostrophes": "Ce n’est pas seulement un outil, c’est un changement de paradigme. Il est important de noter que vous êtes entre de bonnes mains. N’hésitez pas à explorer toutes les options disponibles pour votre projet.",
};

// [text, lang] pairs: same diff, but with --lang forced on both sides.
const FORCED = {
  "forced es on english": ["The quick brown fox jumps over the lazy dog and keeps going for a while.", "es"],
  "forced en on spanish": ["El zorro marrón salta sobre el perro perezoso y sigue corriendo un buen rato más.", "en"],
  "forced de on german": ["In der heutigen schnelllebigen Welt ist es wichtig zu beachten, dass nahtlose Synergien entscheidend sind.", "de"],
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
    js = Unslop.analyze(text, lang ? { lang: lang } : undefined);
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
