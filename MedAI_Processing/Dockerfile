FROM python:3.11-slim

# Install system deps as root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && rm -rf /var/lib/apt/lists/*

# Create non-root user afterwards
RUN useradd -m -u 1000 user
ENV HOME=/home/user
WORKDIR $HOME/app

# Download dependencies
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Logger and Caching path
RUN mkdir -p $HOME/app/logs $HOME/app/cache $HOME/app/cache/hf $HOME/app/cache/outputs

USER user
EXPOSE 7860
CMD ["python","-m","uvicorn","app:app","--host","0.0.0.0","--port","7860"]
