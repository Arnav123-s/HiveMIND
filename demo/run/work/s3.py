import time
import psutil
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Define the models to benchmark
models = [
    "line-corporation/japanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False",
    "line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False"
]

# Define the arithmetic questions to test
questions = [
    "1 + 1 = ?",
    "2 * 2 = ?",
    "3 - 1 = ?",
    "4 / 2 = ?",
    "5 % 2 = ?",
    "6 ** 2 = ?",
    "7 // 2 = ?",
    "8 & 1 = ?",
    "9 | 1 = ?",
    "10 ^ 1 = ?"
]

# Function to measure load time, memory used, and tokens per second
def benchmark_model(model_name):
    print(f"Benchmarking {model_name}...")
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Measure load time
    start_time = time.time()
    model.eval()
    end_time = time.time()
    load_time = end_time - start_time
    print(f"Load time: {load_time:.2f} seconds")
    
    # Measure memory used
    process = psutil.Process()
    start_memory = process.memory_info().rss / 1024 / 1024
    model.eval()
    end_memory = process.memory_info().rss / 1024 / 1024
    memory_used = end_memory - start_memory
    print(f"Memory used: {memory_used:.2f} MB")
    
    # Measure tokens per second
    tokens_per_second = 0
    for question in questions:
        inputs = tokenizer(question, return_tensors="pt").to("cpu")
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=10)
        end_time = time.time()
        tokens_per_second += len(outputs[0]) / (end_time - start_time)
    tokens_per_second /= len(questions)
    print(f"Tokens per second: {tokens_per_second:.2f}")
    
    # Check how many questions are answered correctly
    correct_answers = 0
    for question in questions:
        inputs = tokenizer(question, return_tensors="pt").to("cpu")
        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=10)
        answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
        if answer.strip() == question.split("=")[1].strip():
            correct_answers += 1
    print(f"Correct answers: {correct_answers}/{len(questions)}")
    print()

# Benchmark each model
for model in models:
    benchmark_model(model)