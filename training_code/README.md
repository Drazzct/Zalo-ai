# Training Code & Artifacts Documentation
> Zalo AI Challenge 2026 - DataMate

## 1. Approach Overview
This solution utilizes an in-context reasoning agent with sandbox SQL/Python execution (`ReasoningPipeline`).
- **No model fine-tuning or parameter updates** were performed.
- Model generation relies on frozen base weights with strict rule enforcement, schema profiling, calendar resolution, and self-reflection error correction.

## 2. Base Model Declarations
- **Model Name:** Qwen2.5-Coder-7B-Instruct (or Qwen3-14B)
- **Public Source:** https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
- **Original Release Date:** September 2024 (Predates October 26, 2026 requirement)
- **License:** Apache 2.0
- **Parameter Count:** 7.61 Billion parameters ($\le$ 15B total allowed)
- **Revision / Commit:** main / b680b5...

## 3. Data & Reproduction
Since no fine-tuning was performed, reproduction of training is not applicable.
The inference pipeline is 100% reproducible and operates fully offline using the frozen weights packaged in `/code/models/`.
