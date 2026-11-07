# Weight edit report: writer

Base model: `Qwen/Qwen3-1.7B`  
Edited: 98 matrices in layers 14-27 (down_proj, gate_proj, k_proj, o_proj, q_proj, up_proj, v_proj); rank 8, alpha 32; 4,358,144 trained numbers.

## Mean relative change ||dW||/||W|| by layer

| layer | mean | max |
|---|---|---|
| 14 | 0.3379% | 0.3951% |
| 15 | 0.3387% | 0.3963% |
| 16 | 0.3300% | 0.3937% |
| 17 | 0.3339% | 0.3941% |
| 18 | 0.3400% | 0.4112% |
| 19 | 0.3319% | 0.3914% |
| 20 | 0.3223% | 0.3912% |
| 21 | 0.3048% | 0.3645% |
| 22 | 0.3070% | 0.3657% |
| 23 | 0.3101% | 0.3646% |
| 24 | 0.3047% | 0.3600% |
| 25 | 0.3033% | 0.3694% |
| 26 | 0.2988% | 0.3788% |
| 27 | 0.2950% | 0.3378% |

## By module

| module | mean | max |
|---|---|---|
| down_proj | 0.1886% | 0.2093% |
| gate_proj | 0.3335% | 0.3665% |
| k_proj | 0.3699% | 0.3944% |
| o_proj | 0.3708% | 0.4112% |
| q_proj | 0.3092% | 0.3303% |
| up_proj | 0.3102% | 0.3454% |
| v_proj | 0.3469% | 0.3913% |

## 10 most-changed matrices

| tensor | rel change | effective rank |
|---|---|---|
| `model.layers.18.self_attn.o_proj.weight` | 0.4112% | 8 |
| `model.layers.15.self_attn.o_proj.weight` | 0.3963% | 8 |
| `model.layers.14.self_attn.o_proj.weight` | 0.3951% | 8 |
| `model.layers.18.self_attn.k_proj.weight` | 0.3944% | 8 |
| `model.layers.17.self_attn.o_proj.weight` | 0.3941% | 8 |
| `model.layers.16.self_attn.o_proj.weight` | 0.3937% | 8 |
| `model.layers.19.self_attn.o_proj.weight` | 0.3914% | 8 |
| `model.layers.19.self_attn.v_proj.weight` | 0.3913% | 8 |
| `model.layers.20.self_attn.o_proj.weight` | 0.3912% | 8 |
| `model.layers.19.self_attn.k_proj.weight` | 0.3840% | 8 |
