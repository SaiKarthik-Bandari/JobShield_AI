from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

def register_routes(app):

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            username = request.form["username"]
            email = request.form["email"]
            password = request.form["password"]

            user_exists = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()

            if user_exists:
                flash("User already exists. Please login.")
                return redirect(url_for("login"))

            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                role="user"
            )

            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please login.")
            return redirect(url_for("login"))

        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]

            user = User.query.filter_by(username=username).first()

            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(
                    url_for("admin_dashboard" if user.role == "admin" else "user_dashboard")
                )

            flash("Invalid credentials")
            return redirect(url_for("login"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/user/dashboard")
    @login_required
    def user_dashboard():
        if current_user.role != "user":
            return redirect(url_for("login"))
        return render_template("user_dashboard.html")

    @app.route("/admin/dashboard")
    @login_required
    def admin_dashboard():
        if current_user.role != "admin":
            return redirect(url_for("login"))
        return render_template("admin_dashboard.html")
