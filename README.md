# Detection of AI-Generated Text Using Machine Learning

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-ML-orange)
![NLP](https://img.shields.io/badge/NLP-Text%20Classification-green)

## Project Overview

This project detects whether a text is human-written or AI-generated using NLP and Machine Learning techniques.



## Techniques Used

### Text Preprocessing
- Lowercasing
- Tokenization
- Stopword Removal
- Cleaning

### Embeddings
- TF-IDF
- Word2Vec

### Models
- Logistic Regression
- Support Vector Machine (SVM)
- Random Forest

## Dataset

Balanced dataset containing:
- Human-written essays
- AI-generated essays

## Results

| Embedding | Model | Accuracy |
|------------|---------|---------|
| TF-IDF | Logistic Regression | 100% |
| TF-IDF | SVM | 100% |
| Word2Vec | Logistic Regression | 82.46% |
| Word2Vec | SVM | 100% |
| Word2Vec | Random Forest | 96.49% |

![PCA Projection](images/PCA_visualisation%20_of_TF-IDF_features.png)

![Confusion Matrix](images/Confusion%20_matrix.png)

![Embedding Comparison](images/Embedding%20_technique_comparison.png)

## Author

Jaiveer Singh Minhas
ISEP Paris
