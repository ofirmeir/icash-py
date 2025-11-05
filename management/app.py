from flask import Flask
import os

from mvc_app.controllers import bp as main_bp
from mvc_app.db import create_tables
import mvc_app.models
from mvc_app.logging_config import setup_logging

# Replace monolith with MVC app factory bootstrap
setup_logging("log.cfg")


def create_app(test_config=None):
    """Application factory"""
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "mvc_app", "templates"))
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
    app.register_blueprint(main_bp)
    # ensure tables exist
    create_tables()
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
