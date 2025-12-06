from datetime import datetime, timedelta, timezone

import jwt
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, limiter
from .models import User
from .config import SECRET_KEY, JWT_ALGO, JWT_EXP_MINUTES

auth_bp = Blueprint("auth", __name__)


# ---------- Helper: Get user from JWT token ----------

def get_user_from_token(req):
    auth_header = req.headers.get("Authorization", "")
    print("Auth header:", auth_header)

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        print("Token expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        user_id = int(user_id)
    except ValueError:
        return None

    user = User.query.get(user_id)
    return user


# ---------- Auth Endpoints ----------

@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "User already exists"}), 400

    user = User(
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Signup successful"}), 200


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Generate JWT token
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXP_MINUTES)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGO)

    return jsonify({
        "message": "Login successful",
        "token": token,
        "email": user.email
    }), 200
