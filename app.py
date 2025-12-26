from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import pickle
import re
import nltk
import pytesseract
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from PIL import Image

# -----------------------------
# NLTK setup
# -----------------------------
nltk.download("stopwords")
nltk.download("wordnet")

stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

# -----------------------------
# Tesseract path (Windows)
# -----------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -----------------------------
# Load ML model
# -----------------------------
model = pickle.load(open("model/fake_real_job_model.pkl", "rb"))
vectorizer = pickle.load(open("model/tfidf_vectorizer.pkl", "rb"))

# -----------------------------
# Flask app
# -----------------------------
app = Flask(__name__)
app.secret_key = "jobcheck_secret_key"

# -----------------------------
# Database
# -----------------------------
def get_db():
    return sqlite3.connect("database.db")

# -----------------------------
# Create Admin
# -----------------------------
def create_admin():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS admin (username TEXT, password TEXT)"
    )
    cur.execute("SELECT * FROM admin")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO admin VALUES (?, ?)",
            ("admin", "admin123")
        )
    conn.commit()
    conn.close()

# -----------------------------
# Create Predictions Table
# -----------------------------
def create_predictions_table():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result TEXT
        )
    """)
    conn.commit()
    conn.close()

# -----------------------------
# Text cleaning
# -----------------------------
def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", "", text)
    words = [lemmatizer.lemmatize(w) for w in text.split() if w not in stop_words]
    return " ".join(words)

# -----------------------------
# Signup
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS users (username TEXT, email TEXT, password TEXT)"
        )
        cur.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            (username, email, password),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("signup.html")

# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password),
        )
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect(url_for("user_dashboard"))

    return render_template("login.html")

# -----------------------------
# User Dashboard
# -----------------------------
@app.route("/user/dashboard", methods=["GET", "POST"])
def user_dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    prediction = None
    extracted_text = None

    if request.method == "POST":
        job_text = request.form.get("job_text")
        job_image = request.files.get("job_image")

        # TEXT → ML
        if job_text:
            cleaned = clean_text(job_text)
            vec = vectorizer.transform([cleaned])
            result = model.predict(vec)[0]

            prediction = "🚨 Fake Job Posting" if result == 1 else "✅ Real Job Posting"

            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO predictions (result) VALUES (?)",
                ("Fake" if result == 1 else "Real",)
            )
            conn.commit()
            conn.close()

        # IMAGE → OCR → ML
        elif job_image:
            image = Image.open(job_image)
            extracted_text = pytesseract.image_to_string(image)

            if extracted_text.strip():
                cleaned = clean_text(extracted_text)
                vec = vectorizer.transform([cleaned])
                result = model.predict(vec)[0]

                prediction = "🚨 Fake Job Posting (Image)" if result == 1 else "✅ Real Job Posting (Image)"

                conn = get_db()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO predictions (result) VALUES (?)",
                    ("Fake" if result == 1 else "Real",)
                )
                conn.commit()
                conn.close()
            else:
                prediction = "❌ No readable text found"

    return render_template(
        "user_dashboard.html",
        prediction=prediction,
        extracted_text=extracted_text
    )

# -----------------------------
# Admin Login
# -----------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, password),
        )
        admin = cur.fetchone()
        conn.close()

        if admin:
            session["admin"] = username
            return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")

# -----------------------------
# Admin Dashboard
# -----------------------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cur = conn.cursor()

    # Counts
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM predictions")
    prediction_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM predictions WHERE result='Fake'")
    fake_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM predictions WHERE result='Real'")
    real_count = cur.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        user_count=user_count,
        prediction_count=prediction_count,
        fake_count=fake_count,
        real_count=real_count
    )


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    create_admin()
    create_predictions_table()
    app.run(debug=True)
