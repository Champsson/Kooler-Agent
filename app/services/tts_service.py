import os
import tempfile
import openai
from app.config import Config
from app.utils import timer_decorator, logger

# Initialize OpenAI client
openai.api_key = Config.OPENAI_API_KEY

@timer_decorator
def text_to_speech(text, voice="alloy"):
    """Convert text to speech using OpenAI's TTS API
    
    Available voices:
    - alloy: Neutral and balanced
    - echo: Warm and clear
    - fable: Expressive and narrative
    - onyx: Deep and authoritative
    - nova: Professional and smooth
    - shimmer: Bright and optimistic
    """
    try:
        response = openai.audio.speech.create(
            model="tts-1-hd",  # Using the high-definition model for best quality
            voice=voice,
            input=text
        )
        
        # Create a temporary file to store the audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_filename = temp_file.name
        
        # Save the audio to the temporary file
        response.stream_to_file(temp_filename)
        
        return temp_filename
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        return None

