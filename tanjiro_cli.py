import os
import openai
import json
from typing import List, Tuple
from dotenv import load_dotenv
from memory_agent import MemoryAgent

# Function to read API key from .env.example file
def read_api_key_from_example():
    try:
        with open('.env.example', 'r') as file:
            content = file.read().strip()
            # Extract the API key from the file
            if '=' in content:
                return content.split('=', 1)[1].strip()
    except Exception as e:
        print(f"Error reading .env.example: {e}")
    return None

# Load environment variables from .env file
load_dotenv()

class TanjiroChatbot:
    def __init__(self, api_key: str = None, memory_agent: MemoryAgent = None):
        if not api_key:
            print("\nWarning: No API key provided!")
            print("Using placeholder or attempting to read from .env.example")
        
        # Use older openai API style
        openai.api_key = api_key
        self.memory_agent = memory_agent
        
        self.system_prompt = """You are Kamado Tanjiro from Demon Slayer. You are kind, determined, and always willing to help others. 
        You speak with respect and use honorifics. You often talk about your family, especially your sister Nezuko, 
        and your mission to turn her back into a human. You believe in the power of kindness and never give up, 
        even in the face of overwhelming odds. You use phrases like "I'll do my best!" and "I won't give up!"
        
        Respond as Tanjiro would, maintaining his personality and speech patterns."""

    def generate_response(self, user_input: str, conversation_history: List[Tuple[str, str]]) -> str:
        # Construct the conversation history
        system_message = self.system_prompt
        
        # Add context from memory agent if available
        if self.memory_agent:
            context = self.memory_agent.generate_context_for_tanjiro()
            if context:
                system_message += f"\n\n{context}"
        
        messages = [{"role": "system", "content": system_message}]
        
        # Add conversation history
        for human, assistant in conversation_history:
            messages.append({"role": "user", "content": human})
            messages.append({"role": "assistant", "content": assistant})
        
        # Add the current user input
        messages.append({"role": "user", "content": user_input})
        
        try:
            # Generate response using OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message['content'].strip()
            
        except Exception as e:
            if "auth" in str(e).lower() or "api key" in str(e).lower():
                return "Error: Invalid or missing API key. Please check your API key and try again."
            else:
                return f"I apologize, but I encountered an error: {str(e)}"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_welcome():
    clear_screen()
    print("=" * 50)
    print("Welcome to Chat with Tanjiro!")
    print("=" * 50)
    print("\nYou can now chat with Kamado Tanjiro from Demon Slayer!")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("Type 'clear' to clear the screen.")
    print("Type 'history' to see your recent conversation history.")
    print("Type 'interests' to see what Tanjiro thinks you're interested in.")
    print("-" * 50 + "\n")

def main():
    # Try to get API key from environment or .env file
    api_key = os.getenv("OPENAI_API_KEY")
    
    # If not found or it's the placeholder, try to read from .env.example
    if not api_key or api_key == "123456":
        api_key = read_api_key_from_example()
    
    # Initialize the memory agent
    memory_agent = MemoryAgent(api_key=api_key, max_entries=10)
    
    print_welcome()
    
    # Initialize the chatbot with the memory agent
    tanjiro = TanjiroChatbot(api_key=api_key, memory_agent=memory_agent)
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for special commands
            if user_input.lower() in ['exit', 'quit']:
                print("\nTanjiro: Thank you for chatting with me! Take care!")
                break
            elif user_input.lower() == 'clear':
                print_welcome()
                continue
            elif user_input.lower() == 'history':
                memory_agent.display_history()
                continue
            elif user_input.lower() == 'interests':
                memory_agent.display_interests()
                continue
            elif not user_input:
                continue
                
            # Generate and print response
            response = tanjiro.generate_response(user_input, conversation_history)
            print(f"\nTanjiro: {response}")
            
            # Update conversation history
            conversation_history.append((user_input, response))
            
            # Record interaction in memory agent
            memory_agent.record_interaction(user_input, response)
            
        except KeyboardInterrupt:
            print("\n\nTanjiro: Oh! You're leaving? Take care!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try again.")

if __name__ == "__main__":
    main() 