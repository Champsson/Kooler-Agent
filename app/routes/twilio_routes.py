import os
import time
import tempfile
import threading
import re
import concurrent.futures
from flask import Blueprint, request, Response, url_for
from twilio.twiml.voice_response import VoiceResponse
from twilio.twiml.messaging_response import MessagingResponse
import openai
from app.services.conversation_service import process_conversation
from app.services.tts_service import get_cached_tts
from app.utils import timer_decorator, logger

# Caches for in-progress responses
RESPONSE_CACHE = {}  # Cache for in-progress responses
CHUNK_CACHE = {}  # Cache for response chunks

twilio_bp = Blueprint('twilio', __name__, url_prefix='/twilio')

def chunk_response(text, max_length=100):
    """Break response into smaller chunks at sentence boundaries"""
    if len(text) <= max_length:
        return [text]
    
    # Split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += " " + sentence if current_chunk else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def process_and_respond(speech_result, call_sid):
    """Process speech input and prepare response in background"""
    # Process with AI assistant
    ai_response = process_conversation(speech_result, mode='voice')
    
    # Break response into chunks
    chunks = chunk_response(ai_response)
    
    # Process all chunks in parallel
    s3_urls = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_chunk = {executor.submit(get_cached_tts, chunk, "nova"): chunk for chunk in chunks}
        for future in concurrent.futures.as_completed(future_to_chunk):
            try:
                s3_url = future.result()
                if s3_url:
                    s3_urls.append(s3_url)
            except Exception as e:
                logger.error(f"Error processing chunk: {str(e)}")
    
    # Store in cache for retrieval
    RESPONSE_CACHE[call_sid] = s3_urls

@twilio_bp.route('/voice', methods=['POST'])
def voice_webhook():
    """Handle incoming voice calls from Twilio"""
    response = VoiceResponse()
    
    # Initial greeting with minimal latency
    # Use pre-generated OpenAI greeting stored in S3
    greeting_url = "https://kooler-agent-tts.s3.amazonaws.com/greeting.mp3"
    response.play(greeting_url) 

    
    # Gather speech input
    gather = response.gather(
        input='speech',
        action='/twilio/voice/process',
        method='POST',
        speechTimeout='auto',
        speechModel='phone_call'
    )
    
    return Response(str(response), mimetype='text/xml')

@twilio_bp.route('/voice/process', methods=['POST'])
def process_voice():
    """Process speech input from voice call"""
    speech_result = request.form.get('SpeechResult', '')
    call_sid = request.form.get('CallSid')
    
    if not speech_result:
        response = VoiceResponse()
        response.say("I'm sorry, I didn't catch that. Please try again.", voice='alice')
        return Response(str(response), mimetype='text/xml')
    
    # Start background processing
    threading.Thread(target=process_and_respond, args=(speech_result, call_sid)).start()
    
    # Immediate acknowledgment
    response = VoiceResponse()
    response.say("I'm finding that information for you.", voice='alice')
    
    # Redirect to continue endpoint which will check for the response
    response.redirect(f'/twilio/voice/continue?call_sid={call_sid}')
    
    return Response(str(response), mimetype='text/xml')

@twilio_bp.route('/voice/continue', methods=['GET', 'POST'])
def voice_continue():
    """Continue voice response when processing is complete"""
    call_sid = request.args.get('call_sid') or request.form.get('CallSid')
    
    response = VoiceResponse()
    
    # Check if response is ready
    if call_sid in RESPONSE_CACHE:
    s3_urls = RESPONSE_CACHE.pop(call_sid)
    
    # Add a short pause for better transition
    response.pause(length=0.5)
    
    # Play all audio files
    for s3_url in s3_urls:
        response.play(s3_url)

        
        # Add gather for continued conversation
        gather = response.gather(
            input='speech',
            action='/twilio/voice/process',
            method='POST',
            speechTimeout='auto',
            speechModel='phone_call'
        )
        gather.say("Is there anything else I can help you with?", voice='alice')
    else:
        # Response not ready yet, wait a bit and check again
        response.pause(length=1)
        response.redirect(f'/twilio/voice/continue?call_sid={call_sid}')
    
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
    response.say("We apologize, but our system is temporarily unavailable. We'd like to collect your information for a callback when our system is back online.", voice='alice')
    
    # Gather the caller's information
    gather = response.gather(
        input='speech dtmf',
        num_digits=10,
        action='/twilio/voice/fallback/process',
        method='POST',
        timeout=5,
        speech_timeout='auto'
    )
    gather.say("Please say your name and phone number after the tone, or press any key to skip.", voice='alice')
    
    # If they don't provide input, give them another option
    response.say("We didn't receive your information. Please call our main office for immediate assistance. Thank you for your patience.", voice='alice')
    
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
    response.say("Thank you for your information. A representative will call you back as soon as our system is back online. We appreciate your patience.", voice='alice')
    
    return Response(str(response), mimetype='text/xml')

@twilio_bp.route('/sms/fallback', methods=['POST'])
def sms_fallback():
    """Fallback handler for SMS when primary handler fails"""
    response = MessagingResponse()
    
    # Add a message explaining the situation and requesting information
    response.message("We apologize, but our system is temporarily unavailable. Please reply with your name and a brief message, and a representative will contact you when our system is back online.")
    
    return Response(str(response), mimetype='text/xml')
