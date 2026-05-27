FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y git ffmpeg && rm -rf /var/lib/apt/lists/*

# Clone LTX-Video and install
RUN git clone https://github.com/Lightricks/LTX-Video.git /opt/LTX-Video
WORKDIR /opt/LTX-Video
RUN pip install -e ".[inference]" --no-cache-dir

# Copy our service
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir
COPY app.py .

ENV LTX_VIDEO_DIR=/opt/LTX-Video
ENV MODEL_WEIGHTS_PATH=/opt/LTX-Video/models/ltxv-13b-0.9.8-distilled-fp8.safetensors
ENV PIPELINE_CONFIG=configs/ltxv-13b-0.9.8-distilled-fp8.yaml

EXPOSE 6006

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "6006"]
