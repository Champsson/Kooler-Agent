import os
from flask import Flask
from app.config import Config

def create_app(config_class=Config):
    static_folder = os.path.join(os.path.dirname(__file__), 'static')
    app = Flask(__name__, static_folder=static_folder)
    
    # Register blueprints
    from app.routes.twilio_routes import twilio_bp
    from app.routes.api_routes import api_bp
    
    app.register_blueprint(twilio_bp)
    app.register_blueprint(api_bp)
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return {"status": "healthy"}, 200
    
    return app
