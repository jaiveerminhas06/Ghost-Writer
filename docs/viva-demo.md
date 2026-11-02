# Viva demo: five minutes, click by click

Written for Jaiveer to run the web app in front of examiners. Every score below was read from the running app (the typo edits use a fixed seed, so you get the same ones). If a number on screen differs from this page, say what is on screen.

## Before you go in (10 minutes early)

```bash
bash scripts/demo.sh
```

That one command builds the page if it is missing or out of date, starts one server that serves page and API together, loads every model once (about 30 seconds the first time, then the first click is as fast as the tenth), and opens http://localhost:8000. It prints `Ready: http://localhost:8000` when it is done. Ctrl+C stops it.

- Close other GPU programs first (4 GB card). Do not start the Streamlit demo at the same time.
- Switch the browser to a light theme and zoom to 100%. Open the page once and check it shows the headline "Did a student or an AI write this essay?".
- Have a second tab on `docs/api.md` ready for the "why an API" question.

### If it fails in the room

| What you see | What to do |
|---|---|
| `Something is already answering on http://localhost:8000` | An old server is running. Open the page anyway if it loads; otherwise `PORT=8010 bash scripts/demo.sh`. |
| Page says "The API is out of date, restart it" | Ctrl+C the script and run it again. |
| `The server stopped` and a Python error | Read the last line. Usually the GPU is busy (`nvidia-smi`) or a model file in `models/` is missing (notebooks 08 and 09 create them). Try `CUDA_VISIBLE_DEVICES= bash scripts/demo.sh` to run on CPU (the code falls back to CPU; slower, and not tried with this page). |
| No page at all, no time to debug | Show the saved screenshots in `images/` and the README results table, and walk through the notebooks instead. The modelling does not depend on the page. |
| Old Streamlit fallback | `streamlit run demo/app.py` (does the same job with fewer panels). Do not run it alongside the API. |

## The path

**0:00 — Check an essay, the AI essay** (30 s)
Click **AI essay by Claude** in the Examples list. The score appears on the ruler: **+9.7**, past the **+7.8** flag line, so "Flagged".
Point out: the ruler, not a percentage. The headline says "reads like the AI essays I was trained on, but that isn't proof". Claude is a model family the detector never saw in training. Say: "The score is a log-odds number; the flag line was chosen on validation data to allow about 0.5% of student essays through."

**0:30 — The sentences that moved it** (30 s)
Scroll to the essay. Yellow marks show which sentences moved the score; the margin notes say which one it leans on most. Say: "Each sentence was deleted in turn and the essay re-scored; the bigger the drop, the darker the mark." If the marks are faint, say that this essay is flagged throughout (the score saturates near +9.8), so no single sentence matters much; the app falls back to integrated gradients for those.

**1:00 — A student essay** (30 s)
Click **Student essay**: **−7.9**, "Not flagged", no marks. Say: "The same page, the other side of the line."

**1:30 — The honest failure** (60 s)
Click **Student essay it wrongly flags** (+9.1). Point out the note: "This example was written by a student." Say: "This is a real human essay from the test set. It is careful and fluent, and the detector flags it. At the strict line about 2.3% of student essays on topics it never saw were flagged, and on the worst topic (Summer projects) 5.2%. These numbers are in the box under the ruler and come from the results files, not from me." Switch **Strict / Standard** to show the line move (+7.8 to +4.7): same essay, still flagged.
Then say: "The residual false positives are longer and more polished than average. That is a fairness problem, and it is why a flag is a reason to ask questions, not evidence."

**2:30 — Try to fool it** (90 s)
Click **Try to fool it** on that essay. Choose **Typos in 5% of words**, press **Rewrite and re-score**.
Result: **+9.1 to −6.6**, not flagged, with 9 of 209 words changed. Say: "Nine misspellings took a flagged human essay below the line. The model reads polish as machine, so mistakes read as human. A pass is no proof of a human either." Press **Try different typos** once to show it is a seeded random edit (the seed is in the table).
Then go back to the Claude essay (Check an essay, Claude example, Try to fool it) and run **Typos in 10%**: **+9.7 to +9.3**, still flagged. Run **Paraphrase with T5** (about 15% of words changed): **+9.7**, unchanged. Say: "Typos and a pretrained paraphraser barely move a clearly machine essay. Across the test set 98.9% of AI essays are still caught with 10% typos and 96.4% after the heavy T5 paraphrase. I did not test LLM 'humaniser' rewriting."

**4:00 — Check a class** (60 s)
Click **Check a class**, then **Load the demo class**, choose **Does the electoral college work?**.
Result: **11 of 30 essays cross the flag line**. Point out the sentence "Known authors": **0 of the 19 student essays were flagged, 11 of the 11 AI essays were**. Say: "These 30 essays come from a topic held out of training, never from the training split. The selection rule is fixed in code (seed 42, the real student-to-AI ratio) and I did not choose them by score." If asked about the other topic: **Summer projects** gives 13 of 30, with 2 of the 19 student essays flagged: the same method, the worse result, shown anyway.
Point out the expected-false-flags sentence: "If all 30 were students, about one would be flagged, probably between 0 and 3" (exact Poisson interval, explained in `docs/api.md`).

**4:45 — Close** (15 s)
Say: "What I would not claim: it works on non-native writers, adults, newer models, or partly AI-written essays. Nobody has measured that. The model card says so." (This list is on the Check an essay page, bottom.)

## If the API is slow

- First request after a restart: the detector takes about 10 s to load (the warm-up in `demo.sh` does this for you). If you skipped it with `NO_WARMUP=1`, say "it loads the model on the first request" and keep talking through the ruler.
- **T5 paraphrase** takes a few seconds even warm, and the heavy one longer. Start it, then explain what it is (a T5-base trained on the PAWS paraphrase set, not on ChatGPT output) and come back. Do not click again: the button is disabled while it works and a second click would only queue.
- The server runs one model call at a time. If two requests collide, the second waits; the page shows a skeleton while it does.
- If a request fails the page says so in one line and keeps your essay; press the button again. Rate limit is 60 requests a minute, which you will not reach by hand.
- If T5 is unavailable (model files missing) the card says so; use the typos cards instead.

## Questions you are likely to get

See "Likely viva questions" at the end of `docs/api.md` (why an API, why a limiter, why the language check, what "kept on this computer" means) and the Key takeaways cell of each notebook for the modelling questions.
