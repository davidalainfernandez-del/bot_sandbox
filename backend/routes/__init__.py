from .health import bp as health_bp
from .status import bp as status_bp
from .admin import bp as admin_bp


def register_routes(app):
    app.register_blueprint(health_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(admin_bp)