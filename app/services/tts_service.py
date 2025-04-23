import os
import time
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
    - alloy: Neutral, versatile voice
    - echo: Warm, natural voice
    - fable: British accent, clear and engaging
    - onyx: Deep, authoritative male voice
    - nova: Warm female voice
    - shimmer: Cheerful, younger-sounding voice
    """
    try:
        # Create a temporary file to store the audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_filename = temp_file.name
        temp_file.close()
        
        # For initial testing without an OpenAI API key, return a mock file path
        if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY == "your_openai_api_key":
            logger.warning("No OpenAI API key provided, returning mock audio file path")
            return temp_filename
        
        # Generate speech using OpenAI TTS
        response = openai.audio.speech.create(
            model="tts-1",  # or "tts-1-hd" for higher quality
            voice=voice,
            input=text
        )
        
        # Save the audio to the temporary file
        response.stream_to_file(temp_filename)
        
        logger.info(f"Generated speech saved to {temp_filename}")
        return temp_filename
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        return None
