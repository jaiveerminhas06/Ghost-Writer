# Viva demo: five minutes, click by click

Written for Jaiveer to run the web app in front of examiners. Every score below was read from the running app (the typo edits use a fixed seed, so you get the same ones). If a number on screen differs from this page, say what is on screen.

## Before you go in (10 minutes early)

```bash
bash scripts/demo.sh
```

That one command builds the page if it is missing or out of date, starts one server that serves page and API together, loads every model once (about 30 seconds the first time, then the first click is as fast as the tenth), and opens http://localhost:8000. It prints `Ready: http://localhost:8000` when it is done. Ctrl+C stops it.

- Close other GPU programs first (4 GB card). Do not start the Streamlit demo at the same time.
- **Check free RAM with the slides and the browser open** (`free -h`, the "available" column). The jury keeps all 20 detectors in memory, about 6.7 GB for the whole server. If less than about 2 GB is free after the server has started, or the machine starts swapping, restart with `GW_JURY_LAZY=1 bash scripts/demo.sh`: the detectors are then read from disk when needed and nothing is kept, which saves about 3 GB and makes one trial take about 4 seconds instead of 0.8 (the first one after a restart is slow either way).
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

Every number below was read from the running app (the typo edits use fixed seeds, so you get the same ones). If the screen differs, say what is on screen.

**0:00 — The AI essay and the jury** (45 s)
Click **AI essay by Claude** in the Examples list. The twenty marks drop in one by one; the official marker lands last. Headline: "Flagged. Higher than every student essay we checked. That isn't proof." All 20 marks sit in the **Off the scale** box: say "the scale ends at 'higher than all 2,291 student essays we checked'. That is a limit, not a measurement, which is why the marks are stacked in a box and their order means nothing."
Say: "One scale for everything: how many of the 2,291 student essays we checked score this high or higher. The official verdict is three of these twenty detectors combined; the other seventeen show how far to trust it. All twenty were trained on the same essays with the same method; only the random seed differs."

**0:45 — The sentences that moved it** (30 s)
Scroll to the essay. Yellow marks show which sentences moved the score. Say: "These highlights come from one detector, seed 42, not the whole jury; the page says so." If the marks are faint, say this essay is flagged throughout (the score saturates).

**1:15 — A student essay** (20 s)
Click **Student essay**: "Not flagged. About 1 in 7 student essays score this high or higher." 0 of 20 flag it. Say: "It never says 'this reads like a student's'. Not flagged is not proof of who wrote it."

**1:35 — The limit, shown honestly** (60 s: the 60-second jury moment)
Click **Student essay the final system still flags**. It is a real student essay from a held-out topic (Summer projects). All 20 detectors flag it, the note says "A real student essay that the final system gets wrong." Say: "Unanimous and wrong. Twenty detectors agreeing is not proof, because they share their training data."
Press **Re-run the trial**. The marks travel to new places. The headline becomes "After typos: Above usual. Higher than most student essays, but most essays that score here are written by students (about 7 in 10 at a one-third AI share, about 9 in 10 at 10%)." The panel reads: "Typos in 15 of 392 words. 19 of 20 detectors changed their mind; the official verdict moved from flagged to above usual." Then: "This is a student's essay, and the same kind of small edit that cleared it also lets AI essays slip through."
Read the general figures: "Light typos removed the flag from 2.6% of flagged AI essays in our tests, and from 28.9% of essays from AI models the detectors had not seen. Most of those moved to 'above usual'. That zone also holds 2.6% of student essays on new topics, and rewording tools push some students there too, so 'above usual' means 'look closer', not 'AI'." Press **Show original** to go back.

**2:35 — Before and after, and a split jury** (45 s)
Click **Student essay the earlier detector flagged**. The earlier single-model detector flagged it (+9.1 on its old ruler). On the final system 2 of 20 detectors flag it, 16 put it in "above usual" and the verdict is "above usual": the before-and-after. Click **AI essay that splits the jury**: 10 of 20 flag it and the note reads "The detectors disagree. That means the jury is less sure. It doesn't tell you who wrote the essay." Say: "A split means less sure, never 'probably a student'." Press **Re-run the trial** once: 13 of 20 change their mind and the verdict moves from above usual to not flagged. This essay was written by an AI model.

**3:20 — Try to fool it** (45 s)
Click **Try to fool it**. Choose **Typos in 5% of words**, press **Rewrite and re-score**: the page names the verdict before and after and keeps every attempt with its seed. Say: "On the final system, 5% typos removed the flag from 2.6% of flagged AI essays on familiar topics, but from 28.9% for AI models it had never seen. That is the price of the strict line: it cut student false flags about fivefold on new topics. The older numbers, 98.9% still caught under 10% typos, belong to the earlier single model and its old threshold."

**4:05 — Check a class** (60 s)
Click **Check a class**, then choose **Summer projects**. Wait for "Scoring 30 of 30 files" to finish. Result: "11 of 30 essays are flagged, 2 more are above usual." Known authors: "0 of the 19 student essays were flagged and 2 were above usual; 11 of the 11 AI essays were flagged." Point out the new column **Jurors flagging** (for example 20 of 20, 0 of 20) and the strip: it is the same scale as the essay page, with the "Off the scale" box and its count. Flagged essays show "None of 2,291" in the table. Say: "If all 30 were students you would still expect fewer than one flagged and about one more in 'above usual'."
Then **Does the electoral college work?**: 11 of 11 AI essays flagged, none of the 19 students. Say: "I show both because showing only this one would flatter the detector." Both classes were picked before any score was seen.

**5:05 — Close** (15 s)
Say: "What I would not claim: it works on non-native writers, adults, newer models, or partly AI-written essays. Nobody has measured that. The model card says so." (This list is on the Check an essay page, bottom.)

## If the API is slow

- First request after a restart: the twenty detectors take about 11 s to load (the warm-up in `demo.sh` does this for you). If you skipped it with `NO_WARMUP=1`, say "it loads the detectors on the first request" and keep talking through the scale.
- One trial takes under a second on the GPU. With `GW_JURY_LAZY=1` it takes about four seconds: say what the marks mean while they arrive.
- **T5 paraphrase** takes a few seconds even warm, and the heavy one longer. Start it, then explain what it is (a T5-base trained on the PAWS paraphrase set, not on ChatGPT output) and come back. Do not click again: the button is disabled while it works.
- The server runs one model call at a time. If two requests collide, the second waits; the page shows a skeleton while it does.
- If a request fails the page says so in one line and keeps your essay; press the button again. Rate limit is 60 units a minute (a trial costs 3, a score 1): clicking Re-run twenty times in a minute would hit it, which you will not do by hand.
- On a machine without a GPU the live jury is not available. The built-in examples still work from precomputed results and the page says so; a pasted essay shows the official verdict with a note that the live jury needs the GPU.
- If T5 is unavailable (model files missing) the card says so; use the typos cards instead.

## Questions you are likely to get

See "Likely viva questions" at the end of `docs/api.md` (why an API, why a limiter, why the language check, what "kept on this computer" means) and the Key takeaways cell of each notebook for the modelling questions.
