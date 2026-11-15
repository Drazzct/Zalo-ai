#!/bin/bash
set -e

# Default competition paths inside Docker container:
INPUT_DIR=${DATA_DIR:-"/data"}
OUTPUT_FILE=${OUTPUT_FILE:-"/result/submission.jsonl"}
LOG_DIR=${LOG_DIR:-"/result/logs"}
MODEL_DIR=${MODEL_DIR:-"/code/models"}

echo "=============================================="
echo "Starting Zalo AI DataMate Predict Script..."
echo "Input : $INPUT_DIR"
echo "Output: $OUTPUT_FILE"
echo "Logs  : $LOG_DIR"
echo "=============================================="

# Ensure output directories exist
mkdir -p "$(dirname "$OUTPUT_FILE")"
mkdir -p "$LOG_DIR"

# Detect model weights in /code/models
if [ -d "$MODEL_DIR" ] && [ "$(ls -A "$MODEL_DIR" 2>/dev/null)" ]; then
    MODEL_PATH=$(find "$MODEL_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    if [ -z "$MODEL_PATH" ]; then
        MODEL_PATH="$MODEL_DIR"
    fi
    echo "Found local model weights at: $MODEL_PATH"
    
    # Run prediction using direct in-process vLLM
    python3 predict.py \
        --input-dir "$INPUT_DIR" \
        --output "$OUTPUT_FILE" \
        --log-dir "$LOG_DIR" \
        --model-backend direct_vllm \
        --model-name "$MODEL_PATH"
else
    # Fallback mode (e.g. mock or local environment)
    python3 predict.py \
        --input-dir "$INPUT_DIR" \
        --output "$OUTPUT_FILE" \
        --log-dir "$LOG_DIR"
fi

echo "Prediction completed successfully!"
