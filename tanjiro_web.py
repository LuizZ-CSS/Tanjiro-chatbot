import os
import gradio as gr
from typing import List, Tuple, Dict
from dotenv import load_dotenv
from memory_agent import MemoryAgent
from tanjiro_cli import TanjiroChatbot, read_api_key_from_example

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables or .env.example file
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "123456":
    api_key = read_api_key_from_example()

# Initialize the memory agent
memory_agent = MemoryAgent(api_key=api_key, max_entries=10)

# Initialize the chatbot with the memory agent
tanjiro = TanjiroChatbot(api_key=api_key, memory_agent=memory_agent)

# Store conversation history
conversation_history = []

def format_history_for_display(entries):
    """Format history entries for display in the chatbot"""
    history_text = "Recent Conversation History:\n\n"
    for i, entry in enumerate(entries, 1):
        history_text += f"[{i}] You: {entry['user_input']}\n"
        history_text += f"    Tanjiro: {entry['response']}\n\n"
    return history_text

def format_interests_for_display(analysis):
    """Format interests analysis for display in the chatbot"""
    ds_topics = analysis.get("demon_slayer_topics", {})
    gen_topics = analysis.get("general_topics", {})
    
    interests_text = "Tanjiro's Understanding of Your Interests:\n\n"
    
    if not ds_topics and not gen_topics:
        interests_text += "I haven't identified any specific topics of interest yet."
    else:
        # Display Demon Slayer topics if available
        if ds_topics:
            interests_text += "Demon Slayer Topics:\n"
            for topic, weight in sorted(ds_topics.items(), key=lambda x: x[1], reverse=True):
                stars = "★" * int(weight)
                interests_text += f"- {topic.capitalize()}: {stars} ({weight})\n"
            interests_text += "\n"
                
        # Display general topics if available
        if gen_topics:
            interests_text += "General Topics:\n"
            for topic, weight in sorted(gen_topics.items(), key=lambda x: x[1], reverse=True):
                stars = "★" * int(weight)
                interests_text += f"- {topic.capitalize()}: {stars} ({weight})\n"
            interests_text += "\n"
        
        # Display analysis summary if available
        if "summary" in analysis:
            interests_text += "Summary:\n"
            interests_text += analysis["summary"]
    
    return interests_text

def respond(message, chat_history):
    """Process user message and generate response from Tanjiro"""
    global conversation_history
    
    # Base case - empty message
    if not message or message.strip() == "":
        return chat_history, ""
    
    # Special commands
    if message.lower() == 'history':
        # For the web UI, we'll return the history as a message
        entries = memory_agent.get_recent_entries()
        if not entries:
            response = "No conversation history available."
        else:
            response = format_history_for_display(entries)
            
        # Add to the chat history in tuple format
        chat_history.append((message, response))
        return chat_history, ""
    
    elif message.lower() == 'interests':
        # Generate interests analysis and return as a message
        try:
            analysis = memory_agent.analyze_user_interests()
            response = format_interests_for_display(analysis)
        except Exception as e:
            response = f"Error analyzing interests: {str(e)}"
        
        # Add to the chat history in tuple format
        chat_history.append((message, response))
        return chat_history, ""
    
    # Normal message processing
    try:
        # Convert Gradio history format to our format for processing
        current_conversation = []
        for user_msg, bot_msg in chat_history:
            current_conversation.append((user_msg, bot_msg))
        
        # Generate response
        response = tanjiro.generate_response(message, current_conversation)
        
        # Update our internal conversation history
        conversation_history.append((message, response))
        
        # Record interaction in memory agent
        memory_agent.record_interaction(message, response)
        
        # Add to the chat history in tuple format
        chat_history.append((message, response))
        return chat_history, ""
    
    except Exception as e:
        error_msg = f"I apologize, but I encountered an error: {str(e)}"
        chat_history.append((message, error_msg))
        return chat_history, ""

def clear_history():
    """Clear the chat history"""
    return [], ""

# Create the Gradio interface
def create_web_interface():
    """Create and configure the web interface using Gradio"""
    
    # Create the interface with individual components
    with gr.Blocks() as interface:
        gr.Markdown("## Chat with Tanjiro from Demon Slayer")
        
        # Add CSS as a separate stylesheet
        gr.Markdown(f"""
        <style>
        .gradio-container {{
            font-family: 'Roboto', sans-serif;
        }}
        footer {{display: none !important;}}
        .chatbot .user {{
            background-color: #e6f7ff;
        }}
        .chatbot .bot {{
            background-color: #ffe6e6;
        }}
        img {{
            max-width: 100%;
            max-height: 400px;
            border-radius: 10px;
            margin: 10px 0;
            display: block;
        }}
        .message-image {{
            max-width: 100%;
            max-height: 400px;
            border-radius: 10px;
            margin: 10px 0;
        }}
        </style>
        """)
        
        gr.Markdown("""Talk with Kamado Tanjiro from Demon Slayer!
        - Type 'history' to see your conversation history
        - Type 'interests' to see what Tanjiro thinks you're interested in
        - Type 'meme [topic]' to request a specific meme (e.g., 'meme nezuko')
        - Tanjiro will occasionally share memes related to your conversation!
        """)
        
        chatbot = gr.Chatbot(label="Conversation with Tanjiro")
        msg = gr.Textbox(
            placeholder="Type your message here...",
            show_label=False,
            container=False
        )
        clear = gr.Button("Clear")
        
        # Add example queries
        gr.Examples(
            examples=[
                "Hello Tanjiro, how are you today?",
                "Tell me about your sister Nezuko.",
                "What's your mission as a Demon Slayer?",
                "What breathing technique do you use?",
                "history",
                "interests"
            ],
            inputs=msg
        )
        
        # Set up the interaction
        msg.submit(fn=respond, inputs=[msg, chatbot], outputs=[chatbot, msg])
        clear.click(fn=clear_history, inputs=None, outputs=[chatbot, msg], queue=False)
        
    return interface

# Launch the web interface
if __name__ == "__main__":
    # Debug API key status
    if api_key:
        print("API key loaded successfully")
    else:
        print("Warning: No API key found")
        
    web_interface = create_web_interface()
    web_interface.launch(
        server_name="127.0.0.1",  # Use localhost instead of 0.0.0.0 
        server_port=7861,         # Use port 7861 instead of 7860
        share=False,              # Don't create a public URL
        inbrowser=True            # Opens in browser automatically
    ) 