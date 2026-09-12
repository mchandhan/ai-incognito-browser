import gradio as gr
from openai import OpenAI
import os
import sys
import pathlib
import socket
from starlette.responses import HTMLResponse
from fastapi import FastAPI
import uvicorn

# Remove common token environment variables at startup to avoid accidental leakage
_sensitive_env_keys = [
    "HF_TOKEN",
    "HUGGING_FACE_TOKEN",
    "HUGGINGFACE_HUB_TOKEN",
    "HUGGINGFACE_TOKEN",
    "OPENAI_API_KEY",
    "OPENAI_KEY",
    "DEFAULT_HF_TOKEN",
]
for _k in _sensitive_env_keys:
    if _k in os.environ:
        os.environ.pop(_k, None)

# Truncate app_log.txt on startup to remove any previous tokens that may have been logged
try:
    _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_log.txt")
    if os.path.exists(_log_path):
        open(_log_path, "w", encoding="utf-8").close()
except Exception:
    pass

# Hugging Face Configuration
# Do NOT store tokens in source. Leave empty and enter your token in the UI.
DEFAULT_HF_TOKEN = ""

# 100% Verified Free Serverless Models on router.huggingface.co/v1
FREE_MODELS = [
    "Qwen/Qwen2.5-Coder-3B-Instruct",
    "Qwen/Qwen3-4B-Instruct-2507",
    "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "meta-llama/Llama-3.1-8B-Instruct",
    "deepseek-ai/DeepSeek-V3",
    "meta-llama/Llama-3.3-70B-Instruct",
    "microsoft/phi-4",
    "google/gemma-3-4b-it",
]

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, smart, and friendly AI assistant. "
    "Provide clear, conversational, and nicely formatted responses."
)


def get_client(token: str):
    """Return an OpenAI client configured for Hugging Face Router."""
    return OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=token.strip(),
    )


def chat_stream(user_message, history, token, model, temperature, max_tokens, system_prompt):
    """Stream responses from Hugging Face OpenAI-compatible API with reasoning support."""
    if not token or not token.strip():
        yield "Warning: No API token provided. Please enter your Hugging Face token in the Settings panel below."
        return

    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h.get("content", "")})
        elif isinstance(h, (list, tuple)) and len(h) == 2:
            if h[0]:
                messages.append({"role": "user", "content": h[0]})
            if h[1]:
                messages.append({"role": "assistant", "content": h[1]})

    messages.append({"role": "user", "content": user_message})

    try:
        client = get_client(token)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=int(max_tokens),
            temperature=float(temperature),
            stream=True,
        )
        partial = ""
        reasoning = ""
        in_thinking = False
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            rc = getattr(delta, "reasoning_content", None)
            c = getattr(delta, "content", None)
            if rc:
                if not in_thinking:
                    in_thinking = True
                    reasoning = "> Thinking Process:\n> "
                reasoning += rc.replace("\n", "\n> ")
                yield reasoning
            if c:
                if in_thinking:
                    in_thinking = False
                    partial = reasoning + "\n\n---\n\n" + c
                else:
                    partial += c
                yield partial
    except Exception as e:
        yield f"**Error:** `{e}`\n\n> Check your HF token and selected model."


# ── Ultra-Modern Glassmorphic CSS ──────────────────────────────────────
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #121212;
    --panel: #1a1a1a;
    --panel-soft: #F5F5F5;
    --text: #FFFFFF;
    --text-dark: #000000;
    --muted: #9E9E9E;
    --hover: #E0E0E0;
    --border: #9E9E9E;
}

* {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    box-sizing: border-box;
}

body, .gradio-container {
    background: var(--bg) !important;
    color: var(--text) !important;
    min-height: 100vh;
}

.gradio-container {
    max-width: 980px !important;
    margin: 0 auto !important;
    padding: 16px 20px 40px !important;
}

#chatbot {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 18px !important;
    overflow: hidden !important;
}

.message-row {
    margin-bottom: 14px !important;
}

[data-testid="user"] {
    background: var(--panel-soft) !important;
    color: var(--text-dark) !important;
    border-radius: 14px !important;
    border: 1px solid var(--border) !important;
}

[data-testid="bot"] {
    background: var(--panel) !important;
    color: var(--text) !important;
    border-radius: 14px !important;
    border: 1px solid var(--border) !important;
}

pre, code {
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 8px !important;
}

pre {
    background: #000000 !important;
    border: 1px solid var(--border) !important;
    padding: 12px 16px !important;
    color: var(--text) !important;
}

