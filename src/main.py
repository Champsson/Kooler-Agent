import os
from . import create_app

app = create_app()

if __name__ == "__main__":
    # Note: For development, Flask's built-in server is fine.
    # For production (e.g., on Render), use gunicorn.
    port = int(os.environ.get("PORT", 5000)) # Render typically sets the PORT env var
    app.run(host="0.0.0.0", port=port, debug=(app.config.get("FLASK_ENV") == "development"))

