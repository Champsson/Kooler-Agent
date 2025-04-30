import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Assumes .env file is in the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """Application configuration settings loaded from environment variables."""

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

    # Pinecone
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "kooler-agent-knowledge")

    # ServiceTitan
    SERVICETITAN_CLIENT_ID = os.getenv("SERVICETITAN_CLIENT_ID")
    SERVICETITAN_CLIENT_SECRET = os.getenv("SERVICETITAN_CLIENT_SECRET")
    SERVICETITAN_APP_KEY = os.getenv("SERVICETITAN_APP_KEY")
    SERVICETITAN_TENANT_ID = os.getenv("SERVICETITAN_TENANT_ID")

    # Flask App
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a_default_secret_key_for_dev")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    # Basic validation (optional but recommended)
    @staticmethod
    def validate():
        required_vars = [
            "OPENAI_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", 
            "TWILIO_PHONE_NUMBER", "PINECONE_API_KEY", "PINECONE_ENVIRONMENT",
            "SERVICETITAN_CLIENT_ID", "SERVICETITAN_CLIENT_SECRET", 
            "SERVICETITAN_APP_KEY", "SERVICETITAN_TENANT_ID"
        ]
        missing_vars = [var for var in required_vars if not getattr(Config, var)]
        if missing_vars:
            print(f"Warning: Missing required environment variables: {', '.join(missing_vars)}")
            # Depending on strictness, you might raise an exception here
            # raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Instantiate config
config = Config()
# config.validate() # Uncomment to enable validation on import

