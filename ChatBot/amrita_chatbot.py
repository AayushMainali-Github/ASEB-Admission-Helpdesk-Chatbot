import google.generativeai as genai
import os
from typing import List, Dict
import json
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AmritaAdmissionBot:
    def __init__(self, api_key: str):
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Load content
        self.content = self.load_content()
        
        # Initialize chat history
        self.chat_history = []
        
        # Create system prompt
        self.system_prompt = """You are an AI assistant for Amrita Vishwa Vidyapeetham's Bengaluru Campus Admission Help Desk. 
        Your role is to provide accurate information about admissions, programs, and campus details.
        
        Important guidelines:
        1. For general questions (greetings, how are you, etc.):
           - Be friendly but concise
           - Only greet once at the start of conversation
           - Get straight to the point
        
        2. For specific questions about Amrita Bengaluru:
           - First check if you have the information
           - If you don't have specific details, provide contact information:
             "For this information, please contact the admission office at:
             Email: admissions@blr.amrita.edu
             Phone: +91-80-2844 0000
             Website: https://www.amrita.edu/campus/bengaluru"
        
        3. For admission-related queries:
           - Always mention the official admission portal
           - Emphasize that Amrita doesn't use agents or third-party consultants
        
        4. Be clear that you only have information about the Bengaluru campus
        
        5. Use chat history for context:
           - If a question is unclear, use previous questions for context
           - If someone asks for "more details" or "explain", refer to the last topic discussed
           - Maintain conversation flow by connecting related questions
        
        Remember: Be direct and concise. Use chat history to provide context-aware responses."""
        
    def load_content(self) -> str:
        """Load the content from the file."""
        try:
            with open('content.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logging.error("Content file not found!")
            return ""
            
    def get_response(self, user_query: str) -> str:
        """Get response from the model."""
        try:
            # Add user query to chat history
            self.chat_history.append({"role": "user", "content": user_query})
            
            # Create the full prompt with chat history
            chat_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.chat_history[-5:]])  # Last 5 messages for context
            
            full_prompt = f"""Content about Amrita Bengaluru Campus:
            {self.content}
            
            Recent conversation:
            {chat_context}
            
            Current User Query: {user_query}
            
            Please provide a response:
            1. For general questions (greetings, how are you, etc.):
               - Be friendly but concise
               - Get straight to the point
            
            2. For specific questions about Amrita Bengaluru:
               - First check if you have the information
               - If you don't have specific details, provide contact information:
                 "For this information, please contact the admission office at:
                 Email: admissions@blr.amrita.edu
                 Phone: +91-80-2844 0000
                 Website: https://www.amrita.edu/campus/bengaluru"
            
            3. For unclear or follow-up questions:
               - Use the recent conversation above to understand context
               - If someone asks for "more details" or "explain", refer to the last topic
               - If still unclear, ask for clarification while mentioning the last topic discussed
            
            Keep responses direct and concise. Use the conversation history to maintain context."""
            
            # Get response from model
            response = self.model.generate_content(full_prompt)
            response_text = response.text
            
            # Add response to chat history
            self.chat_history.append({"role": "assistant", "content": response_text})
            
            return response_text
            
        except Exception as e:
            logging.error(f"Error getting response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request. Please try again or contact the official admission channels."

def main():
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Please set the GOOGLE_API_KEY in your .env file or environment variables")
        print("You can create a .env file with the following content:")
        print("GOOGLE_API_KEY=your_api_key_here")
        return
        
    # Initialize bot
    bot = AmritaAdmissionBot(api_key)
    
    print("Welcome to Amrita Bengaluru Campus Admission Help Desk!")
    print("Type 'quit' to exit")
    print("-" * 50)
    
    while True:
        user_input = input("\nYour question: ").strip()
        
        if user_input.lower() == 'quit':
            print("\nThank you for using Amrita Bengaluru Campus Admission Help Desk!")
            break
            
        if not user_input:
            continue
            
        response = bot.get_response(user_input)
        print("\nResponse:", response)

if __name__ == "__main__":
    main() 