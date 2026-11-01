# The Ghost Writer API, in plain language

For the viva. Everything here is in `api/` (about 530 lines in 8 small files) and tested in `tests/` (37 tests, no GPU needed).

## Why there is an API at all

The models (DistilRoBERTa, the explainer, the attribution model, T5) are Python. A web page can't run Python, so a small server sits between them: the page sends an essay, the server runs the existing code in `src/`, and sends back numbers. **No model logic lives in the API.** It only checks the input, calls `src/`, and shapes the answer. If someone asks "where is the detector?", the answer is `src/detector.py`, the same file the notebooks and the Streamlit demo use.

It is built with **FastAPI**: each function with `@app.post("/api/...")` above it becomes an address the page can call. FastAPI also checks the shape of what arrives and writes the live documentation at `/docs`.

## The endpoints

| Endpoint | What it does | Uses |
|---|---|---|
| `GET /api/meta` | Everything the page needs to know before any essay: the two flag lines (+7.8 strict, +4.7 standard), the false-flag rates, the attack results, how many essays it trained on, the three built-in examples with their known labels. | Reads the results files (`results/09_*`, `13_attack.csv`, `14_errors.csv`, `splits.csv`, `demo/samples.json`) |
| `POST /api/score` | Scores one essay. Returns the score (a logit: higher means more AI-like), word and token counts, whether the essay was longer than the 512 tokens the model reads, and the character where reading stopped. | `src/detector.py` |
| `POST /api/explain` | Says how much each sentence pushed the score. Removes each sentence in turn and re-scores (occlusion); if no sentence moves the score (a very confident essay), it switches to integrated gradients instead. Same rule as the Streamlit demo. | `src/explain.py` |
| `POST /api/attribution` | The three training sources the essay most resembles. Always shown with the warning that for a source it never saw, it picks the right family only 0 to 28% of the time. | `src/attribution.py` |
| `POST /api/rewrite` | Changes the essay (typos in 5% or 10% of words, or a T5 paraphrase, light or heavy), then scores the new version. | `src/paraphraser.py`, then the detector |
| `POST /api/batch` | Takes many `.txt`, `.docx` or `.pdf` files (a class), reads the text out of each, scores each, and reports any file that couldn't be scored with the reason. | `textfiles.py`, then the detector |

**Why `/score` doesn't know about "strict" or "standard".** The server returns only the score. The two flag lines come from `/meta`, and the page compares the score to the line you picked. So flipping Strict/Standard needs no request and the flag line just slides.

**Why the typos use a fixed seed (42).** Notebook 13 measured the attacks with `SEED = 42`. Using the same seed means the button does what the notebook measured. Different seeds give different typos and can give different verdicts: on the "wrongly flags" example, seed 0 left the essay at +3.3 and seed 42 at −6.6. That is a finding, not a bug.

## What each file does

- **`main.py`**: the endpoints above. Each one does the same four things: check the rate limit, check the essay is acceptable, wait its turn for the model, call `src/`.
- **`settings.py`**: every number you could want to change (40-word minimum, the rate limit, file-size limits, the seed) in one place. Nothing is hidden in the code.
- **`results.py`**: **the reason no number on the page is invented.** It reads each figure from the project's CSV files. The "worst topic" (Summer projects, 7.7% at the standard line) isn't typed anywhere; it is calculated from `14_errors.csv` each time the server starts.
- **`errors.py`**: every failure has the same shape, `{"detail": "a sentence you can show", "code": "too_short"}`. The page shows `detail` as it is and uses `code` to decide what to do.
- **`uploads.py`**: keeps uploaded files off the disk (see "Are uploads saved?" below).
- **`textfiles.py`**: pulls plain text out of `.txt` (tries UTF-8, then Windows encoding), `.docx` (python-docx) and `.pdf` (pypdf). A scanned PDF has no text, so it is reported as "No text found". One bad file never stops the others.
- **`limiter.py`** and **`language.py`**: explained next.

