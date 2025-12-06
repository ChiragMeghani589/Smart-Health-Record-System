import uuid
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from sqlalchemy import func
from sklearn.metrics.pairwise import cosine_similarity

from .extensions import db, vectorizer, embeddings_store
from . import extensions as ext
from .models import Record, Chunk
from .utils import extract_text_from_pdf, chunk_text, simple_summary, rebuild_vector_store_from_db
from .auth_routes import get_user_from_token

records_bp = Blueprint("records", __name__)


# ---------- API: Upload record ----------

@records_bp.route("/upload-record", methods=["POST"])
def upload_record():
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

@records_bp.route("/search-records", methods=["POST"])
def search_records():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True)
    raw_query = data.get("query", "")
    query = str(raw_query).strip()

    # pagination params
    page = int(data.get("page", 1))
    page_size = int(data.get("page_size", 5))
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 5

    if not query:
        return jsonify({"error": "Query is required"}), 400

    # ---------- DEBUG ---------- 
    all_recs = Record.query.filter_by(user_id=user.id).all()
    print("DEBUG all patient_ids for user", user.id, "=>",
          [r.patient_id for r in all_recs])
    print("DEBUG raw_query:", raw_query, "type:", type(raw_query), "-> query:", repr(query))

    # ---------- 0) PURE PATIENT_ID SEARCH (digits only) ----------
    # If the query is ONLY digits (like "1234", "43101"), treat it as an ID.
    if query.isdigit():
        print("DEBUG treating query as patient_id search")

        id_q = Record.query.filter_by(user_id=user.id, patient_id=query)
        total = id_q.count()
        print("DEBUG patient_id exact matches:", total)

        records_page = (
            id_q
            .order_by(Record.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        final_results = []
        for rec in records_page:
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
            "total": total,
            "page": page,
            "page_size": page_size,
        }), 200

    # ---------- 1) SEMANTIC (TF-IDF) SEARCH OVER TEXT ----------
    if ext.chunk_vectors is None or not embeddings_store:
        return jsonify({
            "results": [],
            "total": 0,
            "page": page,
            "page_size": page_size
        }), 200

    try:
        query_vec = vectorizer.transform([query])
        sims = cosine_similarity(query_vec, ext.chunk_vectors)[0]

        results_by_record = {}  # record_id -> {score, snippet}

        for idx, sim in enumerate(sims):
            sim = float(sim)
            if sim <= 0.0:
                continue

            rec_id = embeddings_store[idx]["record_id"]
            chunk_text_val = embeddings_store[idx]["chunk_text"]

            if rec_id not in results_by_record or sim > results_by_record[rec_id]["score"]:
                results_by_record[rec_id] = {
                    "record_id": rec_id,
                    "score": sim,
                    "snippet": chunk_text_val,
                }

        if not results_by_record:
            return jsonify({
                "results": [],
                "total": 0,
                "page": page,
                "page_size": page_size
            }), 200

        scored_list = sorted(
            results_by_record.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        total = len(scored_list)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = scored_list[start:end]

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

@records_bp.route("/record/<record_id>", methods=["GET"])
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

@records_bp.route("/record/<record_id>", methods=["DELETE"])
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


# ---------- API: Update record ----------

@records_bp.route("/record/<record_id>", methods=["PUT"])
def update_record(record_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rec = Record.query.filter_by(id=record_id, user_id=user.id).first()
    if not rec:
        return jsonify({"error": "Record not found"}), 404

    try:
        patient_id = request.form.get("patient_id", "").strip()
        new_file = request.files.get("file")

        if patient_id:
            rec.patient_id = patient_id

        if new_file:
            text = extract_text_from_pdf(new_file)
            if not text.strip():
                return jsonify({"error": "No text extracted from new PDF"}), 400

            rec.full_text = text
            rec.file_name = new_file.filename

            # Remove old chunks
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
