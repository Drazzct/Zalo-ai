# Dockerfile for Zalo AI Challenge 2026 - DataMate
# Strictly conforms to zac2026_DataMate_docker_guideline_final.pdf

FROM vllm/vllm-openai:v0.10.1.1

# Reset entrypoint so standard bash/docker run starts predict.sh
ENTRYPOINT []

# Offline environment flags and NCCL P2P disable for RTX 5090 Blackwell compatibility
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PIP_NO_CACHE_DIR=1 \
    NCCL_P2P_DISABLE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Step 1: Install Python dependencies
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# Step 2: Fix NCCL hang on dual GPU (Blackwell RTX 5090 workaround from guideline Section 8)
RUN pip install --no-cache-dir --no-deps nvidia-nccl-cu12==2.27.7

# Step 3: Copy model weights (cached layer)
COPY models/ /code/models/

# Step 4: Copy training code, data generation, and manifest (Section 8 requirement)
COPY training_code/ /code/training_code/

# Step 5: Copy inference code and entrypoints
COPY predict.sh README.md /code/
COPY predict.py /code/predict.py
COPY src/ /code/src/

# Make entrypoint script executable
RUN chmod +x /code/predict.sh

# Default container execution command
CMD ["bash", "/code/predict.sh"]
