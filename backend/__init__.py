from flask import Flask
from flask_cors import CORS

from .config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from .extensions import db, limiter
from .utils import rebuild_vector_store_from_db
from .auth_routes import auth_bp
from .record_routes import records_bp


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Config
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

    # Init extensions
    db.init_app(app)
    limiter.init_app(app)

    # Register blueprints with /api prefix
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(records_bp, url_prefix="/api")

    # Create tables & rebuild vector store at startup
    with app.app_context():
        db.create_all()
        rebuild_vector_store_from_db()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
