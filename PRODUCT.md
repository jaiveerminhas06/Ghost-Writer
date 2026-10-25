# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Professor and viva examiners for CSE472 (Deep Learning for NLP), who will paste essays and probe how the detector decides and where it fails. Recruiters reading the resume, who spend under a minute and want to see it work. Both read English essays; neither is a machine-learning expert by default.

## Product Purpose
Ghost Writer decides whether a student essay was written by a person or an AI, and shows why: a verdict, the sentences that drove it, and a live "try to fool it" test. Success is that a visitor understands the verdict, sees its evidence, and trusts the project's honesty about its limits.

## Positioning
The first version reported a fake 100% accuracy; the rebuild reports leakage-safe numbers and shows its own failure modes (false positives on polished human writing, attribution that fails on unseen sources). It explains rather than only labels.

## Capabilities and Constraints
Fine-tuned DistilRoBERTa detector with a strictness setting (0.5% or 1% false-positive target). Sentence highlights by occlusion, or integrated gradients when occlusion is flat. "Most similar training sources" panel, only for flagged essays, always with the 0-28% held-out warning. "Try to fool it": typos 5/10% and T5 paraphrase light/heavy, with before/after score. Highlights can take up to a minute on CPU. Essay text is not stored or logged. Code must stay small and plain: the student explains every line in a viva, no heavy libraries.

## Brand Commitments
Name: Ghost Writer. Honest voice: a flag is a statistical hint about style, not proof of authorship. Caveats are shown next to results, not hidden.

## Evidence on Hand
Real model scores and the three built-in sample essays in demo/samples.json. Headline numbers are in README.md and MODEL_CARD.md. No testimonials or user counts exist; do not invent any.

## Product Principles
1. Show the evidence with the verdict.
2. State limits in plain words, next to the result they qualify.
3. Never present a flag as proof.
4. Keep every element explainable to a student.

## Accessibility & Inclusion
Readable contrast in light and dark, usable at phone width, and meaning never carried by colour alone (flagged state also uses words).
