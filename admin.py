from flask import render_template
from flask_login import login_required, current_user
from models import User, Prediction

@login_required
def admin_dashboard():
    if current_user.role != "admin":
        return "Unauthorized"

    users = User.query.all()
    predictions = Prediction.query.all()
    return render_template(
        "admin_dashboard.html",
        users=users,
        predictions=predictions
    )
