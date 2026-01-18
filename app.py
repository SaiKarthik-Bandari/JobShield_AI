from flask import Flask, render_template, request, redirect, Response
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_access_cookies, unset_jwt_cookies
)
import mysql.connector
import pickle, re
from datetime import datetime, timedelta
import pytesseract
from PIL import Image
import numpy as np
import cv2
import train_model


# =====================================================
# APP + JWT CONFIG
# =====================================================
app = Flask(__name__)
app.secret_key = "jobcheck_secret"

app.config["JWT_SECRET_KEY"] = "jobcheck_super_secret_jwt"
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=5)

jwt = JWTManager(app)

# =====================================================
# DATABASE
# =====================================================
db = mysql.connector.connect(
    host="localhost",
    user="jobcheck_user",
    password="jobcheck123",
    database="jobcheck_db",
    auth_plugin="mysql_native_password"
)
cursor = db.cursor(dictionary=True)

# =====================================================
# LOAD ML MODEL
# =====================================================
model = pickle.load(open("model/fake_real_job_model.pkl", "rb"))
vectorizer = pickle.load(open("model/tfidf_vectorizer.pkl", "rb"))

# =====================================================
# TEXT UTILITIES
# =====================================================
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_text_from_image(file):
    img = np.array(Image.open(file).convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
    return clean_text(pytesseract.image_to_string(gray))

# =====================================================
# PREDICTION
# =====================================================
def predict_job(text):
    cleaned = clean_text(text)

    if len(cleaned.split()) < 10:
        return "Invalid Input", 0.0

    vec = vectorizer.transform([cleaned])
    probs = model.predict_proba(vec)[0]
    pred = int(model.predict(vec)[0])
    confidence = round(float(max(probs)) * 100, 2)

    return ("Fake Job", confidence) if pred == 1 else ("Real Job", confidence)

# =====================================================
# ROUTES
# =====================================================
@app.route("/")
def home():
    return redirect("/login")

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        cursor.execute(
            "SELECT id FROM users WHERE username=%s OR email=%s",
            (request.form["username"], request.form["email"])
        )
        if cursor.fetchone():
            return render_template("signup.html", message="User already exists")

        cursor.execute("""
            INSERT INTO users (username,email,password,role)
            VALUES (%s,%s,%s,'user')
        """, (
            request.form["username"],
            request.form["email"],
            request.form["password"]
        ))
        db.commit()
        return redirect("/login")

    return render_template("signup.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    message = None

    if request.method == "POST":
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (request.form["username"], request.form["password"])
        )
        user = cursor.fetchone()

        if user:
            token = create_access_token(
                identity=str(user["id"]),
                additional_claims={"role": user["role"]}
            )
            resp = redirect(
                "/admin/dashboard" if user["role"] == "admin" else "/predict"
            )
            set_access_cookies(resp, token)
            return resp
        else:
            message = "Invalid username or password"

    return render_template("login.html", message=message)

# ---------------- FORGOT PASSWORD ----------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = None

    if request.method == "POST":
        email = request.form["email"]

        cursor.execute(
            "SELECT password FROM users WHERE email=%s",
            (email,)
        )
        user = cursor.fetchone()

        if user:
            message = f"Your password is: {user['password']}"
        else:
            message = "Email not found. Please register first."

    return render_template("forgot_password.html", message=message)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    resp = redirect("/login")
    unset_jwt_cookies(resp)
    return resp

# ---------------- PREDICT ----------------
@app.route("/predict", methods=["GET","POST"])
@jwt_required()
def predict():
    result = confidence = None

    if request.method == "POST":
        text = request.form.get("job_text", "")
        source = "text"

        if "job_image" in request.files and request.files["job_image"].filename:
            text = extract_text_from_image(request.files["job_image"])
            source = "ocr"

        result, confidence = predict_job(text)

        cursor.execute("""
            INSERT INTO predictions
            (user_id, job_text, prediction, confidence, source, created_at)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            get_jwt_identity(),
            text,
            result,
            confidence,
            source,
            datetime.now()
        ))
        db.commit()

    return render_template("predict.html", result=result, confidence=confidence)

# ---------------- USER DASHBOARD ----------------
@app.route("/dashboard")
@jwt_required()
def dashboard():
    cursor.execute("""
        SELECT prediction, confidence, source, created_at
        FROM predictions
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (get_jwt_identity(),))
    history = cursor.fetchall()

    return render_template("user_dashboard.html", history=history)

# ---------------- USER DOWNLOAD HISTORY ----------------
@app.route("/user/download-history")
@jwt_required()
def user_download_history():
    cursor.execute("""
        SELECT prediction, confidence, source, created_at
        FROM predictions
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (get_jwt_identity(),))
    rows = cursor.fetchall()

    def generate():
        yield "Prediction,Confidence,Source,Date\n"
        for r in rows:
            yield f"{r['prediction']},{r['confidence']},{r['source']},{r['created_at']}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=my_history.csv"}
    )

# =====================================================
# ADMIN DASHBOARD
# =====================================================
@app.route("/admin/dashboard")
@jwt_required()
def admin_dashboard():
    if get_jwt()["role"] != "admin":
        return redirect("/login")

    cursor.execute("SELECT COUNT(*) total_users FROM users")
    total_users = cursor.fetchone()["total_users"]

    cursor.execute("SELECT COUNT(*) total_admins FROM users WHERE role='admin'")
    total_admins = cursor.fetchone()["total_admins"]

    cursor.execute("SELECT COUNT(*) total_predictions FROM predictions")
    total_predictions = cursor.fetchone()["total_predictions"]

    cursor.execute("""
        SELECT
            SUM(CASE WHEN prediction='Fake Job' THEN 1 ELSE 0 END) AS fake_jobs,
            SUM(CASE WHEN prediction='Real Job' THEN 1 ELSE 0 END) AS real_jobs
        FROM predictions
    """)
    row = cursor.fetchone()
    fake_jobs = row["fake_jobs"] or 0
    real_jobs = row["real_jobs"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS flagged_jobs
        FROM predictions
        WHERE prediction='Fake Job' AND confidence >= 70
    """)
    flagged_jobs = cursor.fetchone()["flagged_jobs"]

    cursor.execute("""
        SELECT
            DATE(created_at) AS day,
            COUNT(*) AS total,
            SUM(CASE WHEN prediction='Fake Job' THEN 1 ELSE 0 END) AS fake,
            SUM(CASE WHEN prediction='Real Job' THEN 1 ELSE 0 END) AS real_jobs
        FROM predictions
        GROUP BY DATE(created_at)
        ORDER BY day DESC
    """)
    daily_logs = cursor.fetchall()
    for d in daily_logs:
        d["real"] = d["real_jobs"]

    cursor.execute("SELECT id,username,email,role FROM users")
    users = cursor.fetchall()

    return render_template(
        "admin_dashboard.html",
        stats={
            "total_users": total_users,
            "total_admins": total_admins,
            "total_predictions": total_predictions,
            "fake_jobs": fake_jobs,
            "real_jobs": real_jobs,
            "flagged_jobs": flagged_jobs
        },
        daily_logs=daily_logs,
        users=users
    )

# ---------------- PROMOTE / DEMOTE ----------------
@app.route("/admin/promote/<int:user_id>")
@jwt_required()
def promote(user_id):
    if get_jwt()["role"] != "admin":
        return redirect("/login")
    cursor.execute("UPDATE users SET role='admin' WHERE id=%s", (user_id,))
    db.commit()
    return redirect("/admin/dashboard")

@app.route("/admin/demote/<int:user_id>")
@jwt_required()
def demote(user_id):
    if get_jwt()["role"] != "admin":
        return redirect("/login")
    cursor.execute("UPDATE users SET role='user' WHERE id=%s", (user_id,))
    db.commit()
    return redirect("/admin/dashboard")

# ---------------- ADMIN DOWNLOAD ----------------
@app.route("/admin/download-history")
@jwt_required()
def admin_download():
    if get_jwt()["role"] != "admin":
        return redirect("/login")

    cursor.execute("""
        SELECT u.username,p.prediction,p.confidence,p.source,p.created_at
        FROM predictions p JOIN users u ON u.id=p.user_id
        ORDER BY p.created_at DESC
    """)
    rows = cursor.fetchall()

    def generate():
        yield "User,Prediction,Confidence,Source,Date\n"
        for r in rows:
            yield f"{r['username']},{r['prediction']},{r['confidence']},{r['source']},{r['created_at']}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=all_predictions.csv"}
    )




#=========================================
@app.route("/admin/retrain")
@jwt_required()
def retrain_model_route():
    if get_jwt()["role"] != "admin":
        return redirect("/login")

    try:
        train_model.retrain_model()
        print("✅ Model retrained successfully")
    except Exception as e:
        print("❌ Retraining failed:", e)

    return redirect("/admin/dashboard")


# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
