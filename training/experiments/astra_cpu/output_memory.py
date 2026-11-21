"""Compare dense and chunked answer loss in fresh CPU processes at the T80 vocabulary size."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

VOCAB = 151_669


def measure(answer, chunk, gradient_path):
    import psutil
    import torch
    from transformers import Qwen3Config, Qwen3ForCausalLM
    from training.lm_head_loss import answer_nll

    torch.set_num_threads(1)
    torch.manual_seed(17)
    model = Qwen3ForCausalLM(Qwen3Config(vocab_size=VOCAB, hidden_size=128, intermediate_size=256,
                                       num_hidden_layers=1, num_attention_heads=4, num_key_value_heads=2,
                                       head_dim=32, use_cache=False, tie_word_embeddings=True))
    model.requires_grad_(False)
    trainable = model.model.layers[0].mlp.down_proj.weight
    trainable.requires_grad_(True)
    ids = torch.randint(0, VOCAB, (1, 64 + answer))
    before = psutil.Process().memory_info().rss
    start = time.perf_counter()
    loss = answer_nll(model, ids, answer, chunk) / answer
    loss.backward()
    wall = time.perf_counter() - start
    high_water = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024  # Linux KiB
    import numpy as np
    np.save(gradient_path, trainable.grad.numpy())
    return {"answer_tokens": answer, "chunk": chunk, "mean_loss": loss.item(),
            "rss_before_mib": round(before / 2**20, 1), "process_peak_mib": round(high_water / 2**20, 1),
            "forward_backward_seconds": round(wall, 3), "torch": torch.__version__}


def compare():
    import numpy as np
    report = {"vocabulary": VOCAB, "hidden_width": 128, "layers": 1, "threads": 1, "dtype": "float32",
              "measurements": []}
    with tempfile.TemporaryDirectory() as folder:
        for answer in (24, 192):
            samples = []
            for chunk in (0, 64):
                path = Path(folder) / f"{answer}-{chunk}.npy"
                run = subprocess.run([sys.executable, "-m", "training.experiments.astra_cpu.output_memory",
                                      "--worker", str(answer), str(chunk), "--gradient", str(path)],
                                     check=True, capture_output=True, text=True)
                samples.append(json.loads(run.stdout))
            gradients = [np.load(Path(folder) / f"{answer}-{chunk}.npy") for chunk in (0, 64)]
            error = np.abs(gradients[1] - gradients[0])
            np.testing.assert_allclose(gradients[1], gradients[0], rtol=1e-4, atol=1e-7)
            assert abs(samples[1]["mean_loss"] - samples[0]["mean_loss"]) < 1e-5
            report["measurements"].append({"answer_tokens": answer, "absolute_gradient_error_max": float(error.max()),
                                           "arms": samples})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", nargs=2, type=int, metavar=("ANSWER", "CHUNK"))
    parser.add_argument("--gradient", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(measure(*args.worker, args.gradient)))
    else:
        result = json.dumps(compare(), indent=2)
        if args.out:
            args.out.write_text(result + "\n")
        print(result)
