# eval - does the detector actually detect?

A labeled corpus and a scorer that measure noslop against ground truth, so
"improved detection" is a number, not a feeling.

## The corpus

- `corpus/ai/` - 19 samples written by an LLM asked for ordinary content
  (blog post, product copy, tutorial, cover letter...) with **no** style
  instructions beyond picking a genre likely to exercise a given check (the
  three 0.9.0 additions - see `MANIFEST.md`). Nobody stuffed tells into
  these; they are what default assistant prose looks like.
- `corpus/human/` - 17 samples people wrote before LLMs existed, plus one
  genuinely public-domain modern text: essays, fiction, journalism,
  letters, manuals, early open-source docs, and a Russian statute excerpt
  (added in 0.9.0 to guard the new Russian buzzword/density checks against
  flagging real formal Russian). All public domain or permissively
  licensed, sourced and dated in `SOURCES.md`.

Small on purpose. This is a calibration set for a heuristic linter, not a
benchmark for publishing claims - 36 samples is enough to catch "this change
flags Mark Twain as a robot" before it ships, which is the job.

## Run it

    py eval/run_eval.py           # table of every sample + summary
    py eval/run_eval.py --json    # machine-readable
    py eval/run_eval.py --check   # CI mode: exit 1 if a floor is broken

## What CI enforces

`run_eval.py --check` runs in CI with floors on AUC, detection rate at the
"worth a pass" threshold (10/1k), and false-positive rate on the human half.
A change that buys recall by flagging human prose fails the build. The floors
sit below the currently measured numbers (see the table below) so routine
drift passes and only a real regression trips.

## Measured state (v0.9.0)

Filled in per release by running the scorer; CI keeps it honest. v0.9.0 adds
four corpus samples (three AI, one human) alongside the new detectors, so
its numbers aren't directly comparable sample-for-sample to earlier rows -
see `MANIFEST.md` / `SOURCES.md` for what's new and why.

| metric | v0.6.0 engine | v0.7.0 engine | v0.9.0 engine (32→36 samples) |
|---|---|---|---|
| AUC | 0.80 | 0.97 | 0.9752 |
| detection @10 ("worth a pass") | 38% | 88% | 89.5% |
| detection @25 ("reads as AI") | 6% | 19% | 36.8% |
| human FP @10 | 6% (one sample) | 6% (the same sample) | 5.9% (the same sample, larger denominator) |
| human FP @25 | 0% | 0% | 0% |

The AI samples still under 10 are the long, careful essay-register pieces -
the class the README's limitations section already owns up to. An earlier
build of this engine caught those two as well, at the price of flagging
ordinary human email closers, short non-native academic essays, and terse
fiction; the review pass that caught those false positives cost a few
recall points, and that trade is the right one for a linter.

The one human sample over 10 - on every engine so far - is Thoreau's
*Walden* at 16.8: he uses "landscape" twice meaning an actual landscape,
and em-dashes the way 1854 prose does. That's the known cost of vocabulary
tells, and "worth a pass" is the soft verdict on purpose - no human sample
reaches the hard one on any engine, including the new Russian statute
excerpt added this pass (0.0 - see below).

### What's new in 0.9.0

Ten new detectors (chatbot disclaimer phrases at the artifact floor,
punctuation-entropy, generic listicle headings, bare bullet glyphs,
copula-avoidance and scope-inflation phrasing, a heading-level-skip
diagnostic, cross-paragraph opener repetition, windowed type-token/
function-word diagnostics, and a set of Russian-specific additions) were
each run through this eval before and after landing. Three moved a number:

- The chatbot-disclaimer artifact promotion and the new bare-bullet/
  generic-heading checks pushed `07-listicle-travel.txt` and the three new
  AI samples well past the hard verdict, which is most of the detect@25
  jump from 19% to 37%.
- To isolate the engine from the corpus change: on the original 32-sample
  corpus alone, AUC and detection@10 are unchanged from v0.7.0 (0.9688 /
  87.5%) - those two headline numbers move only because of the 4 new
  samples. The one engine-driven gain on the old corpus is detection@25,
  18.8% to 25.0% (`07-listicle-travel.txt` crossing the hard verdict).
- Nothing moved the human side. The formal-Russian sample
  (`17-law-civil-code-ru.txt`) scores 0.0 - none of the new Russian
  buzzword/"является"-density additions fired on it, because Russian's
  case and verb-conjugation endings mean a bare-stem match like
  `является` doesn't match its own plural `являются` or a noun's genitive
  form. That's a real limitation (an inflected AI sample could slip past
  the same way a clean one does here), traded deliberately for not flagging
  ordinary formal Russian - see the comments on `density_crutch` in
  `noslop.py`.
- The windowed-TTR and function-word-ratio diagnostics, and the
  heading-level-skip diagnostic, are report-only by design (see the
  README's "What it checks" section) - they show up in `--json` but never
  move `score_per_1k`, so they don't appear in this table at all.

No signal that was tried and hurt AUC or the FP ceilings shipped scored;
the task list this pass didn't produce one, but that's the standing rule
for anything added here going forward.

A real caveat about the AI half: it was generated by one model family at
default settings. Text from other models, other decades, or prompted to
"sound human" will score differently. These numbers say the tells fire on
unedited assistant prose and stay quiet on human writing - not that noslop
is an AI detector. It isn't; it's a linter.
