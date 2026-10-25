"""Ghost Writer demo: run from the repo root with   streamlit run demo/app.py

Panels (decision 6, with the attribution decision of 2026-10-25):
1. Verdict: the fine-tuned DistilRoBERTa score against a threshold chosen on validation human essays (09).
2. Sentence highlights: occlusion; integrated gradients when occlusion is flat (14).
3. "Most similar training sources": only for flagged essays, always with the warning from 11.
4. Try to fool it: typos / T5 paraphrasing, then re-score. Works on human text too (13).
"""
import html
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")      # models are cached locally; never wait on the network

import numpy as np
import streamlit as st
import torch

st.set_page_config(page_title="Ghost Writer", page_icon="👻", layout="wide")


# ---------- models (loaded once per server process) ----------
@st.cache_resource(show_spinner="Loading the detector…")
def get_detector():
    import transformers
    transformers.logging.set_verbosity_error()
    from src.detector import Detector
    return Detector()


@st.cache_resource(show_spinner="Loading the attribution model…")
def get_attribution():
    from src import attribution
    return attribution.load()


@st.cache_resource(show_spinner="Loading the paraphraser (about 1 GB, first use only)…")
def get_t5():
    import transformers
    transformers.logging.set_verbosity_error()
    from src.paraphraser import T5Paraphraser
    return T5Paraphraser()


# ---------- helpers ----------
STRICT, STANDARD = 0.005, 0.01
SATURATED = 0.5          # if no sentence changes the score by more than this when removed, occlusion is flat (see 14)
MAX_SENTENCES_SHOWN = 80
MIN_SHARE = 0.10        # sentences below 10% of the strongest contribution get no background (a white box on a dark theme reads as the loudest)


def highlight_html(text, spans, scores, note_beyond):
    """Sentences coloured from white to orange by score. Opaque backgrounds with fixed dark text stay readable
    in light and dark themes; the number is also in the tooltip and in the table below (colour is never alone)."""
    pos = np.nan_to_num(scores, nan=0.0).clip(min=0)
    top = pos.max() if pos.max() > 0 else 1.0
    out, last = [], 0
    for (s, e), score in zip(spans, scores):
        out.append(html.escape(text[last:s]))
        piece = html.escape(text[s:e])
        if np.isnan(score):
            out.append(f'<span title="beyond the 512 tokens the detector reads" '
                       f'style="border-bottom:2px dotted #9a9a94">{piece}</span>')
        elif score / top >= MIN_SHARE:
            mix = (min(score / top, 1.0) - MIN_SHARE) / (1 - MIN_SHARE)
            r, g, b = (int(lo + (hi - lo) * mix) for lo, hi in zip((255, 232, 214), (240, 150, 100)))   # pale → strong orange
            out.append(f'<span title="contribution {score:+.2f}" style="background:rgb({r},{g},{b});color:#1f1f1d;'
                       f'padding:1px 2px;border-radius:3px">{piece}</span>')
        else:
            out.append(piece)
        last = e
    out.append(html.escape(text[last:]))
    return '<div style="line-height:1.8;white-space:pre-wrap">' + "".join(out) + "</div>"


def explain(det, text):
    from src.explain import occlusion, integrated_gradients
    spans, occ, logit = occlusion(det, text)
    valid = ~np.isnan(occ)
    if valid.any() and np.abs(occ[valid]).max() >= SATURATED:
        return spans, occ, "occlusion"
    _, ig, *_ = integrated_gradients(det, text)
    return spans, ig, "integrated gradients"


# ---------- sidebar ----------
with st.sidebar:
    st.header("Settings")
    mode = st.radio("How strict should the detector be?",
                    ["Strict: about 0.5% of human essays flagged", "Standard: about 1% of human essays flagged"], index=0)
    st.caption("These rates were measured on essays like the training ones. On new topics the real rate is higher "
               "(2–8% on prompts the detector had not seen).")
    st.divider()
    st.markdown("**Please read**\n\n"
                "- Course project for CSE472. **Do not use it to judge real students.**\n"
                "- It separates *student essays* from *2023-era AI essays*. It has never been tested on other kinds of writing.\n"
                "- The careful, fluent human writers are the ones it flags wrongly.\n"
                "- A flag is a reason to ask questions, not evidence.")

det = get_detector()
threshold = det.thresholds[STRICT if mode.startswith("Strict") else STANDARD]

# ---------- input ----------
st.title("👻 Ghost Writer")
st.caption("Did a student or an AI write this essay? Paste one, or load an example.")

samples = json.load(open(Path(__file__).parent / "samples.json"))
if "text" not in st.session_state:
    # a link like  ...:8501/?sample=0  opens with that example already loaded (handy for presenting)
    q = st.query_params.get("sample", "")
    st.session_state.text = list(samples.values())[int(q)] if q.isdigit() and int(q) < len(samples) else ""
cols = st.columns(len(samples))
for col, (label, body) in zip(cols, samples.items()):
    if col.button(label, use_container_width=True):
        st.session_state.text = body
        st.session_state.pop("fooled", None)
text = st.text_area("Essay", key="text", height=220, placeholder="Paste an essay (English, at least a few sentences)…")

