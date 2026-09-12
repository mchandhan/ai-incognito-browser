# Phantom AI Incognito Browser

A privacy-focused desktop browser with an integrated AI assistant powered by free Hugging Face cloud models. Run locally or in Docker. All conversations stay in memory, never persisted to disk.

## Features

- Private, in-memory browsing with no disk cache
- Integrated AI Studio with access to free cloud models
- Desktop PyQt6 browser with built-in search bar
- FastAPI backend with Gradio chat interface
- Docker support for easy deployment
- Hugging Face Serverless Router integration
- Support for Qwen, DeepSeek, and Llama models
- No hardcoded API tokens or credentials
- Automatic log truncation on startup

## Architecture

- `app.py` - Gradio AI backend and browser landing page (runs in Docker on port 5050 or locally)
- `filename.py` - Desktop PyQt6 browser GUI with local start page (runs on port 5000)
- `Dockerfile` - Container configuration for the backend
- `requirements.txt` - Python dependencies

## Prerequisites

- Python 3.11 or higher
- Git
- Docker (optional, for container deployment)
- Hugging Face API token (free tier available at https://huggingface.co/settings/tokens)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mchandhan/phantom-browser.git
   cd phantom-browser
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   ```

3. Activate virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Locally

### Option 1: Desktop Browser (Recommended for local use)

Start the desktop application:
```bash
python filename.py
```

This starts both:
- Local browser home page on port 5000
- AI backend (app.py) automatically on port 5050

### Option 2: Web Backend Only

Start just the backend server:
```bash
python app.py
```

Access at `http://localhost:5050` or `http://localhost:5050/chat` for the AI studio.

## Using the AI Studio

1. Open the browser and navigate to the AI chat interface
2. Go to the "Model & Studio Settings" section (expand the accordion)
3. Enter your Hugging Face API token in the "Hugging Face API Token (required)" field
   - Get a free token at: https://huggingface.co/settings/tokens
   - Click "New token" and create a token with "read" permission
4. Select a model from the dropdown (defaults to Qwen2.5-Coder-3B)
5. Adjust temperature and max tokens as needed
6. Type your prompt and press Enter or click Send

## Running with Docker

### Build the Docker image:
```bash
docker build -t ai-incognito-browser:latest .
```

### Run the container:
```bash
docker run -d --name ai-browser -e GRADIO_SERVER_PORT=5000 -p 5000:5000 ai-incognito-browser:latest
```

### Access from another device on your network:
Replace `YOUR_PC_IP` with your computer's IP address:
```
http://YOUR_PC_IP:5000/
```

To find your IP address:
- Windows: Run `ipconfig` and look for "IPv4 Address"
- macOS/Linux: Run `ifconfig` or `hostname -I`

### Stop the container:
```bash
docker stop ai-browser
docker rm ai-browser
```

## Available Models

The application includes access to these free serverless models:
- Qwen/Qwen2.5-Coder-3B-Instruct
- Qwen/Qwen3-4B-Instruct-2507
- DeepSeek-R1-Distill-Qwen-7B
- meta-llama/Llama-3.1-8B-Instruct
- meta-llama/Llama-3.3-70B-Instruct
- microsoft/phi-4
- google/gemma-3-4b-it

## Port Configuration

Default ports:
- Desktop browser landing page: 5000
- AI backend server: 5050
- Chat interface: http://localhost:5050/chat

To change ports, set environment variables before running:

Windows:
```bash
$env:GRADIO_SERVER_PORT=8000
python app.py
```

macOS/Linux:
```bash
export GRADIO_SERVER_PORT=8000
python app.py
```

## Troubleshooting

### Port already in use
If you see "error while attempting to bind on address", find and kill the process:

Windows:
```bash
netstat -ano | findstr ":5050"
taskkill /PID <PID> /F
```

macOS/Linux:
```bash
lsof -i :5050
kill -9 <PID>
```

### "This site can't be reached" on mobile
1. Ensure firewall allows port 5000/5050
2. Use your PC's actual LAN IP (not localhost)
3. Both devices must be on the same WiFi network

### AI responses not working
1. Verify you entered a valid Hugging Face API token
2. Check that your token has "read" permission
3. Ensure you have internet connectivity
4. Verify the selected model is available

## Security Notes

- No API tokens or credentials are hardcoded in the source
- Sensitive environment variables are cleared at startup
- Application logs are truncated on startup
- All conversations remain in memory only
- No persistent session data is stored

## Development

To contribute or modify:

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Make your changes

3. Commit and push:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on GitHub:
https://github.com/mchandhan/phantom-browser/issues