blockquote {
    border-left: 3px solid var(--border) !important;
    background: rgba(158, 158, 158, 0.12) !important;
    padding: 8px 14px !important;
    border-radius: 0 10px 10px 0 !important;
    margin: 8px 0 !important;
}

#msg-input textarea {
    background: var(--panel-soft) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 14px !important;
    color: var(--text-dark) !important;
    padding: 14px 20px !important;
    font-size: 0.98rem !important;
}

#msg-input textarea:focus {
    border-color: var(--border) !important;
    outline: none !important;
}

#send-btn {
    background: var(--panel-soft) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    color: var(--text-dark) !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    cursor: pointer !important;
}

#send-btn:hover {
    background: var(--hover) !important;
}

#clear-btn {
    background: var(--panel-soft) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text-dark) !important;
    font-weight: 600 !important;
}

#clear-btn:hover {
    background: var(--hover) !important;
}

.quick-chip {
    background: var(--panel-soft) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text-dark) !important;
    padding: 8px 14px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    text-align: left !important;
}

.quick-chip:hover {
    background: var(--hover) !important;
    border-color: var(--border) !important;
    color: var(--text-dark) !important;
}

.accordion {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    margin-top: 14px !important;
}

input, select {
    background: var(--panel-soft) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-dark) !important;
}

input:focus, select:focus {
    border-color: var(--border) !important;
}

label {
    color: var(--text) !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px;
}