## Versions: how the page knows the server matches it

`GET /api/meta` includes an `api_version` number (`api/settings.py`). The page is built for one version. If the server sends a different one the page does not guess: an older server (or one with no version) gets "The API is out of date. Restart it", a newer one gets "This page is out of date. Reload it". Separately, every sentence on the page that quotes a figure from `/api/meta` is built in one place (`frontend/src/lib/figures.js`) and simply leaves a clause out if its figure is missing, so a half-updated server never produces "undefined%" or a blank page.

## Are uploads saved? (`uploads.py`, tested in `tests/test_privacy.py`)

The class page promises "Scores are kept on this computer and cleared when you close the tab" and that files are read in memory and never saved. That had to be made true, because the framework underneath FastAPI (Starlette) normally keeps each uploaded file in memory only up to 1 MB and **writes it to a temporary file on disk above that**. Our limit per file is 5 MB, so a 3 MB essay would have been written to disk. Two things now prevent that:

1. The in-memory size is raised above anything we accept (`MultiPartParser.spool_max_size`), so no upload part ever rolls over to a file.
2. A request bigger than 20 MB is refused before it is read: by its `Content-Length` header, or, for a request that does not declare one, as soon as the bytes counted while it streams in pass the limit.

The tests prove it rather than assume it: a 3 MB upload stays in memory (a spy records zero roll-overs); the same upload with the framework default **does** roll over (so the first test would fail if the fix were removed); an oversized request gets a 413; nothing appears in the project or temp folder; and a marker word inside an essay never shows up in the log output. The browser keeps the scores and the extracted text in `sessionStorage`, which belongs to one tab and disappears when it closes (a new tab starts empty, and nothing is written to `localStorage` or cookies).

What we cannot show by test: server logs written by uvicorn contain only the address of each request (for example `POST /api/batch 200 OK`), never its body; that is how uvicorn works, not something we added.

## The class estimate: "about 3, probably between 0 and 7"

On the class page the sentence "you would still expect about N to cross it, probably between A and B" answers: *if every essay were honest student work, how many would the detector flag anyway?*

- **The mean.** Each honest essay is flagged with some small chance `p`: the false-flag rate on topics the model never saw (2.3% at Strict, 3.9% at Standard; they come from `results/09_threshold_rates.csv`). For `n` essays the expected count is `n x p`. A class of 130 at 2.3% gives 3.0.
- **The range.** The real count varies around that mean. If each essay is flagged independently with chance `p`, the count is a binomial; when `p` is small that is almost exactly a **Poisson** distribution with mean `n x p`. Its probabilities come one after another: `P(0) = e^-mean`, then `P(k+1) = P(k) x mean / (k+1)`. "Probably between" is the central 95%: from the smallest `k` where the chance of "k or fewer" reaches 2.5%, up to the smallest `k` where it reaches 97.5%. For a mean of 3 that is 0 to 7 (the chance of 7 or fewer is 98.8%, of 6 or fewer only 96.6%). For a mean of 16 it is 9 to 24. The code is `poissonInterval` in `frontend/src/lib/figures.js`, tested against these textbook values.
- **What it does not include.** It treats `p` as exactly known and the same for every essay. In truth `p` was measured on a finite set of essays and differs by topic (the worst unseen topic, Summer projects, was 5.2% at Strict and 7.7% at Standard), so the real range is wider than the one shown. The sentence names the worst topic for that reason.

## The demo class and how its 30 essays were picked

`demo/class_sample/` holds 30 essays whose real authors are known, so the class page can compare the detector's flags with the truth ("Known authors: 0 of the 19 student essays were flagged (at 2.3% we'd expect about 0.4), and 11 of the 11 AI essays were."). `demo/class_sample/make_class_sample.py` builds it, and gives the same class every time it is run:

