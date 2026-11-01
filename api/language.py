"""A light "is this English?" check. No model, no dependency.

The detector was trained on English school essays, so a score for French or Chinese text would mean nothing. Two steps:
1. Script: if most letters are not Latin (Cyrillic, Chinese, Arabic ...), refuse and name the script.
2. Function words: share of words that are common English function words ("the", "of", "and" ...) against the same for
   French, Spanish, German, Italian and Portuguese. Refuse when English is low AND another language is higher.

It errs towards scoring: a refused English essay is worse than a scored foreign one. Limits: very short, mixed-language or
name-heavy text can fool it; those cases are rare among 40+ word school essays (see tests/test_language.py).
"""
import re
import unicodedata

from . import settings

_WORDS = {
    "English": "the of and to in is that it for as with was on be by are this not or have from they his at an which but he you i we their has had been were will would can more".split(),
    "French": "le la les un une des du de et est que qui dans pour pas sur au aux avec ce cette ces il elle nous vous ils elles je tu ne se son sa ses mais ou où été être ont très plus en".split(),
    "Spanish": "el la los las un una unos unas de del y es que en por para con no se su sus al lo como pero más muy este esta estos ya fue son".split(),
    "German": "der die das den dem des und ist nicht ein eine einer einen mit von zu auf für auch sich es im ich du er sie wir aber wie wird sind war".split(),
    "Italian": "il lo la i gli le un uno una di del della e è che in per con non si su come ma più anche sono questo".split(),
    "Portuguese": "o a os as um uma de do da dos das e é que em para com não se por mais como mas foi são".split(),
}
FUNCTION_WORDS = {lang: frozenset(words) for lang, words in _WORDS.items()}
_TOKEN = re.compile(r"[^\W\d_]+")


def _script_name(ch):
    first = unicodedata.name(ch, "").split(" ")[0]
    return {"CJK": "Chinese or Japanese", "HIRAGANA": "Japanese", "KATAKANA": "Japanese", "HANGUL": "Korean"}.get(first, first.title()) or "another"


def english_check(text):
    """Return None if the text may be scored, else a (code, message) pair to show the visitor."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "not_english", "There are no letters to read. Paste an English essay to score it."
    latin = sum(1 for c in letters if ord(c) < 0x250)       # Basic Latin through Latin Extended-B
    if latin / len(letters) < settings.MIN_LATIN_SHARE:
        other = next(c for c in letters if ord(c) >= 0x250)
        return "not_english", (f"This essay is written in {_script_name(other)} script. The detector only learned from English "
                               "school essays, so any score it gave here would mean nothing. Paste an English essay to score it.")
    words = [w.lower() for w in _TOKEN.findall(text)]
    if not words:
        return "not_english", "There are no words to read. Paste an English essay to score it."
    share = {lang: sum(w in fw for w in words) / len(words) for lang, fw in FUNCTION_WORDS.items()}
    english = share["English"]
    other_lang, other = max(((l, s) for l, s in share.items() if l != "English"), key=lambda x: x[1])
    if english >= settings.CLEAR_ENGLISH_SHARE:
        return None
    if other > english:
        return "not_english", (f"This essay looks like {other_lang}. The detector only learned from English school essays, "
                               "so any score it gave here would mean nothing. Paste an English essay to score it.")
    if english < settings.MIN_ENGLISH_SHARE:
        return "not_english", ("This doesn't look like English prose. The detector only learned from English school essays, "
                               "so any score it gave here would mean nothing.")
    return None
