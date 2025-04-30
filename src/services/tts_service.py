import os
from openai import OpenAI
from pathlib import Path
from ..config import config
from ..utils import get_logger
import uuid

logger = get_logger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=config.OPENAI_API_KEY)

# Define the directory to store temporary TTS audio files
# This should be accessible by the web server
# Using a subdirectory within the instance path is a common pattern
# Ensure this path is correctly configured for Render deployment later
TTS_AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "instance", "tts_audio")
Path(TTS_AUDIO_DIR).mkdir(parents=True, exist_ok=True)
logger.info(f"TTS Audio directory set to: {TTS_AUDIO_DIR}")

def generate_audio(text: str, voice: str = "alloy", model: str = "tts-1") -> str:
    """Generates audio from text using OpenAI TTS and saves it to a temporary file.

    Args:
        text (str): The text to synthesize.
        voice (str, optional): The voice to use (e.g., alloy, echo, fable, onyx, nova, shimmer). Defaults to "alloy".
        model (str, optional): The TTS model to use (e.g., tts-1, tts-1-hd). Defaults to "tts-1".

    Returns:
        str: The absolute path to the generated MP3 audio file.
           Returns None if generation fails.
    """
    if not text:
        logger.warning("TTS generation skipped: No text provided.")
        return None

    try:
        # Generate a unique filename
        unique_filename = f"tts_{uuid.uuid4()}.mp3"
        speech_file_path = Path(TTS_AUDIO_DIR) / unique_filename

        logger.info(f"Generating TTS audio for text: 	{text[:50]}...	 Voice: {voice}, Model: {model}")
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text
        )

        # Stream the audio to the file
        response.stream_to_file(speech_file_path)
        logger.info(f"TTS audio successfully generated and saved to: {speech_file_path}")
        
        # Return the absolute path to the file
        return str(speech_file_path.resolve())

    except Exception as e:
        logger.error(f"Failed to generate TTS audio: {e}", exc_info=True)
        return None

# Example usage (for testing)
if __name__ == "__main__":
    test_text = "Hello! This is a test of the OpenAI Text-to-Speech service integrated into Weggy."
    print(f"Generating audio for: 	{test_text}	")
    
    audio_path = generate_audio(test_text)
    
    if audio_path:
        print(f"Audio generated successfully: {audio_path}")
        # You would typically need a way to play this file to verify
        # Or check if the file exists and has a non-zero size
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            print("File exists and has size > 0.")
        else:
            print("Error: File does not exist or is empty.")
    else:
        print("Audio generation failed.")

