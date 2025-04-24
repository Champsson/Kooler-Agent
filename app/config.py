import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    
    # ServiceTitan Configuration
    SERVICETITAN_CLIENT_ID = os.getenv('SERVICETITAN_CLIENT_ID')
    SERVICETITAN_CLIENT_SECRET = os.getenv('SERVICETITAN_CLIENT_SECRET')
    SERVICETITAN_TENANT_ID = os.getenv('SERVICETITAN_TENANT_ID')
    SERVICETITAN_API_URL = os.getenv('SERVICETITAN_API_URL')
    
    # Vector Database (Pinecone)
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT')
    
    # AWS Configuration
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'kooler-agent-tts')
    AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')


