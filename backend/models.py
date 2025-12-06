from datetime import datetime, timezone

from .extensions import db


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Record(db.Model):
    __tablename__ = "record"

    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    user = db.relationship("User", backref="records")

    patient_id = db.Column(db.String(50))
    file_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    full_text = db.Column(db.Text)

    chunks = db.relationship("Chunk", backref="record", cascade="all, delete-orphan", lazy=True)


class Chunk(db.Model):
    __tablename__ = "chunk"

    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.String, db.ForeignKey("record.id"), nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)
