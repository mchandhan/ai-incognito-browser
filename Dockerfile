FROM python:3.11-slim

# The container runs only the AI backend service.
# The desktop browser app (filename.py) is a local GUI app and should run on the host machine,
# typically on port 5000 for the local browser landing page.
ENV PYTHONUNBUFFERED=1 \
    GRADIO_SERVER_PORT=5050 \
    PORT=5050 \
    APP_PORT=5050 \
    BROWSER_PORT=5000

WORKDIR /app

# Install minimal system deps required by some audio/image libs used by Gradio
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project files
COPY . /app

EXPOSE 5050

# Run the backend AI app. The desktop browser app remains local and separate.
CMD ["python", "app.py"]
