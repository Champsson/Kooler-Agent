from flask import Blueprint, request, url_for, Response, send_from_directory
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
import os

from ..services import tts_service, orchestration_service # Removed assistant_service, twilio_service (unused here)
from ..utils import get_logger
from ..config import config

logger = get_logger(__name__)

twilio_bp = Blueprint("twilio_bp", __name__, url_prefix="/twilio")

# Note: Thread management is now handled within orchestration_service

# --- Voice Webhooks --- 

@twilio_bp.route("/voice", methods=["POST"])
def handle_incoming_call():
    """Handles incoming calls, initiates conversation, and gathers initial speech input."""
    response = VoiceResponse()
    call_sid = request.values.get("CallSid", None)
    from_number = request.values.get("From", None)
    logger.info(f"Incoming call received: SID={call_sid}, From={from_number}")

    # Initial greeting and gather input
    gather = Gather(
        input="speech",
        action=url_for("twilio_bp.process_speech", _external=True), # URL for processing speech
        method="POST",
        speechTimeout="auto", # Let Twilio decide based on silence
        speechModel="phone_call", # Model optimized for phone audio
        enhanced=True # Use enhanced speech recognition if available
    )
    # Use a standard voice for the initial prompt, TTS comes later for responses
    gather.say("Hello, thank you for calling Kooler Garage Doors. This is Weggy, the AI assistant. How can I help you today?", voice="Polly.Joanna") 
    response.append(gather)

    # If Gather fails (e.g., no input), redirect back to the start
    response.redirect(url_for("twilio_bp.handle_incoming_call", _external=True), method="POST")

    return Response(str(response), mimetype="text/xml")

@twilio_bp.route("/voice/process", methods=["POST"])
def process_speech():
    """Processes the speech input gathered from the user via the Orchestration Service."""
    response = VoiceResponse()
    call_sid = request.values.get("CallSid", None)
    speech_result = request.values.get("SpeechResult", None)
    confidence = request.values.get("Confidence", 0.0)
    logger.info(f"Processing speech for call {call_sid}: {speech_result} (Confidence: {confidence})")

    if not call_sid:
        logger.error("Received voice process request without CallSid.")
        response.say("Sorry, an internal error occurred. Please try calling back.", voice="Polly.Joanna")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    if not speech_result:
        logger.warning(f"No speech result received for call {call_sid}. Reprompting.")
        response.say("Sorry, I didn't catch that. Could you please repeat how I can help you?", voice="Polly.Joanna")
        # Re-gather input
        gather = Gather(
            input="speech",
            action=url_for("twilio_bp.process_speech", _external=True),
            method="POST",
            speechTimeout="auto",
            speechModel="phone_call",
            enhanced=True
        )
        response.append(gather)
        response.redirect(url_for("twilio_bp.handle_incoming_call", _external=True), method="POST") # Fallback redirect
        return Response(str(response), mimetype="text/xml")

    try:
        # 1. Call Orchestration Service to handle the interaction
        assistant_response_text = orchestration_service.handle_interaction(call_sid, speech_result)

        # 2. Generate audio using OpenAI TTS
        audio_file_path = tts_service.generate_audio(assistant_response_text)
        
        if audio_file_path:
            # Construct the public URL for the audio file
            # IMPORTANT: This needs proper configuration in create_app() or via web server (Nginx/Gunicorn)
            # Assuming instance/tts_audio is served at /tts_audio/
            # Corrected line 86:
            audio_url = f"{request.host_url.rstrip('/')}/tts_audio/{os.path.basename(audio_file_path)}"
            logger.info(f"Generated TTS audio URL: {audio_url}")
            response.play(audio_url)
        else:
            logger.error("TTS generation failed. Falling back to standard voice.")
            response.say(assistant_response_text, voice="Polly.Joanna") # Fallback voice

        # 3. Decide whether to continue gathering or end the call
        # For simplicity now, gather again after response. Add logic later to hang up based on conversation.
        gather = Gather(
            input="speech",
            action=url_for("twilio_bp.process_speech", _external=True),
            method="POST",
            speechTimeout="auto",
            speechModel="phone_call",
            enhanced=True
        )
        response.append(gather)
        response.redirect(url_for("twilio_bp.handle_incoming_call", _external=True), method="POST") # Fallback redirect

    except Exception as e:
        logger.error(f"Error during voice processing for call {call_sid}: {e}", exc_info=True)
        response.say("I encountered an unexpected error processing your request. Please try calling back later.", voice="Polly.Joanna")
        response.hangup()

    return Response(str(response), mimetype="text/xml")

# --- SMS Webhook --- 

@twilio_bp.route("/sms", methods=["POST"])
def handle_incoming_sms():
    """Handles incoming SMS messages via the Orchestration Service."""
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", None)
    logger.info(f"Incoming SMS received from {from_number}: {incoming_msg}")

    response = MessagingResponse()

    if not from_number:
        logger.error("Received SMS without a 'From' number.")
        # Cannot reply without a number
        return Response(str(response), mimetype="text/xml")

    if not incoming_msg:
        logger.warning(f"Received empty SMS from {from_number}. Sending default reply.")
        response.message("Sorry, I didn't understand that. Could you please rephrase your message?")
        return Response(str(response), mimetype="text/xml")

    try:
        # 1. Call Orchestration Service to handle the interaction
        assistant_response_text = orchestration_service.handle_interaction(from_number, incoming_msg)

        # 2. Send response via SMS
        response.message(assistant_response_text)
        logger.info(f"Sending SMS reply to {from_number}: {assistant_response_text[:50]}...")

    except Exception as e:
        logger.error(f"Error during SMS processing for {from_number}: {e}", exc_info=True)
        response.message("I encountered an unexpected internal error. Please try again later.")

    return Response(str(response), mimetype="text/xml")

# --- Route for serving TTS audio files --- 
# This needs to be properly configured in the main Flask app (create_app)
# to serve files from the instance/tts_audio directory.
@twilio_bp.route("/tts_audio/<filename>")
def serve_tts_audio(filename):
    """Serves the generated TTS audio files."""
    # IMPORTANT: Add security checks here if needed (e.g., validate filename)
    audio_dir = tts_service.TTS_AUDIO_DIR
    logger.info(f"Attempting to serve TTS audio file: {filename} from {audio_dir}")
    try:
        # Ensure the directory path is absolute for send_from_directory
        abs_audio_dir = os.path.abspath(audio_dir)
        return send_from_directory(abs_audio_dir, filename, mimetype="audio/mpeg")
    except FileNotFoundError:
        logger.error(f"TTS audio file not found: {filename}")
        return "File not found", 404
    except Exception as e:
        logger.error(f"Error serving TTS audio file {filename}: {e}", exc_info=True)
        return "Internal server error", 500

