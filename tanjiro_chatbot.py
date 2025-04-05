import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import gradio as gr

class TanjiroChatbot:
    def __init__(self):
        self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # Tanjiro's personality prompt
        self.system_prompt = """You are Kamado Tanjiro from Demon Slayer. You are kind, determined, and always willing to help others. 
        You speak with respect and use honorifics. You often talk about your family, especially your sister Nezuko, 
        and your mission to turn her back into a human. You believe in the power of kindness and never give up, 
        even in the face of overwhelming odds. You use phrases like "I'll do my best!" and "I won't give up!"
        
        Respond as Tanjiro would, maintaining his personality and speech patterns."""

    def generate_response(self, user_input, history):
        # Construct the conversation history
        conversation = self.system_prompt + "\n\n"
        for human, assistant in history:
            conversation += f"Human: {human}\nAssistant: {assistant}\n\n"
        conversation += f"Human: {user_input}\nAssistant: "

        # Generate response
        inputs = self.tokenizer(conversation, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            **inputs,
            max_length=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = response.split("Assistant: ")[-1].strip()
        
        return response

def create_chatbot_interface():
    chatbot = TanjiroChatbot()
    
    def respond(message, history):
        return chatbot.generate_response(message, history)
    
    # Create Gradio interface
    interface = gr.ChatInterface(
        respond,
        title="Chat with Tanjiro",
        description="Have a conversation with Kamado Tanjiro from Demon Slayer!",
        examples=[
            "How are you doing today?",
            "Tell me about your sister Nezuko.",
            "What's your mission as a Demon Slayer?",
        ],
        theme="soft"
    )
    
    return interface

if __name__ == "__main__":
    interface = create_chatbot_interface()
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True
    ) 