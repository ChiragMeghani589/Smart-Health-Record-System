import uuid
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------- Flask + DB setup ----------
app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///health_records.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# TF-IDF based "vector store"
vectorizer = TfidfVectorizer(stop_words="english")
embeddings_store = []  # list of {record_id, chunk_text}
chunk_vectors = None   # sparse matrix


# ---------- DB Models ----------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Record(db.Model):
    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    user = db.relationship("User", backref="records")
    
    patient_id = db.Column(db.String(50))
    file_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    full_text = db.Column(db.Text)

    chunks = db.relationship("Chunk", backref="record", cascade="all, delete-orphan", lazy=True)


class Chunk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.String, db.ForeignKey("record.id"), nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)


# ---------- Utility functions ----------

def extract_text_from_pdf(file_stream) -> str:
    reader = PdfReader(file_stream)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
    return text


def chunk_text(text: str, max_chars: int = 1000):
    chunks = []
    text = text.strip()
    for i in range(0, len(text), max_chars):
        chunk = text[i:i + max_chars]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def rebuild_vector_store_from_db():
    """
    Load all chunks from DB and rebuild TF-IDF matrix.
    """
    global embeddings_store, chunk_vectors, vectorizer

    embeddings_store = []
    all_chunks = Chunk.query.all()
    for c in all_chunks:
        embeddings_store.append({
            "record_id": c.record_id,
            "chunk_text": c.chunk_text
        })

    if not embeddings_store:
        chunk_vectors = None
        return

    texts = [item["chunk_text"] for item in embeddings_store]
    chunk_vectors = vectorizer.fit_transform(texts)


def simple_summary(text: str, max_chars: int = 500) -> str:
    text = text.strip()
    if not text:
        return ""
    lines = text.splitlines()
    summary = "\n".join(lines[:5])
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "..."
    return summary


# ---------- Auth Helpers ----------

def get_user_from_token(request):

    auth_header = request.headers.get("Authorization", "")
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
        user_id = int(user_id)   # 👈 convert back to int
    except ValueError:
        return None
        
    user = User.query.get(user_id)
    return user



# ---------- Auth Endpoints ----------

from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"   # store in env variable ideally
JWT_ALGO = "HS256"
JWT_EXP_MINUTES = 60  # token expires in 1 hour


@app.route("/api/signup", methods=["POST"])
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

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app)

@limiter.limit("5 per minute")
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Generate JWT token
    from datetime import datetime, timedelta, timezone
    
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


# ---------- API: Upload record ----------

@app.route("/api/upload-record", methods=["POST"])
def upload_record():
    # Optional: enforce login
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    patient_id = request.form.get("patient_id", "").strip()

    if not patient_id:
        return jsonify({"error": "Patient ID is required"}), 400
    
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        text = extract_text_from_pdf(file)
        if not text.strip():
            return jsonify({"error": "No text extracted from PDF"}), 400

        record_id = str(uuid.uuid4())
        record = Record(
            id=record_id,
            user_id=user.id,
            patient_id=patient_id,
            file_name=file.filename,
            created_at=datetime.now(timezone.utc),
            full_text=text
        )
        db.session.add(record)

        chunks = chunk_text(text)
        for chunk_text_value in chunks:
            db.session.add(Chunk(record_id=record_id, chunk_text=chunk_text_value))

        db.session.commit()

        rebuild_vector_store_from_db()

        return jsonify({
            "message": "Record uploaded and indexed successfully",
            "record": {
                "id": record_id,
                "patient_id": patient_id,
                "file_name": file.filename,
                "created_at": record.created_at.isoformat(),
                "num_chunks": len(chunks)
            }
        }), 200

    except Exception as e:
        print("Error in upload_record:", e)
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


# ---------- API: Search records ----------

from sqlalchemy import func
from sklearn.metrics.pairwise import cosine_similarity

