FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/comfyanonymous/ComfyUI.git /app/ComfyUI

WORKDIR /app/ComfyUI

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app

COPY requirements.txt /app/requirements-worker.txt
RUN pip install --no-cache-dir -r /app/requirements-worker.txt

COPY handler.py /app/handler.py

CMD ["python", "-u", "/app/handler.py"]
