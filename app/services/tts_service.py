import os
import tempfile
import hashlib
import openai
from app.config import Config
from app.utils import timer_decorator, logger

# Initialize OpenAI client
openai.api_key = Config.OPENAI_API_KEY

# Simple cache for TTS responses
TTS_CACHE = {}

@timer_decorator
def text_to_speech(text, voice="nova"):
    """Convert text to speech using OpenAI's TTS API
    
    Available voices:
    - alloy: Neutral and balanced
    - echo: Warm and clear
    - fable: Expressive and narrative
    - onyx: Deep and authoritative (male voice)
    - nova: Professional and smooth (female voice)
    - shimmer: Bright and optimistic
    """
    try:
        # Create a temporary file to store the audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_filename = temp_file.name
        temp_file.close()
        
        # Generate speech using OpenAI TTS
        response = openai.audio.speech.create(
            model="tts-1-hd",  # Using the high-definition model for best quality
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

@timer_decorator
def get_cached_tts(text, voice="nova"):
    """Get cached TTS or generate new"""
    # Create a cache key based on text and voice
    cache_key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    
    # Check if we have a cached S3 URL
    if cache_key in TTS_CACHE:
        logger.info(f"Using cached TTS for: {text[:30]}...")
        return TTS_CACHE[cache_key]
    
    # Generate new TTS
    speech_file = text_to_speech(text, voice)
    if not speech_file:
        return None
    
    # Upload to S3 (import here to avoid circular imports)
    from app.services.storage_service import upload_to_s3
    s3_url = upload_to_s3(speech_file, f"tts-{cache_key}.mp3")
    
    if s3_url:
        # Cache the S3 URL
        TTS_CACHE[cache_key] = s3_url
        # Clean up the temp file
        os.remove(speech_file)
    
    return s3_url


