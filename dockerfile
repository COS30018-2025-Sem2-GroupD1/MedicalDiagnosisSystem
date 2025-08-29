# Use Python slim image for smaller size
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
	ca-certificates \
	curl \
	&& rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 user
ENV HOME=/home/user
ENV APP_PATH=$HOME/medical_diagnosis_system
WORKDIR $APP_PATH

# Copy requirements first for better layer caching
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Set up Hugging Face cache directories
ENV HF_HOME="$HOME/.cache/huggingface"
ENV TRANSFORMERS_CACHE="$HF_HOME/transformers"
ENV HUGGINGFACE_HUB_CACHE="$HF_HOME/hub"
ENV SENTENCE_TRANSFORMERS_HOME="$HF_HOME/sentence-transformers"

# Create necessary directories with correct permissions
RUN mkdir -p \
	$APP_PATH/logs \
	$APP_PATH/cache \
	$HOME/.cache/huggingface \
	&& chown -R user:user $HOME

# Copy application code
COPY --chown=user ./app ./app
COPY --chown=user .env .env

# Switch to non-root user
USER user

# HF Spaces uses port 7860
EXPOSE 7860

# Start command using HF Spaces port
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
