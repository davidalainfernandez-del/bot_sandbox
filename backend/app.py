import os
from flask import Flask

from backend.routes import register_routes


def create_app() -> Flask:
    app = Flask(__name__)
    register_routes(app)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))