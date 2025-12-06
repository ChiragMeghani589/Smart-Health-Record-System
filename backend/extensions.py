from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sklearn.feature_extraction.text import TfidfVectorizer

# SQLAlchemy instance (initialized in create_app)
db = SQLAlchemy()

# Rate limiter (initialized in create_app)
limiter = Limiter(
    key_func=get_remote_address,
)

# TF–IDF vector store globals
vectorizer = TfidfVectorizer(stop_words="english")
embeddings_store = []  # list of {record_id, chunk_text}
chunk_vectors = None   # sparse matrix
