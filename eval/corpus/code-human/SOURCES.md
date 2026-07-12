# Human code corpus sources

15 verbatim excerpts of genuinely human-written source code, used as the human half
of the code-mode eval. Every file is pinned to a pre-2021 tag or commit - written
before LLM code assistants were in circulation, so authorship isn't a guess. All
licenses are permissive; each excerpt keeps its upstream header where the slice
includes it, and this table is the attribution.

The picks are deliberately adversarial, not random: heavily commented tutorial code,
full-sentence comment discipline, JSDoc on trivial functions, imperative-mood body
comments, Google-style Args/Returns docstrings, and non-native-English comments are
each represented, because those are exactly the human habits an AI-code detector is
most tempted to flag.

| File | Project | Path @ pin | Year | License | Why it's here |
|------|---------|-----------|------|---------|---------------|
| 01-heapq.py | CPython | Lib/heapq.py @ v3.8.0 (first 170 lines) | 2019 tag; code from 2002 | PSF | Essay-length narrative comments |
| 02-flask-helpers.py | Flask | src/flask/helpers.py @ 1.1.2 (first 150) | 2020 | BSD-3 | Disciplined docstrings on everything |
| 03-requests-sessions.py | Requests | requests/sessions.py @ v2.25.1 (first 160) | 2020 | Apache-2.0 | Full-sentence comment style |
| 04-norvig-spell.py | Peter Norvig, pytudes | py/spell.py | 2007-2016 | MIT | Tutorial code by a famous explainer |
| 05-jquery-core.js | jQuery | src/core.js @ 1.12.4 (first 150) | 2016 tag; code from 2012 era | MIT | Imperative body comments ("Define a local copy of...") - the narration-check FP trap |
| 06-lodash-chunk.js | Lodash | lodash.js @ 4.17.15 (lines 6760-6960) | 2019 | MIT | Full JSDoc on tiny functions |
| 07-redis-sds.c | Redis | src/sds.c @ 6.0.0 (first 180) | 2020 | BSD-3 | Chatty full-sentence C comments |
| 08-kilo.c | antirez, kilo | kilo.c @ 69c3ce6 (first 200) | 2016 | BSD-2 | Step-by-step teaching comments |
| 09-go-strings.go | Go | src/strings/strings.go @ go1.15 (first 150) | 2020 | BSD-3 | Terse stdlib doc comments |
| 10-ripgrep-args.rs | ripgrep | src/args.rs @ 0.10.0 (first 150) | 2018 | MIT/Unlicense | Modern Rust, doc comments |
| 11-rbenv.sh | rbenv | libexec/rbenv @ v1.1.2 | 2017 | MIT | Real-world shell, sparse comments |
| 12-flaskr-schema.sql | Flask tutorial | examples/tutorial/flaskr/schema.sql @ 1.1.2 | 2019 | BSD-3 | Plain human SQL DDL |
| 13-guava-strings.java | Guava | .../base/Strings.java @ v29.0 (first 150) | 2020 | Apache-2.0 | Javadoc with @param on small methods |
| 14-tensorflow-checkops.py | TensorFlow | tensorflow/python/ops/check_ops.py @ v1.15.0 (lines 100-260) | 2019 | Apache-2.0 | Google-style Args:/Returns: docstrings - the docstring-check FP trap |
| 15-vue-observer.js | Vue.js | src/core/observer/index.js @ v2.6.11 (first 160) | 2019 | MIT | Non-native-English author comments - the register the Stanford ESL bias research warns about |

All fetched from `raw.githubusercontent.com` at the pins above. Excerpts are
contiguous slices (a `head`/`sed` range of the real file), never stitched or edited.
