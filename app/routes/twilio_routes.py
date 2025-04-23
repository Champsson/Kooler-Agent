import os
import tempfile
from flask import Blueprint, request, Response, url_for
from twilio.twiml.voice_response import VoiceResponse
from twilio.twiml.messaging_response import MessagingResponse
import openai
from app.services.conversation_service import process_conversation
from app.services.tts_service import text_to_speech
from app.utils import logger

twilio_bp = Blueprint('twilio', __name__, url_prefix='/twilio')

@twilio_bp.route('/voice', methods=['POST'])
def voice_webhook():
    """Handle incoming voice calls from Twilio"""
    response = VoiceResponse()
    
    # Initial greeting with minimal latency
    response.say("Thank you for calling Kooler Garage Doors. I'm processing your request.")
    
    # Gather speech input
    gather = response.gather(
        input='speech',
        action='/twilio/voice/process',
        method='POST',
        speechTimeout='auto',
        speechModel='phone_call'
    )
    gather.say("How can I help you today?")
    
    return Response(str(response), mimetype='text/xml')

@twilio_bp.route('/voice/process', methods=['POST'])
def process_voice():
    """Process speech input from voice call"""
    speech_result = request.form.get('SpeechResult', '')
    
    # Initial acknowledgment with minimal latency
    response = VoiceResponse()
    response.say("I'm finding that information for you.", voice='alice')
    
    # Process the conversation with the AI assistant
    ai_response = process_conversation(speech_result, mode='voice')
    
    # Convert AI response to speech using OpenAI TTS
    voice_type = "nova"  # Options: alloy, echo, fable, onyx, nova, shimmer
    speech_file = text_to_speech(ai_response, voice=voice_type)
    
    if speech_file:
        # Create a publicly accessible URL for the audio file
        # In production, you'd use proper file hosting
        # For development, we'll use a simple approach
        audio_url = url_for('static', filename=os.path.basename(speech_file), _external=True)
        
        # Move the file to the static directory
        os.makedirs('app/static', exist_ok=True)
        os.rename(speech_file, f"app/static/{os.path.basename(speech_file)}")
        
        # Play the audio file
        response.play(audio_url)
    else:
        # Fallback to Twilio TTS if OpenAI TTS fails
        response.say(ai_response, voice='alice')
    
    # Add gather for continued conversation
    gather = response.gather(
        input='speech',
        action='/twilio/voice/process',
        method='POST',
        speechTimeout='auto',
        speechModel='phone_call'
    )
    gather.say("Is there anything else I can help you with?", voice='alice')
    
    return Response(str(response), mimetype='text/xml')

@twilio_bp.route('/sms', methods=['POST'])
def sms_webhook():
    """Handle incoming SMS messages from Twilio"""
    incoming_msg = request.form.get('Body', '')
    
    # Process the conversation with the AI assistant
    ai_response = process_conversation(incoming_msg, mode='sms')
    
    # Create TwiML response
    response = MessagingResponse()
    response.message(ai_response)
    
    return Response(str(response), mimetype='text/xml')

@twilio_bp.route('/voice-memo', methods=['POST'])
def voice_memo_webhook():
    """Handle incoming voice memos from Twilio"""
    # Get the URL of the voice memo
    media_url = request.form.get('MediaUrl0', '')
    
    if not media_url:
        response = MessagingResponse()
        response.message("Sorry, I couldn't process your voice memo.")
        return Response(str(response), mimetype='text/xml')
    
    # Download the voice memo
    import requests
    audio_data = requests.get(media_url).content
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_filename = temp_file.name
    temp_file.write(audio_data)
    temp_file.close()
    
    # Transcribe using OpenAI Whisper
    try:
        with open(temp_filename, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        
        # Get the transcribed text
        transcribed_text = transcript.text
        
        # Process with AI assistant
        ai_response = process_conversation(transcribed_text, mode='sms')
        
        # Send response
        response = MessagingResponse()
        response.message(ai_response)
        
        return Response(str(response), mimetype='text/xml')
    
    except Exception as e:
        logger.error(f"Error processing voice memo: {str(e)}")
        response = MessagingResponse()
        response.message("I'm sorry, I had trouble understanding your voice memo. Could you please try again or send a text message?")
        return Response(str(response), mimetype='text/xml')
    finally:
        # Clean up temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
@twilio_bp.route('/voice/fallback', methods=['POST'])
def voice_fallback():
    """Fallback handler for voice calls when primary handler fails"""
    response = VoiceResponse()
    
    # Initial message explaining the situation
    response.say("We apologize, but our system is temporarily unavailable. We'd like to collect your information for a callback when our system is back online.")
    
    # Gather the caller's information
    gather = response.gather(
        input='speech dtmf',
        num_digits=10,
        action='/twilio/voice/fallback/process',
        method='POST',
        timeout=5,
        speech_timeout='auto'
    )
    gather.say("Please say your name and phone number after the tone, or press any key to skip.")
    
    # If they don't provide input, give them another option
    response.say("We didn't receive your information. Please call our main office for immediate assistance. Thank you for your patience.")
    
    return Response(str(response), mimetype='text/xml')

@twilio_bp.route('/voice/fallback/process', methods=['POST'])
def process_voice_fallback():
    """Process the caller's information from the fallback handler"""
    response = VoiceResponse()
    
    # Get the caller's input
    caller_input = request.form.get('SpeechResult', '')
    caller_number = request.form.get('From', 'unknown')
    
    # Log the information for follow-up
    logger.info(f"Fallback callback request - From: {caller_number}, Info: {caller_input}")
    
    # Thank the caller
    response.say("Thank you for your information. A representative will call you back as soon as our system is back online. We appreciate your patience.")
    
    return Response(str(response), mimetype='text/xml')

@twilio_bp.route('/sms/fallback', methods=['POST'])
def sms_fallback():
    """Fallback handler for SMS when primary handler fails"""
    response = MessagingResponse()
    
    # Add a message explaining the situation and requesting information
    response.message("We apologize, but our system is temporarily unavailable. Please reply with your name and a brief message, and a representative will contact you when our system is back online.")
    
    return Response(str(response), mimetype='text/xml')
