---
title: Ghost Writer
emoji: 👻
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

Ghost Writer: an AI-generated-text detector for student essays that shows why it decides as it does.
Course project for CSE472 (Deep Learning for NLP). Code, results and model card: https://github.com/jaiveerminhas06/Ghost-Writer

The detector is a fine-tuned DistilRoBERTa. A flag is a statistical hint about writing style, not proof of authorship.
Pasted text is scored on the server and is not stored or logged.
