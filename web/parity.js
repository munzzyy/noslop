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

function cliAnalyze(text) {
  // --threshold 1e12 so the CLI always exits 0: it exits 1 on a high score by
  // design, which execFileSync would otherwise throw on. The score in --json
  // output is the same either way.
  const args = RUNNER.slice(1).concat([CLI, "--json", "--no-config", "--threshold", "1e12"]);
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
};

let pass = 0, fail = 0;
const failures = [];
for (const [name, text] of Object.entries(FIXTURES)) {
  let py, js, err = null;
  try {
    py = cliAnalyze(text);
    js = Unslop.analyze(text);
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
