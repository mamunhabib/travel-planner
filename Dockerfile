# 1. Base Image: Minimal, lightweight Python 3.10 Debian-slim image
FROM python:3.10-slim

# 2. Performance & Logging Configuration
# Forces unbuffered stdout/stderr so logs stream in real time to Kubernetes & Filebeat
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# 3. OCI Image Label for GitHub Container Registry (GHCR) linking
LABEL org.opencontainers.image.source="https://github.com/mamunhabib/travel-planner"

# 4. Working Directory inside the container
WORKDIR /app

# 5. Dependency Layer Caching:
# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy Application Source Code
COPY . .

# 7. Expose Streamlit Port
EXPOSE 8501

# 8. Start Streamlit in headless production mode
CMD ["streamlit", "run", "app/ui.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
