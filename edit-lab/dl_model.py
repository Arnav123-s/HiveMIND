from huggingface_hub import snapshot_download

p = snapshot_download("Qwen/Qwen3-1.7B", max_workers=2)
print("model at", p)