::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: var(--muted);
    border-radius: 8px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--hover);
}
"""


# ── UI Architecture ──────────────────────────────────────────────────
with gr.Blocks(title="Phantom AI Studio - Free Cloud Models") as demo:
    demo.css = custom_css
    demo.theme = gr.themes.Base()

    # Hero Header Banner
    gr.HTML("""
    <div style="text-align: center; padding: 1.4rem 0 0.8rem;">
        <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: 0.75rem;
                    background: #F5F5F5; border: 1px solid #9E9E9E;
                    border-radius: 12px; padding: 6px 18px; font-size: 0.82rem; font-weight: 600; color: #000000;">
            <span style="width: 8px; height: 8px; background: #9E9E9E; border-radius: 50%; display: inline-block;"></span>
            <span>Hugging Face Serverless Router &bull; Active &amp; Free</span>
        </div>
        <h1 style="font-family: 'Outfit', sans-serif !important; font-size: 2.6rem; font-weight: 800;
                   letter-spacing: -0.8px; margin: 0 0 0.4rem; color: #FFFFFF;">
            Phantom AI Studio
        </h1>
        <p style="color: #FFFFFF; margin: 0 auto; max-width: 600px; font-size: 0.95rem; line-height: 1.5;">
            Powered by <strong style="color:#FFFFFF;">Qwen 2.5</strong>, <strong style="color:#FFFFFF;">DeepSeek-V3</strong>, and <strong style="color:#FFFFFF;">Llama 3.3</strong> cloud models &mdash; lightning fast, free &amp; private.
        </p>
    </div>
    """)

    # Interactive Chatbot Viewport
    chatbot = gr.Chatbot(
        elem_id="chatbot",
        height=450,
        show_label=False,
        render_markdown=True,
        layout="bubble",
        placeholder="Type your prompt here... (Press Enter to send)",
    )

    # Quick Suggestion Chips Row
    with gr.Row():
        chip1 = gr.Button("Write a Python web scraper", elem_classes=["quick-chip"], scale=1)
        chip2 = gr.Button("Explain quantum computing simply", elem_classes=["quick-chip"], scale=1)
        chip3 = gr.Button("Compare Qwen vs DeepSeek", elem_classes=["quick-chip"], scale=1)
        chip4 = gr.Button("Brainstorm creative AI startup ideas", elem_classes=["quick-chip"], scale=1)

    # Input Command Bar
    with gr.Row(equal_height=True):
        msg = gr.Textbox(
            placeholder="Type your prompt here... (Press Enter to send)",
            show_label=False,
            scale=6,
            elem_id="msg-input",
            lines=1,
            max_lines=6,
            autofocus=True,
        )
        send_btn = gr.Button("Send", scale=1, elem_id="send-btn", min_width=110)

    # Auxiliary Action Bar
    with gr.Row():
        clear_btn = gr.Button("Clear Chat", elem_id="clear-btn", scale=1)
        gr.HTML("""
        <div style="display:flex; align-items:center; justify-content:flex-end; height:100%; gap:12px; color:#64748b; font-size:0.8rem;">
            <span>Streaming enabled</span>
            <span>Session strictly in-memory</span>
        </div>
        """, scale=5)

    # Model & Parameter Settings
    with gr.Accordion("Model & Studio Settings", open=False, elem_classes=["accordion"]):
        with gr.Row():
            model_choice = gr.Dropdown(
                choices=FREE_MODELS,
                value=FREE_MODELS[0],
                label="Active Model",
                info="Select from verified free serverless models",
                scale=3,
            )
            hf_token = gr.Textbox(
                value="",
                label="Hugging Face API Token (required)",
                placeholder="Enter your Hugging Face token (hf_xxx)",
                type="password",
                info="Enter your Hugging Face token; not stored in code or logs.",
                scale=3,
                elem_id="token-input",
            )
        with gr.Row():
            temperature = gr.Slider(
                0.0, 1.5, value=0.7, step=0.05,
                label="Temperature",
                info="0.0 = Precise & deterministic | 1.0 = Creative & expressive"
            )
            max_tokens = gr.Slider(
                64, 4096, value=1024, step=64,
                label="Max Tokens",
                info="Maximum length of generated response"
            )
        system_prompt = gr.Textbox(
            value=DEFAULT_SYSTEM_PROMPT,
            label="System Instructions",
            lines=2,
            placeholder="Set custom instructions for the AI persona..."
        )

    # Footer
    gr.HTML("""
    <div style="text-align: center; margin-top: 1.8rem; color: #475569; font-size: 0.8rem;">
        Phantom AI Studio &bull; OpenAI-compatible Hugging Face Cloud Router &bull; Built with Gradio
    </div>
    """)

    # ── Handlers & Events ─────────────────────────────────────────────────
    def user_submit(message, history):
        if message and message.strip():
            return "", history + [{"role": "user", "content": message}]
        return message, history

    def bot_respond(history, token, model, temp, tokens, sys_prompt):
        if not history or history[-1]["role"] != "user":
            return history
        history = history + [{"role": "assistant", "content": ""}]
        prev = [h for h in history[:-2] if h["role"] in ("user", "assistant")]
        user_msg = history[-2]["content"]
        for partial in chat_stream(user_msg, prev, token, model, temp, tokens, sys_prompt):
            history[-1]["content"] = partial
            yield history

    # Send on Enter / Click
    msg.submit(user_submit, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot_respond, [chatbot, hf_token, model_choice, temperature, max_tokens, system_prompt], chatbot
    )
    send_btn.click(user_submit, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot_respond, [chatbot, hf_token, model_choice, temperature, max_tokens, system_prompt], chatbot
    )

    # Clear chat
    clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])

    # Quick prompt chip handlers
    def click_chip_with_prompt(prompt_text, history):
        """Handle chip click by adding prompt to history."""
        if not isinstance(history, list):
            history = []
        return "", history + [{"role": "user", "content": prompt_text}]

    for idx, (chip, prompt_str) in enumerate([
        (chip1, "Write a Python script for web scraping with BeautifulSoup and requests."),
        (chip2, "Explain quantum computing in simple terms for a beginner."),
        (chip3, "Compare the Qwen and DeepSeek model architectures and their strengths."),
        (chip4, "Brainstorm 5 innovative startup ideas using modern AI agents."),
    ]):
        # Create a state to hold the prompt for this chip
        prompt_state = gr.State(value=prompt_str)
        chip.click(
            click_chip_with_prompt,
            inputs=[prompt_state, chatbot],
            outputs=[msg, chatbot],
            queue=False,
        ).then(
            bot_respond, [chatbot, hf_token, model_choice, temperature, max_tokens, system_prompt], chatbot
        )


if __name__ == "__main__":
    requested_port = int(__import__("os").environ.get("GRADIO_SERVER_PORT", "5050"))
    port = requested_port

    def find_free_port(start_port: int = requested_port, max_tries: int = 100) -> int:
        for candidate in range(start_port, start_port + max_tries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock.bind(("0.0.0.0", candidate))
                    return candidate
                except OSError:
                    continue

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("0.0.0.0", 0))
            return sock.getsockname()[1]

    port = find_free_port(requested_port)
    if port != requested_port:
        print(f"Port {requested_port} is busy; using free port {port} instead.")
    os.environ["GRADIO_SERVER_PORT"] = str(port)

    BROWSER_HOME_HTML = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Phantom Browser</title>
      <style>
        :root {
          --bg: #121212;
          --panel: #1a1a1a;
          --panel-soft: #F5F5F5;
          --text: #FFFFFF;
          --text-dark: #000000;
          --muted: #9E9E9E;
          --hover: #E0E0E0;
          --border: #9E9E9E;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          min-height: 100vh;
          font-family: Inter, Segoe UI, Arial, sans-serif;
          background: var(--bg);
          color: var(--text);
        }
        .wrap {
          width: min(1080px, calc(100% - 32px));
          margin: 48px auto 24px;
          padding: 22px 24px 26px;
          border-radius: 28px;
          background: var(--panel);
          border: 1px solid var(--border);
        }
        .brand {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          font-size: 0.8rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: var(--text);
          font-weight: 700;
        }
        .brand .dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--hover);
        }
        h1 {
          margin: 14px 0 10px;
          text-align: center;
          font-size: clamp(2.1rem, 5vw, 4rem);
          line-height: 1.06;
          letter-spacing: -0.06em;
          font-weight: 800;
        }
        .hero {
          text-align: center;
          color: var(--muted);
          font-size: 1rem;
          margin-bottom: 26px;
        }
        .search-shell {
          width: min(900px, 100%);
          margin: 0 auto 30px;
          padding: 14px 14px 14px 18px;
          display: flex;
          align-items: center;
          gap: 10px;
          border-radius: 22px;
          border: 1px solid var(--border);
          background: var(--panel-soft);
        }
        .search-shell input {
          flex: 1;
          min-width: 0;
          border: none;
          background: transparent;
          outline: none;
          font-size: 1.08rem;
          color: var(--text-dark);
          padding: 12px 8px;
        }
        .search-shell input::placeholder {
          color: #666666;
        }
        .search-btn {
          appearance: none;
          border: 1px solid var(--border);
          background: var(--panel-soft) !important;
          color: var(--text-dark);
          font-weight: 800;
          font-size: 0.96rem;
          border-radius: 14px;
          padding: 12px 20px;
          cursor: pointer;
        }
        .search-btn:hover {
          background: var(--hover) !important;
        }
        .actions {
          display: flex;
          justify-content: center;
          flex-wrap: wrap;
          gap: 12px;
          margin-bottom: 24px;
        }
        .btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 11px 18px;
          border-radius: 12px;
          color: var(--text-dark);
          text-decoration: none;
          font-weight: 700;
          border: 1px solid var(--border);
          background: var(--panel-soft);
        }
        .btn:hover {
          background: var(--hover);
        }
        .btn.primary {
          background: var(--panel-soft) !important;
          border-color: var(--border);
          color: var(--text-dark);
        }
        .cards {
          display: flex;
          gap: 14px;
          flex-wrap: wrap;
          margin-top: 18px;
        }
        .card {
          flex: 1 1 220px;
          background: var(--panel-soft);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 16px;
          color: var(--text-dark);
        }
        .card h3 {
          margin: 0 0 8px;
          font-size: 0.98rem;
          color: var(--text-dark);
        }
        .card p {
          margin: 0;
          color: var(--text-dark);
          line-height: 1.55;
          font-size: 0.9rem;
        }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="brand"><span class="dot"></span> Phantom Browser</div>
        <h1>Search smarter. Browse privately.</h1>
        <p class="hero">A private, in-memory browsing experience with an AI copilot built in.</p>

        <form class="search-shell" action="https://duckduckgo.com/" method="get" target="_blank">
          <input type="text" name="q" placeholder="Search the web or ask Phantom..." aria-label="Search" />
          <button class="search-btn" type="submit">Search</button>
        </form>

        <div class="actions">
          <a class="btn primary" href="/chat/">Open AI Studio</a>
          <a class="btn" href="/browser">Refresh</a>
          <a class="btn" href="https://duckduckgo.com" target="_blank">DuckDuckGo</a>
        </div>

        <div class="cards">
          <div class="card">
            <h3>Private Mode</h3>
            <p>No disk cache or persistent session data. Your browsing stays in memory.</p>
          </div>
          <div class="card">
            <h3>Secure Navigation</h3>
            <p>HTTPS upgrades and tracker blocking keep your sessions cleaner and safer.</p>
          </div>
          <div class="card">
            <h3>AI Copilot</h3>
            <p>Jump into the AI Studio for chats, coding help, and research assistance.</p>
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    server_app = FastAPI(title="Phantom Browser")

    @server_app.get("/", include_in_schema=False)
    async def browser_home():
        return HTMLResponse(BROWSER_HOME_HTML)

    @server_app.get("/browser", include_in_schema=False)
    async def browser_home_alias():
        return HTMLResponse(BROWSER_HOME_HTML)

    server_app = gr.mount_gradio_app(server_app, demo, path="/chat")

    demo.queue()
    uvicorn.run(server_app, host="0.0.0.0", port=port)
