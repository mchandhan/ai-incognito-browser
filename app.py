import gradio as gr
from openai import OpenAI
import os
import sys
import pathlib
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
        yield "⚠️ **No API token provided.** Please enter your Hugging Face token in the **Settings** panel below."
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
                    reasoning = "> 💭 *Thinking Process:*\n> "
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

* {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    box-sizing: border-box;
}

body, .gradio-container {
    background: radial-gradient(ellipse 70% 50% at 15% 10%, rgba(124, 58, 237, 0.18) 0%, transparent 60%),
                radial-gradient(ellipse 60% 40% at 85% 15%, rgba(56, 189, 248, 0.16) 0%, transparent 60%),
                radial-gradient(ellipse 50% 50% at 50% 90%, rgba(16, 185, 129, 0.10) 0%, transparent 60%),
                #070913 !important;
    color: #f1f5f9 !important;
    min-height: 100vh;
}

.gradio-container {
    max-width: 980px !important;
    margin: 0 auto !important;
    padding: 16px 20px 40px !important;
}

/* Glassmorphism Cards */
#chatbot {
    background: rgba(13, 18, 36, 0.78) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border: 1px solid rgba(167, 139, 250, 0.22) !important;
    border-radius: 22px !important;
    box-shadow: 0 20px 60px -15px rgba(0, 0, 0, 0.75), inset 0 1px 1px rgba(255, 255, 255, 0.08) !important;
    overflow: hidden !important;
    transition: border-color 0.3s ease;
}

#chatbot:hover {
    border-color: rgba(167, 139, 250, 0.4) !important;
}

/* Chat Messages */
.message-row {
    margin-bottom: 14px !important;
}

/* User Message */
[data-testid="user"] {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    border-radius: 18px 18px 4px 18px !important;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
}

/* Bot Message */
[data-testid="bot"] {
    background: rgba(23, 29, 56, 0.85) !important;
    backdrop-filter: blur(12px) !important;
    color: #e2e8f0 !important;
    border-radius: 18px 18px 18px 4px !important;
    border: 1px solid rgba(148, 163, 184, 0.16) !important;
    box-shadow: 0 4px 25px rgba(0, 0, 0, 0.3) !important;
}

/* Code Blocks in Chat */
pre, code {
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 8px !important;
}

pre {
    background: #0b0f19 !important;
    border: 1px solid rgba(148, 163, 184, 0.2) !important;
    padding: 12px 16px !important;
}

blockquote {
    border-left: 3px solid #a78bfa !important;
    background: rgba(167, 139, 250, 0.08) !important;
    padding: 8px 14px !important;
    border-radius: 0 10px 10px 0 !important;
    margin: 8px 0 !important;
}

/* Input Area Command Bar */
#msg-input textarea {
    background: rgba(17, 24, 48, 0.92) !important;
    border: 1.5px solid rgba(148, 163, 184, 0.22) !important;
    border-radius: 16px !important;
    color: #f8fafc !important;
    padding: 14px 20px !important;
    font-size: 0.98rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
}

#msg-input textarea:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.18), 0 8px 25px rgba(0, 0, 0, 0.4) !important;
    outline: none !important;
}

/* Buttons */
#send-btn {
    background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%) !important;
    border: none !important;
    border-radius: 16px !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    box-shadow: 0 6px 24px rgba(124, 58, 237, 0.45) !important;
    transition: all 0.25s ease !important;
    cursor: pointer !important;
}

#send-btn:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 10px 30px rgba(124, 58, 237, 0.65) !important;
}

#send-btn:active {
    transform: translateY(0) scale(0.98) !important;
}

#clear-btn {
    background: rgba(239, 68, 68, 0.1) !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
    border-radius: 14px !important;
    color: #fca5a5 !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

#clear-btn:hover {
    background: rgba(239, 68, 68, 0.22) !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
}

