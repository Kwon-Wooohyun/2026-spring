from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(50), unique=True, nullable=False)   # 아이디
    nickname   = db.Column(db.String(50), unique=True, nullable=False)   # 닉네임
    password   = db.Column(db.String(200), nullable=False)               # 해시 저장
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviews  = db.relationship('Review',  backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)
    likes    = db.relationship('Like',    backref='user', lazy=True)

class Review(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title          = db.Column(db.String(200), nullable=False)
    author         = db.Column(db.String(100), nullable=False)
    genre          = db.Column(db.String(20),  nullable=False)
    star_difficulty= db.Column(db.Integer,     nullable=False)
    star_worth     = db.Column(db.Integer,     nullable=False)
    content        = db.Column(db.String(500), nullable=False)
    filename       = db.Column(db.String(300), nullable=True)
    created_at     = db.Column(db.DateTime,    default=datetime.utcnow)

    likes    = db.relationship('Like',    backref='review', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='review', lazy=True, cascade='all, delete-orphan')

class Like(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'),   nullable=False)
    created_at= db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('review_id', 'user_id'),)  # 중복 공감 방지

class Comment(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'),   nullable=False)
    content   = db.Column(db.String(300), nullable=False)
    created_at= db.Column(db.DateTime,   default=datetime.utcnow)