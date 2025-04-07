import os
import gradio as gr
import base64
import requests
import hashlib
from dotenv import load_dotenv
from PIL import Image as PILImage
from tanjiro_cli import TanjiroChatbot, read_api_key_from_example
from meme_search import MemeSearcher
from memory_agent import MemoryAgent

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = read_api_key_from_example()

# Initialize components
memory_agent = MemoryAgent(api_key=api_key, max_entries=10)
tanjiro = TanjiroChatbot(api_key=api_key, memory_agent=memory_agent)
meme_searcher = MemeSearcher()

conversation_history = []
current_memes = []
current_meme_index = 0
current_meme_topic = ""

# --- Utility Functions ---
def clean_reddit_url(url):
    if "preview.redd.it" in url:
        direct_url = url.split("?")[0].replace("preview.redd.it", "i.redd.it")
        if not any(ext in direct_url for ext in [".jpg", ".jpeg", ".png", ".gif"]):
            direct_url += ".jpg"
        return direct_url
    return url

def is_valid_reddit_image_url(url):
    invalid_hosts = ["external-preview.redd.it", "external-i.redd.it"]
    return all(host not in url for host in invalid_hosts)

def download_image(url, cache_dir="image_cache"):
    if not is_valid_reddit_image_url(url):
        print("Invalid Reddit image URL")
        return None
    try:
        os.makedirs(cache_dir, exist_ok=True)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = os.path.splitext(url)[-1] or ".jpg"
        cache_path = os.path.join(cache_dir, f"{url_hash}{ext}")
        if os.path.exists(cache_path):
            return cache_path
        headers = {"User-Agent": "Mozilla/5.0"}
        with requests.get(url, headers=headers, stream=True, timeout=10) as r:
            r.raise_for_status()
            with open(cache_path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        return cache_path
    except Exception as e:
        print(f"Download error: {e}")
        return None

def image_to_base64(image_path):
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        mime = "image/png" if image_path.endswith(".png") else "image/jpeg"
        return f"data:{mime};base64,{encoded}"
    except Exception as e:
        print(f"Base64 error: {e}")
        return None

def format_interests_for_display(analysis):
    ds = analysis.get("demon_slayer_topics", {})
    general = analysis.get("general_topics", {})
    result = "📚 **Tanjiro's Understanding of Your Interests**:\n\n"
    if not ds and not general:
        return result + "_I haven't identified any specific topics yet._"
    if ds:
        result += "🔸 **Demon Slayer Topics**:\n"
        for topic, weight in sorted(ds.items(), key=lambda x: x[1], reverse=True):
            stars = "★" * int(weight)
            result += f"- {topic}: {stars} ({weight})\n"
    if general:
        result += "\n🔹 **General Topics**:\n"
        for topic, weight in sorted(general.items(), key=lambda x: x[1], reverse=True):
            stars = "★" * int(weight)
            result += f"- {topic}: {stars} ({weight})\n"
    if "summary" in analysis:
        result += f"\n🧠 **Summary**:\n{analysis['summary']}"
    return result

# --- Core Chat Logic ---
def respond(message, chat_history):
    global current_memes, current_meme_index, current_meme_topic, conversation_history
    if not message.strip():
        return chat_history, gr.update(value="")

    if message.lower() == "interests":
        try:
            analysis = memory_agent.analyze_user_interests()
            response = format_interests_for_display(analysis)
        except Exception as e:
            response = f"Error analyzing interests: {str(e)}"
        chat_history.append((message, response))
        conversation_history.append((message, response))
        return chat_history, gr.update(value="")

    if message.lower().startswith("meme "):
        topic = message[5:].strip().lstrip("#")
        current_meme_topic = topic
        try:
            current_memes = meme_searcher.search_memes(topic, limit=5)
            if not current_memes:
                response = f"No memes found for **{topic}**."
                chat_history.append((message, response))
                conversation_history.append((message, response))
                return chat_history, gr.update(value="")
            meme = current_memes[0]
            cleaned_url = clean_reddit_url(meme.url)
            path = download_image(cleaned_url)
            base64_img = image_to_base64(path) if path else None
            response_text = f"**{meme.title}**\nSource: {meme.source or 'Reddit'}"
            if base64_img:
                html = f"{response_text}<br><img src='{base64_img}' alt='meme' style='max-width:100%'/>"
                chat_history.append((message, html))
                conversation_history.append((message, html))
            else:
                response = f"{response_text}\n{cleaned_url}"
                chat_history.append((message, response))
                conversation_history.append((message, response))
        except Exception as e:
            response = f"Error loading meme: {str(e)}"
            chat_history.append((message, response))
            conversation_history.append((message, response))
        return chat_history, gr.update(value="")

    try:
        memory_agent.record_interaction(message, None)
        current_convo = [(u, a) for u, a in chat_history]
        reply = tanjiro.generate_response(message, current_convo)
        memory_agent.record_interaction(message, reply)
        chat_history.append((message, reply))
        conversation_history.append((message, reply))
        return chat_history, gr.update(value="")
    except Exception as e:
        error = f"Tanjiro had trouble replying: {str(e)}"
        chat_history.append((message, error))
        conversation_history.append((message, error))
        return chat_history, gr.update(value="")

def clear_history():
    global conversation_history
    conversation_history = []
    return [], ""

# --- UI Layout ---
def create_web_interface():
    background_url = "https://wallpapers-clan.com/wp-content/uploads/2024/02/tanjiro-kamado-red-blue-flame-desktop-wallpaper-preview.jpg"
    css = f"""
    html, body {{
        margin: 0;
        padding: 0;
        height: 100%;
        width: 100%;
        background: url('{background_url}') no-repeat center center fixed;
        background-size: cover;
        font-family: 'Roboto', sans-serif;
    }}
    .gradio-container {{
        background-color: transparent !important;
        padding: 0 !important;
    }}
    .chatbot-wrap .message {{
        max-width: 50% !important;
    }}
    #right-panel {{
        position: fixed;
        top: 0;
        right: 0;
        width: 50%;
        height: 100%;
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(10px);
        padding: 20px;
        box-sizing: border-box;
        overflow-y: auto;
        z-index: 2;
    }}
    #reminder {{
        position: fixed;
        bottom: 20px;
        left: 20px;
        width: 340px;
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 15px;
        font-size: 14px;
        overflow-y: auto;
        line-height: 1.6;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        color: #222;
        z-index: 100;
    }}
    """

    with gr.Blocks(css=css) as demo:
        gr.HTML("""
        <div id="reminder">
            <b>Talk with Kamado Tanjiro from Demon Slayer!</b><br><br>
            📜 <code>history</code> – view conversation history<br>
            🎯 <code>interests</code> – learn what Tanjiro knows about you<br>
            😄 Try: <code>meme nezuko</code> or <code>meme #tanjiro</code><br>
            🔁 Use <code>next meme</code> or <code>previous meme</code><br>
            🧠 Add memes: <code>add meme topic | title | source | type | url | tags</code>
        </div>
        """)

        with gr.Column(elem_id="right-panel"):
            chatbot = gr.Chatbot(label="Conversation with Tanjiro", elem_classes="chatbot-wrap", bubble_full_width=False)
            msg = gr.Textbox(placeholder="Type your message here...", show_label=False, lines=1)
            with gr.Row():
                submit = gr.Button("Submit")
                clear = gr.Button("Clear History")

            msg.submit(fn=respond, inputs=[msg, chatbot], outputs=[chatbot, msg])
            submit.click(fn=respond, inputs=[msg, chatbot], outputs=[chatbot, msg])
            clear.click(fn=clear_history, inputs=None, outputs=[chatbot, msg], queue=False)

            gr.Examples(
                examples=[
                    "Hello Tanjiro, how are you?",
                    "Tell me about Nezuko.",
                    "meme #tanjiro",
                    "meme nezuko",
                    "interests"
                ],
                inputs=msg
            )

    return demo



# Launch the app
if __name__ == "__main__":
    print("Starting Tanjiro chatbot...")
    demo = create_web_interface()
    demo.launch(server_name="127.0.0.1", server_port=7866, share=True, inbrowser=True)