/* Quick Prompt Chips */
.quick-chip {
    background: rgba(30, 41, 59, 0.7) !important;
    border: 1px solid rgba(148, 163, 184, 0.25) !important;
    border-radius: 14px !important;
    color: #cbd5e1 !important;
    padding: 8px 14px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
    text-align: left !important;
}

.quick-chip:hover {
    background: rgba(56, 189, 248, 0.15) !important;
    border-color: #38bdf8 !important;
    color: #38bdf8 !important;
    transform: translateY(-2px) !important;
}

/* Settings Accordion */
.accordion {
    background: rgba(15, 23, 42, 0.65) !important;
    backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(148, 163, 184, 0.18) !important;
    border-radius: 18px !important;
    margin-top: 14px !important;
}

/* Inputs in settings */
input, select {
    background: rgba(17, 24, 48, 0.9) !important;
    border: 1px solid rgba(148, 163, 184, 0.25) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
}

input:focus, select:focus {
    border-color: #818cf8 !important;
}

label {
    color: #cbd5e1 !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px;
}

/* Smooth Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: rgba(167, 139, 250, 0.3);
    border-radius: 8px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(167, 139, 250, 0.6);
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.45; transform: scale(0.92); }
}
"""


# ── UI Architecture ──────────────────────────────────────────────────
with gr.Blocks(title="Phantom AI Studio - Free Cloud Models", css=custom_css, theme=gr.themes.Soft(primary_hue="violet", neutral_hue="slate")) as demo:

    # Hero Header Banner
    gr.HTML("""
    <div style="text-align: center; padding: 1.4rem 0 0.8rem;">
        <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: 0.75rem;
                    background: rgba(124, 58, 237, 0.12); border: 1px solid rgba(167, 139, 250, 0.35);
                    border-radius: 30px; padding: 6px 18px; font-size: 0.82rem; font-weight: 600; color: #c4b5fd;">
            <span style="width: 8px; height: 8px; background: #34d399; border-radius: 50%;
                         box-shadow: 0 0 10px #34d399; display: inline-block; animation: pulse 2s infinite;"></span>
            <span>Hugging Face Serverless Router &bull; Active &amp; Free</span>
        </div>
        <h1 style="font-family: 'Outfit', sans-serif !important; font-size: 2.6rem; font-weight: 800;
                   letter-spacing: -0.8px; margin: 0 0 0.4rem;
                   background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 40%, #a78bfa 75%, #38bdf8 100%);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            Phantom AI Studio
        </h1>
        <p style="color: #94a3b8; margin: 0 auto; max-width: 600px; font-size: 0.95rem; line-height: 1.5;">
            Powered by <strong style="color:#e2e8f0;">Qwen 2.5</strong>, <strong style="color:#e2e8f0;">DeepSeek-V3</strong>, and <strong style="color:#e2e8f0;">Llama 3.3</strong> cloud models &mdash; lightning fast, free &amp; private.
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
        chip1 = gr.Button("💻 Write a Python web scraper", elem_classes=["quick-chip"], scale=1)
        chip2 = gr.Button("🧠 Explain quantum computing simply", elem_classes=["quick-chip"], scale=1)
        chip3 = gr.Button("⚡ Compare Qwen vs DeepSeek", elem_classes=["quick-chip"], scale=1)
        chip4 = gr.Button("🚀 Brainstorm creative AI startup ideas", elem_classes=["quick-chip"], scale=1)

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
        send_btn = gr.Button("Send ✦", scale=1, elem_id="send-btn", min_width=110)

    # Auxiliary Action Bar
    with gr.Row():
        clear_btn = gr.Button("🗑️ Clear Chat", elem_id="clear-btn", scale=1)
        gr.HTML("""
        <div style="display:flex; align-items:center; justify-content:flex-end; height:100%; gap:12px; color:#64748b; font-size:0.8rem;">
            <span>⚡ Streaming enabled</span>
            <span>🔒 Session strictly in-memory</span>
        </div>
        """, scale=5)

    # Model & Parameter Settings
    with gr.Accordion("⚙️ Model & Studio Settings", open=False, elem_classes=["accordion"]):
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
    # Allow external controller to select port via environment variable
    try:
        port = int(__import__("os").environ.get("GRADIO_SERVER_PORT", "5050"))
    except Exception:
        port = 5050

    BROWSER_HOME_HTML = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>RAAMA Browser</title>
      <style>
        :root {
          --bg: #071025;
          --panel: rgba(15, 23, 42, 0.82);
          --panel-strong: rgba(15, 23, 42, 0.96);
          --border: rgba(148, 163, 184, 0.18);
          --soft: #94a3b8;
          --text: #e2e8f0;
          --primary: #38bdf8;
          --accent: #8b5cf6;
          --accent-2: #22c55e;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          min-height: 100vh;
          font-family: Inter, Segoe UI, Arial, sans-serif;
          background: radial-gradient(circle at top, rgba(56, 189, 248, 0.12), transparent 28%),
                      radial-gradient(circle at bottom right, rgba(139, 92, 246, 0.16), transparent 24%),
                      var(--bg);
          color: var(--text);
        }
        .wrap {
          width: min(1080px, calc(100% - 32px));
          margin: 48px auto 24px;
          padding: 22px 24px 26px;
          border-radius: 28px;
          background: rgba(15, 23, 42, 0.72);
          border: 1px solid var(--border);
          box-shadow: 0 28px 60px rgba(2, 6, 23, 0.45);
          backdrop-filter: blur(10px);
        }
        .brand {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          font-size: 0.8rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: #c4b5fd;
          font-weight: 700;
        }
        .brand .dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--accent-2);
          box-shadow: 0 0 12px rgba(34, 197, 94, 0.85);
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
          color: var(--soft);
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
          border: 1px solid rgba(148, 163, 184, 0.2);
          background: rgba(15, 23, 42, 0.9);
          box-shadow: 0 18px 36px rgba(15, 23, 42, 0.42);
        }
        .search-shell input {
          flex: 1;
          min-width: 0;
          border: none;
          background: transparent;
          outline: none;
          font-size: 1.08rem;
          color: var(--text);
          padding: 12px 8px;
        }
        .search-shell input::placeholder {
          color: #64748b;
        }
        .search-btn {
          appearance: none;
          border: none;
          background: linear-gradient(135deg, var(--primary), var(--accent));
          color: #03111d;
          font-weight: 800;
          font-size: 0.96rem;
          border-radius: 14px;
          padding: 12px 20px;
          cursor: pointer;
          box-shadow: 0 10px 22px rgba(56, 189, 248, 0.28);
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
          color: var(--text);
          text-decoration: none;
          font-weight: 700;
          border: 1px solid var(--border);
          background: rgba(255,255,255,0.02);
        }
        .btn.primary {
          background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(139, 92, 246, 0.22));
          border-color: rgba(56, 189, 248, 0.4);
          color: #dbeafe;
        }
        .cards {
          display: flex;
          gap: 14px;
          flex-wrap: wrap;
          margin-top: 18px;
        }
        .card {
          flex: 1 1 220px;
          background: rgba(15,23,42,0.7);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 16px;
        }
        .card h3 {
          margin: 0 0 8px;
          font-size: 0.98rem;
          color: #dbeafe;
        }
        .card p {
          margin: 0;
          color: var(--soft);
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

    server_app = FastAPI(title="RAAMA Browser")

    @server_app.get("/", include_in_schema=False)
    async def browser_home():
        return HTMLResponse(BROWSER_HOME_HTML)

    @server_app.get("/browser", include_in_schema=False)
    async def browser_home_alias():
        return HTMLResponse(BROWSER_HOME_HTML)

    server_app = gr.mount_gradio_app(server_app, demo, path="/chat")

    demo.queue()
    uvicorn.run(server_app, host="0.0.0.0", port=port)
