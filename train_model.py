import pandas as pd
import re
import pickle
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import os

# Download required NLTK data
nltk.download("stopwords")
nltk.download("wordnet")

# Load dataset
df = pd.read_csv("data/fake_job_postings.csv")

# Combine text columns
df["text"] = (
    df["title"].fillna("") + " " +
    df["company_profile"].fillna("") + " " +
    df["description"].fillna("") + " " +
    df["requirements"].fillna("") + " " +
    df["benefits"].fillna("")
)

stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

def clean_text(text):
    text = text.lower()
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^a-z\s]", "", text)
    words = [lemmatizer.lemmatize(w) for w in text.split() if w not in stop_words]
    return " ".join(words)

# Clean text
df["clean_text"] = df["text"].apply(clean_text)

X = df["clean_text"]
y = df["fraudulent"]

# Create TF-IDF vectorizer
vectorizer = TfidfVectorizer(max_features=5000)
X_vec = vectorizer.fit_transform(X)

# Train model
model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(X_vec, y)

# Create model folder if not exists
os.makedirs("model", exist_ok=True)

# Save model and vectorizer
pickle.dump(model, open("model/fake_real_job_model.pkl", "wb"))
pickle.dump(vectorizer, open("model/tfidf_vectorizer.pkl", "wb"))

print("✅ Model and TF-IDF vectorizer created successfully")
