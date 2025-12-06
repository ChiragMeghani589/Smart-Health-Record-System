import os

# Flask / DB
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "sqlite:///health_records.db"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# JWT
SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET")
JWT_ALGO = "HS256"
JWT_EXP_MINUTES = 60  # token expires in 1 hour
