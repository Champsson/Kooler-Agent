from flask import Blueprint, request, jsonify
from app.services.conversation_service import process_conversation
from app.utils import logger

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/chat', methods=['POST'])
def chat_endpoint():
    """API endpoint for direct chat interactions"""
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    # Process the conversation with the AI assistant
    response = process_conversation(message, mode='api')
    
    return jsonify({"response": response})

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200
