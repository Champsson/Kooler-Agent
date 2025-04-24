import os
import sys
from app.services.tts_service import text_to_speech
from app.services.storage_service import upload_to_s3

# Set up environment for imports to work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Generate greeting with premium voice
greeting = "Thank you for calling Kooler Garage Doors. How can I help you today?"
print("Generating greeting audio...")
speech_file = text_to_speech(greeting, voice="nova")

if speech_file:
    print(f"Audio generated at: {speech_file}")
    print("Uploading to S3...")
    s3_url = upload_to_s3(speech_file, "greeting.mp3")
    print(f"Greeting uploaded to: {s3_url}")
    print("Done! Use this URL in your Twilio routes.")
else:
    print("Failed to generate greeting audio.")
