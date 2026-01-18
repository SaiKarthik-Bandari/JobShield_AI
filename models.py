from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default="user")  # user/admin

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_text = db.Column(db.Text)
    result = db.Column(db.String(10))
    confidence = db.Column(db.Float)
    user_id = db.Column(db.Integer)
