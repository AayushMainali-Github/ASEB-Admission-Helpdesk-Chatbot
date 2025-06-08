from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv
import google.generativeai as genai
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Chat History Model
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    summary = db.Column(db.String(80), nullable=True)  # New: short summary for chat

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'message': self.message,
            'response': self.response,
            'timestamp': self.timestamp.isoformat(),
            'summary': self.summary
        }

# Initialize database
with app.app_context():
    db.drop_all()  # Drop all tables
    db.create_all()  # Create new tables

# Configure Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# System prompt for the chatbot
SYSTEM_PROMPT = """You are an AI assistant for Amrita Vishwa Vidyapeetham Bengaluru Campus. Your primary role is to provide accurate information from the provided content about admissions, programs, and campus details.

Guidelines:
1. ALWAYS use the provided content as your primary source of information.
2. Provide direct answers from the content without referring users to the admissions office unless the information is not available in the content.
3. Be friendly but concise. Greet users only once at the start of the conversation.
4. For specific questions about:
   - Programs and branches: List all available programs from the content
   - Fee structure: Provide the exact fee details from the content
   - Admission process: Explain the process using the content
   - Campus facilities: Describe what's available based on the content
   - Placements: Share the companies and salary information from the content
5. If information is not in the content, only then suggest contacting the admissions office.
6. For unclear questions:
   - Ask for clarification
   - Use chat history to understand context
   - Connect related questions to maintain conversation flow
7. Keep responses focused and to the point, using information directly from the content.
8. Never make up information that's not in the content.
9. When listing information, use bullet points or numbered lists for clarity.
10. **Always format tables and lists using Markdown syntax so they render properly in the chat interface.**
11. Include specific details like fees, dates, and requirements when available in the content."""

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        session_id = data.get('session_id')

        if not user_message or not session_id:
            return jsonify({'error': 'Message and session_id are required'}), 400

        # Get chat history for context
        chat_history = ChatHistory.query.filter_by(session_id=session_id).order_by(ChatHistory.timestamp).all()
        context = "\n".join([f"User: {msg.message}\nAssistant: {msg.response}" for msg in chat_history[-5:]]) if chat_history else ""

        # Read content file
        with open('content.txt', 'r', encoding='utf-8') as f:
            content = f.read()

        # Generate response
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nReference Content:\n{content}\n\nPrevious conversation:\n{context}\n\nUser: {user_message}"
        )

        # Generate summary if this is the first message in the session
        summary = None
        if not chat_history:
            summary = ' '.join(user_message.split()[:6])

        # Save to database
        chat_entry = ChatHistory(
            session_id=session_id,
            message=user_message,
            response=response.text,
            summary=summary
        )
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({
            'response': response.text,
            'timestamp': chat_entry.timestamp.isoformat()
        })

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    try:
        chat_history = ChatHistory.query.filter_by(session_id=session_id).order_by(ChatHistory.timestamp).all()
        return jsonify([chat.to_dict() for chat in chat_history])
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/sessions', methods=['GET'])
def get_chat_sessions():
    try:
        # Get unique session IDs with their latest message and summary
        sessions = db.session.query(
            ChatHistory.session_id,
            db.func.max(ChatHistory.timestamp).label('last_activity'),
            db.func.max(ChatHistory.summary).label('summary')
        ).group_by(ChatHistory.session_id).all()
        
        return jsonify([{
            'session_id': session[0],
            'last_activity': session[1].isoformat(),
            'summary': session[2]
        } for session in sessions])
    except Exception as e:
        logger.error(f"Error getting chat sessions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/session/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    try:
        ChatHistory.query.filter_by(session_id=session_id).delete()
        db.session.commit()
        return jsonify({'message': 'Chat session deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 