if len(text.split()) < 40:
    st.info("Enter at least 40 words to get a result.")
    st.stop()

# ---------- 1. verdict ----------
logit = float(det.score([text])[0])
flagged = logit >= threshold
n_tokens = len(det.tok(text)["input_ids"])

st.subheader("1. What the detector says")
c1, c2, c3 = st.columns(3)
c1.metric("Score", f"{logit:+.1f}", help="Raw detector score (logit). Higher = more AI-like. Ranges from about -9 to +9.8.")
c2.metric("Flag threshold", f"{threshold:+.1f}")
c3.metric("Result", "AI-like" if flagged else "Not flagged")
if flagged:
    st.warning("This essay's style resembles the AI essays the detector was trained on. "
               "That is not proof: careful, well-structured human writing can score the same way.")
else:
    st.success("This essay's style is closer to the student essays the detector was trained on. "
               "That does not prove a human wrote it.")
if n_tokens > det.max_len:
    st.caption(f"The detector reads only the first {det.max_len} tokens; this essay has {n_tokens}.")

# ---------- 2. highlights ----------
st.subheader("2. Which sentences pushed the score up?")
if not flagged:
    st.write("No highlights, because the essay is not flagged. (Explanations of a 'not flagged' score are unreliable here: see notebook 14.)")
else:
    spans, scores, method = explain(det, text)
    if len(spans) > MAX_SENTENCES_SHOWN:
        st.caption(f"Long essay: highlighting the first {MAX_SENTENCES_SHOWN} sentences only.")
        spans, scores = spans[:MAX_SENTENCES_SHOWN], scores[:MAX_SENTENCES_SHOWN]
    if method == "occlusion":
        st.caption("Method: each sentence was removed in turn; darker = removing it lowers the score more.")
    else:
        st.caption("Method: integrated gradients. The AI-like style runs through the whole essay, so removing any one "
                   "sentence changes nothing. Darker = larger contribution to the score. "
                   "**The verdict is about the whole essay, not about these sentences.**")
    st.markdown(highlight_html(text, spans, scores, True), unsafe_allow_html=True)
    with st.expander("Scores per sentence (the highlighting as numbers)"):
        st.dataframe({"sentence": [text[s:e] for s, e in spans],
                      "contribution": [None if np.isnan(x) else round(float(x), 2) for x in scores]}, use_container_width=True)

# ---------- 3. attribution ----------
if flagged:
    st.subheader("3. Which kind of AI is it most similar to?")
    with st.expander("Show (read the warning first)"):
        st.error("**This cannot tell you which model wrote the essay.** When a whole data source was hidden from training, "
                 "this model picked the right family only 0–28% of the time, at or below chance. "
                 "It recognises how the *training essays were generated* (who prompted which model, with which instructions), "
                 "not the model itself. If the flag above is a false alarm, this panel means nothing either. See notebook 11.")
        from src import attribution
        for family, p in attribution.most_similar(get_attribution(), text, k=3):
            st.write(f"Most similar to training essays from **{family}**-based sources: {p:.0%}")
            st.progress(p)

# ---------- 4. try to fool it ----------
st.subheader("4. Try to fool it")
st.caption("Rewrite the essay and score it again. Try it on a human essay too: paraphrasing honest work can make it look more AI-like.")
ATTACKS = {"Typos in 5% of words": ("typos", 0.05), "Typos in 10% of words": ("typos", 0.10),
           "Paraphrase, light (T5, temperature 1.0)": ("t5", 1.0), "Paraphrase, heavy (T5, temperature 1.5)": ("t5", 1.5)}
choice = st.selectbox("Rewrite with", list(ATTACKS))
if st.button("Rewrite and re-score"):
    from src.paraphraser import inject_typos, words_changed
    kind, param = ATTACKS[choice]
    with st.spinner("Rewriting…"):
        edited = inject_typos(text, param, seed=0) if kind == "typos" else get_t5().paraphrase_essays([text], temperature=param, seed=0)[0]
    st.session_state.fooled = {"edited": edited, "logit": float(det.score([edited])[0]),
                               "changed": words_changed(text, edited), "choice": choice, "orig_logit": logit,
                               "orig_text": text, "threshold": threshold}

res = st.session_state.get("fooled")
if res and res["orig_text"] == text:
    now_flagged = res["logit"] >= res["threshold"]
    a, b, c = st.columns(3)
    a.metric("Score after", f"{res['logit']:+.1f}", f"{res['logit'] - res['orig_logit']:+.1f}", delta_color="off")
    b.metric("Words changed", f"{res['changed']:.0%}")
    c.metric("Result after", "AI-like" if now_flagged else "Not flagged")
    if flagged and not now_flagged:
        st.success("The rewrite got past the detector. Check below whether the essay still reads sensibly.")
    elif flagged and now_flagged:
        st.info("Still flagged. In our tests (notebook 13), typos and paraphrasing rarely changed the verdict "
                "unless they changed about half the words and damaged the text.")
    elif not flagged and now_flagged:
        st.warning("This human-looking essay is now flagged. Paraphrasing can make honest work look machine-written.")
    with st.expander("The rewritten text", expanded=True):
        st.write(res["edited"])
