from flask import Flask
import os
import sys

if __package__ is None or __package__ == "":
    # running as a script (python management/app.py) or tests import
    # ensure parent directory is on sys.path so sibling packages (e.g. `shared`) can be imported
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from mvc_app.controllers import bp as main_bp
    from mvc_app.db import create_tables
    import mvc_app.models as _models
    from mvc_app.logging_config import setup_logging
else:
    # running as a package (python -m management.app)
    from .mvc_app.controllers import bp as main_bp
    from .mvc_app.db import create_tables
    import management.mvc_app.models as _models  # ensure models are imported
    from .mvc_app.logging_config import setup_logging

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