1. **Never essays the model trained or tuned on.** Only the `heldout_prompt` split (a whole topic kept out of training and validation, notebook 03), and only the topic "Does the electoral college work?". A class writes on one topic, and an unseen topic is the situation the 2.3% / 3.9% figures describe.
2. **Student essays:** all of that topic's human essays. **AI essays:** only those really about that topic (`on_topic`, notebook 06: half the dataset's AI essays are off-topic for their label), and not from `train_essays`, which holds the dataset's few known mislabelled rows.
3. **The mix** follows the real ratio inside that split, 62.6% student: 30 x 0.626 = 18.8, so 19 student and 11 AI.
4. **Random draw, seed 42,** inside each group. No filter on length, and the detector's scores were never looked at.
5. **Shuffled, neutral names** (`essay_01.txt`...), so neither the order nor the name says who wrote it. `labels.json` records each essay's row in the dataset, its split, its source and its true label.

`tests/test_api.py` checks the claim against the project's own files: every essay is in the `heldout_prompt` split (not `train` or `val`), its text is exactly the dataset row, and its label is the dataset's label. **Caution for the viva:** the result on these 30 (no student essay flagged) is a demonstration, not a measurement. With 19 student essays, "0 flagged" is also consistent with a true rate of up to about 15%.

## `limiter.py`: why it exists

A public demo can be hammered by one visitor (or a script), and the model runs on one small GPU. The limiter keeps a list of each visitor's recent requests and refuses the next one if they have used 60 "units" in the last minute. It answers `429 Too many requests, wait N seconds`. Rules:

- Scoring, explaining and rewriting cost 1 unit. **A batch costs 1 unit per 10 files**, so checking a class of 28 costs 3 units, not 28.
- It is a function the endpoints call, not "middleware". That matters for two reasons: a batch can be charged by its file count (a middleware can't know it before reading the files), and the refusal travels through the same layers as every other reply, so the browser is allowed to read it. (The first version used middleware and the browser saw only "Failed to fetch". A test now covers it.)
- The limit is one number in `settings.py` (`GW_RATE_LIMIT` overrides it).
- Separately, **only one model call runs at a time** (a lock). A request that waits more than two minutes is told the detector is busy.

## `language.py`: why it exists

The detector only ever saw English school essays. Given French, it would still output a number, and the number would mean nothing, which is worse than no answer. So the API refuses first, and says why. It uses no model, in two steps:

1. **Script.** If less than 60% of the letters are Latin (Russian, Chinese, Arabic…), refuse and name the script.
2. **Function words.** In English prose about a third of words are small words like *the, of, and, to* (median 36% over 3,000 random essays from the dataset; the lowest was 17%). French has *le, la, des*; Spanish *el, los, que*. The check counts what share of the words fall in each language's list. If English is low *and* another language is higher, refuse and name that language ("This essay looks like French").

It leans towards scoring when unsure, because refusing a real English essay is worse than scoring a foreign one. Measured on all 44,866 essays in the dataset, it refuses **1**, a broken AI generation that is only "Passage 1: Passage 2:…". Its limits: very short, mixed-language or name-heavy text can fool it, which is rare in essays of 40+ words.

## Likely viva questions

- **Why FastAPI and not run Python in the page?** The browser can't run PyTorch; the server keeps the model loaded once instead of loading it for every visitor.
- **How do you know the numbers on the page are real?** They come from `/api/score` (the model) or `results.py` (the CSV files). A test (`test_results.py`) checks that the worst-topic figure is derived from the file, not typed in.
- **Why return scores and not "AI / human"?** The line is a choice: strict flags about 0.5% of student essays on familiar topics, standard 1%. The page needs the score to draw it.
- **What happens with two visitors at once?** The lock queues them; the limiter stops one from taking over.
- **Is the essay stored?** No. It is scored in memory and nothing is written or logged. A batch returns the extracted text so the page can reopen an essay; the server keeps nothing.
- **How is it tested without a GPU?** A fake detector (a few lines in `tests/conftest.py`) stands in for DistilRoBERTa, so the tests check the plumbing (validation, errors, limits, file reading). The real model is checked separately by running the server.