@app.route("/api/search-records", methods=["POST"])
def search_records():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True)
    query = data.get("query", "").strip()

    # pagination params
    page = int(data.get("page", 1))
    page_size = int(data.get("page_size", 5))
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 5

    if not query:
        return jsonify({"error": "Query is required"}), 400

    # ---------- 0) DIRECT PATIENT_ID SEARCH ----------
    # If user typed a patient ID, we look ONLY at the patient_id column.
    # This does NOT depend on the PDF content at all.
    patient_query = Record.query.filter(
        Record.user_id == user.id,
        func.lower(Record.patient_id) == query.lower()   # exact, case-insensitive match
    )

    total_direct = patient_query.count()
    if total_direct > 0:
        # apply pagination on patient-id results
        patient_records = (
            patient_query
            .order_by(Record.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        final_results = []
        for rec in patient_records:
            snippet = rec.full_text or ""
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."

            final_results.append({
                "record_id": rec.id,
                "patient_id": rec.patient_id,
                "file_name": rec.file_name,
                "snippet": snippet,
            })

        return jsonify({
            "results": final_results,
            "total": total_direct,
            "page": page,
            "page_size": page_size,
        }), 200
    # ---------- END DIRECT PATIENT_ID SEARCH ----------

    # ---------- 1) SEMANTIC (TF-IDF) SEARCH OVER TEXT ----------
    global vectorizer, chunk_vectors, embeddings_store

    # if nothing indexed yet
    if vectorizer is None or chunk_vectors is None or not embeddings_store:
        return jsonify({"results": [], "total": 0, "page": page, "page_size": page_size}), 200

    try:
        # vectorize query
        query_vec = vectorizer.transform([query])
        sims = cosine_similarity(query_vec, chunk_vectors)[0]

        # keep best chunk per record
        results_by_record = {}  # record_id -> {score, snippet}

        for idx, sim in enumerate(sims):
            sim = float(sim)
            if sim <= 0.0:
                continue

            rec_id = embeddings_store[idx]["record_id"]
            chunk_text = embeddings_store[idx]["chunk_text"]

            if rec_id not in results_by_record or sim > results_by_record[rec_id]["score"]:
                results_by_record[rec_id] = {
                    "record_id": rec_id,
                    "score": sim,
                    "snippet": chunk_text,
                }

        if not results_by_record:
            return jsonify({"results": [], "total": 0, "page": page, "page_size": page_size}), 200

        # sort by score
        scored_list = sorted(
            results_by_record.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        total = len(scored_list)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = scored_list[start:end]

        # fetch only this user's records for those IDs
        record_ids = [item["record_id"] for item in page_items]
        records = Record.query.filter(
            Record.id.in_(record_ids),
            Record.user_id == user.id
        ).all()
        records_by_id = {r.id: r for r in records}

        final_results = []
        for item in page_items:
            rec = records_by_id.get(item["record_id"])
            if not rec:
                continue

            snippet = item["snippet"]
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."

            final_results.append({
                "record_id": rec.id,
                "patient_id": rec.patient_id,
                "file_name": rec.file_name,
                "snippet": snippet,
            })

        return jsonify({
            "results": final_results,
            "total": total,
            "page": page,
            "page_size": page_size
        }), 200

    except Exception as e:
        print("Error in search_records:", e)
        return jsonify({"error": "Internal server error"}), 500




# ---------- API: Get full record + summary ----------

@app.route("/api/record/<record_id>", methods=["GET"])
def get_record(record_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rec = Record.query.filter_by(id=record_id, user_id=user.id).first()
    if not rec:
        return jsonify({"error": "Record not found"}), 404

    summary = simple_summary(rec.full_text)

    return jsonify({
        "record": {
            "id": rec.id,
            "patient_id": rec.patient_id,
            "file_name": rec.file_name,
            "created_at": rec.created_at.isoformat(),
            "full_text": rec.full_text,
            "summary": summary, 
        }
    }), 200


# ---------- API: Delete record ----------

@app.route("/api/record/<record_id>", methods=["DELETE"])
def delete_record(record_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rec = Record.query.filter_by(id=record_id, user_id=user.id).first()
    if not rec:
        return jsonify({"error": "Record not found"}), 404

    try:
        db.session.delete(rec)
        db.session.commit()
        rebuild_vector_store_from_db()
        return jsonify({"message": "Record deleted successfully"}), 200
    except Exception as e:
        print("Error deleting record:", e)
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/record/<record_id>", methods=["PUT"])
def update_record(record_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rec = Record.query.filter_by(id=record_id, user_id=user.id).first()
    if not rec:
        return jsonify({"error": "Record not found"}), 404

    try:
        # Read fields from form-data
        patient_id = request.form.get("patient_id", "").strip()
        new_file = request.files.get("file")

        # Update patient_id only if provided
        if patient_id:
            rec.patient_id = patient_id

        # If a new PDF is uploaded, replace the text & chunks
        if new_file:
            text = extract_text_from_pdf(new_file)
            if not text.strip():
                return jsonify({"error": "No text extracted from new PDF"}), 400

            rec.full_text = text
            rec.file_name = new_file.filename

            # Remove old chunks for this record
            Chunk.query.filter_by(record_id=record_id).delete()

            # Add new chunks
            chunks = chunk_text(text)
            for c in chunks:
                db.session.add(Chunk(record_id=record_id, chunk_text=c))

        db.session.commit()
        rebuild_vector_store_from_db()

        return jsonify({"message": "Record updated successfully"}), 200

    except Exception as e:
        print("Error updating record:", e)
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500




# ---------- Init DB & index ----------

with app.app_context():
    db.create_all()
    rebuild_vector_store_from_db()


if __name__ == "__main__":
    app.run(debug=True)