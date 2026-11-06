"""An offline spelling corrector for 17_augment.ipynb (no new dependency).

It is the classic Norvig corrector, built on the GloVe vocabulary that notebook 14 already uses to *measure* misspellings.
That makes "misspelled" mean the same thing when we measure it and when we repair it.

  1. A word is a candidate for repair only if it is NOT in the 400k-word GloVe vocabulary (the same test as notebook 14's misspell_pct).
  2. Candidates are the words one edit away (delete, swap, replace or insert one letter) among the alphabetic GloVe words; the most
     frequent one wins. For long words (8+ letters) with no such neighbour, two edits are tried, only among the 100k most frequent
     words and only if they keep the first letter.
  3. Short words (under 4 letters) are never touched, and nothing is changed when no candidate exists.
  4. Transpositions ("casue" -> "cause") are tried first, since swapped letters are the commonest slip; then, among the other
     candidates, those that keep the first letter win (people seldom mistype the first letter: "vaction" is "vacation",
     not "action"). Capitalised words in the middle of a sentence are skipped (names), and common contractions typed without the
     apostrophe ("dont", "shouldnt") are mapped to their proper form instead of to a nearby unrelated word.
GloVe's vocabulary file is ordered by frequency, so a smaller index means a more frequent word.
"""
import re
import string

LETTERS = string.ascii_lowercase
WORD = re.compile(r"[A-Za-z]+")
# contractions typed without the apostrophe; apostrophe-less forms that are real words ("were", "its", "well", "ill", "id", "wed",
# "hell", "lets", "shell") are left out on purpose, because they are usually correct as written
_REAL_WORDS = {"were", "its", "well", "ill", "id", "wed", "hell", "lets", "shell", "hed", "shed"}
CONTRACTIONS = {w.replace("'", ""): w for w in (
    "don't doesn't didn't isn't aren't wasn't weren't hasn't haven't hadn't won't wouldn't shouldn't couldn't can't mustn't "
    "could've would've should've must've i'm you're they're we're he's she's that's there's what's i've you've we've they've "
    "i'll you'll we'll they'll i'd you'd we'd they'd").split() if w.replace("'", "") not in _REAL_WORDS}


def _swaps(w):
    return {w[:i] + w[i + 1] + w[i] + w[i + 2:] for i in range(len(w) - 1)}


def _edits1(w):
    splits = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    swaps = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits if b for c in LETTERS]
    inserts = [a + c + b for a, b in splits for c in LETTERS]
    return set(deletes + swaps + replaces + inserts)


class SpellCorrector:
    def __init__(self, top2=100_000, kv=None):
        if kv is None:
            import gensim.downloader as api
            kv = api.load('glove-wiki-gigaword-100')
        keys = kv.index_to_key
        self.vocab = set(keys)                                               # "is this a real word?" (same test as notebook 14)
        self.rank = {w: i for i, w in enumerate(keys) if w.isalpha()}        # candidates to repair to (one edit), by frequency
        self.rank2 = {w: i for w, i in self.rank.items() if i < top2}        # candidates for two-edit repairs
        self._cache = {}
        self.vocab_contractions = set()                                     # contractions we always map (even if GloVe happens to hold them)

    def _repair(self, w):
        """Lower-case repair of a lower-case word, cached (the same misspellings come up again and again)."""
        if w in self._cache:
            return self._cache[w]
        best = None
        swaps = [c for c in _swaps(w) if c in self.rank and c[0] == w[0]]
        c1 = [c for c in _edits1(w) if c in self.rank]
        same_first = [c for c in c1 if c[0] == w[0]]
        pool = swaps or same_first or c1
        if pool:
            best = min(pool, key=self.rank.get)
        elif len(w) >= 8:
            c2 = [c for e in _edits1(w) for c in _edits1(e) if c in self.rank2 and c[0] == w[0]]
            best = min(c2, key=self.rank2.get) if c2 else None
        self._cache[w] = best
        return best

    def correct_word(self, word, sentence_start=True):
        """The repaired word, or None when the word is fine or cannot be repaired."""
        w = word.lower()
        if w in CONTRACTIONS and w not in self.vocab_contractions:
            best = CONTRACTIONS[w]
        else:
            if len(w) < 4 or w in self.vocab or word.isupper() or (word[0].isupper() and not sentence_start):
                return None
            best = self._repair(w)
        if best is None:
            return None
        return best.capitalize() if word[0].isupper() and not word.isupper() else best.upper() if word.isupper() and len(word) > 1 else best

    def correct_text(self, text):
        """(new text, number of words changed, list of (before, after))."""
        changes = []

        def fix(m):
            before = text[:m.start()].rstrip()
            new = self.correct_word(m.group(0), sentence_start=(not before) or before[-1] in '.!?"\'')
            if new is None:
                return m.group(0)
            changes.append((m.group(0), new))
            return new
        return WORD.sub(fix, text), len(changes), changes
