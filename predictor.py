import joblib

model = joblib.load("model/fake_real_job_model.pkl")
vectorizer = joblib.load("model/tfidf_vectorizer.pkl")

def predict_job(text):
    vec = vectorizer.transform([text])
    prob = model.predict_proba(vec)[0]
    label = "FAKE" if prob[1] > 0.5 else "REAL"
    return label, round(max(prob) * 100, 2)
