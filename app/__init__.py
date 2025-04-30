from flask import Flask
from .config import config

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register blueprints here (e.g., Twilio routes)
    # from .routes.twilio_routes import twilio_bp
    # app.register_blueprint(twilio_bp)

    # Simple health check route
    @app.route("/health")
    def health_check():
        return "OK", 200

    return app

