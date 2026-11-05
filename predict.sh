#!/bin/bash
set -e

# Default competition paths inside Docker container:
INPUT_DIR=${DATA_DIR:-"/data"}
OUTPUT_FILE=${OUTPUT_FILE:-"/result/submission.jsonl"}
LOG_DIR=${LOG_DIR:-"/result/logs"}

echo "=============================================="
echo "Starting Zalo AI DataMate Predict Script..."
echo "Input : $INPUT_DIR"
echo "Output: $OUTPUT_FILE"
echo "Logs  : $LOG_DIR"
echo "=============================================="

# Ensure directories exist
mkdir -p "$(dirname "$OUTPUT_FILE")"
mkdir -p "$LOG_DIR"

# Run prediction pipeline
python predict.py \
    --input-dir "$INPUT_DIR" \
    --output "$OUTPUT_FILE" \
    --log-dir "$LOG_DIR"

echo "Prediction completed successfully!"

