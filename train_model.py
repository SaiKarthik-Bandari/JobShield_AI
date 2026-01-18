import pandas as pd
import re
import pickle
import nltk
import os

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# -----------------------------
# Setup
# -----------------------------
os.makedirs("model", exist_ok=True)

nltk.download("stopwords")
nltk.download("wordnet")

stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

# -----------------------------
# Text Cleaning
# -----------------------------
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^a-zA-Z]", " ", text)
    words = text.split()
    words = [lemmatizer.lemmatize(w) for w in words if w not in stop_words]
    return " ".join(words)

# -----------------------------
# RETRAIN FUNCTION (IMPORTANT)
# -----------------------------
def retrain_model():
    # Load Dataset
    df = pd.read_csv("Data/fake_job_postings.csv")
    df = df.fillna("")

    df["text"] = (
        df["title"] + " " +
        df["company_profile"] + " " +
        df["description"] + " " +
        df["requirements"] + " " +
        df["benefits"]
    )

    df["clean_text"] = df["text"].apply(clean_text)

    X = df["clean_text"]
    y = df["fraudulent"]

    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Vectorization
    vectorizer = TfidfVectorizer(max_features=6000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Model
    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced"
    )

    model.fit(X_train_vec, y_train)

    # Evaluation (for logs)
    y_pred = model.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)

    print("Accuracy:", acc)
    print(classification_report(y_test, y_pred))

    # Save Model
    with open("model/fake_real_job_model.pkl", "wb") as f:
        pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)

    with open("model/tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f, protocol=pickle.HIGHEST_PROTOCOL)

    return acc  # return accuracy for confirmation


# -----------------------------
# OPTIONAL: Standalone run
# -----------------------------
if __name__ == "__main__":
    retrain_model()
    print("✅ Model retrained and saved successfully.")
