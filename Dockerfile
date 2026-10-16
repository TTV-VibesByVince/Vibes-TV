FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MEDIA_DIR=/media \
    CACHE_DIR=/cache \
    CONFIG_DIR=/config \
    PORT=8777

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ /app/

EXPOSE 8777
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8777')+'/status', timeout=4)" || exit 1
CMD ["python", "server.py"]
