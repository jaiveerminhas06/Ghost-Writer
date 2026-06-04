# Detection of AI-Generated Text Using Machine Learning

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

### Visualizations

### PCA Projection

![PCA Projection](images/PCA_visualisation_of_TF-IDF_features.png)

### Confusion Matrix

![Confusion Matrix](images/Confusion_matrix.png)

### Embedding Comparison

![Embedding Comparison](images/Embedding_technique_comparison.png)

## Author

Jaiveer Singh Minhas
ISEP Paris
