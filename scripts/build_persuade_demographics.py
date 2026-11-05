"""Match our human essays to the public PERSUADE 2.0 release (Crossley et al., 2024, CC BY 4.0) and attach the writers' demographics.

Why: DAIGT-V2 carries no information about who wrote an essay; PERSUADE 2.0 does (English-learner status, grade, gender, race/ethnicity,
economic disadvantage, disability). Our `persuade_corpus` human essays ARE PERSUADE essays, so an exact text match recovers the labels.

Inputs: the two public files of https://github.com/scrosseye/persuade_corpus_2.0 (hosted on Google Drive, see that README):
  persuade_corpus_2.0_train.csv                        (~617 MB)
  persuade_corpus_2.0_test.csv, inside persuade_corpus_2.0_test.zip, password "persuade_test" (published in the README)
Usage:  python scripts/build_persuade_demographics.py --train /path/persuade_corpus_2.0_train.csv --test /path/persuade_corpus_2.0_test.csv
Output: data/external/persuade_demographics.csv  (git-ignored): row_id -> essay_id_comp, grade_level, gender, ell_status, race_ethnicity,
        economically_disadvantaged, student_disability_status. Matching is by exact text after collapsing whitespace.
Only aggregate results are committed; the per-essay mapping is not.
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data import load_deduped  # noqa: E402

COLS = ['essay_id_comp', 'full_text', 'gender', 'grade_level', 'ell_status', 'race_ethnicity', 'economically_disadvantaged', 'student_disability_status']
norm = lambda t: re.sub(r"\s+", " ", str(t)).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--train', required=True)
    ap.add_argument('--test', required=True)
    a = ap.parse_args()
    parts = []
    for path, name in ((a.train, 'train'), (a.test, 'test')):
        df = pd.read_csv(path, usecols=COLS, low_memory=False).drop_duplicates('essay_id_comp')
        df['persuade_set'] = name
        parts.append(df)
        print(f'{name}: {len(df):,} essays')
    P = pd.concat(parts, ignore_index=True)
    P['key'] = P['full_text'].map(norm)
    dup_keys = P['key'].duplicated(keep=False).sum()
    print(f'PERSUADE essays: {len(P):,}; essays sharing their text with another essay: {dup_keys}')
    P = P.drop_duplicates('key', keep='first').drop(columns=['full_text'])
    ours = load_deduped()
    h = ours[ours['label'] == 0].copy()
    h['key'] = h['text'].map(norm)
    m = h[['key', 'source', 'prompt_name']].reset_index().merge(P, on='key', how='left')
    ok = m['essay_id_comp'].notna()
    print(f'our human essays: {len(m):,}; matched {ok.sum():,} ({100 * ok.mean():.1f}%); by source:')
    print(m.groupby('source')['essay_id_comp'].apply(lambda s: round(100 * s.notna().mean(), 1)).to_string())
    out = ROOT / 'data' / 'external' / 'persuade_demographics.csv'
    out.parent.mkdir(parents=True, exist_ok=True)
    m[ok].drop(columns=['key']).set_index('row_id').to_csv(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
