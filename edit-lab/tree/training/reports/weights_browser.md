# Weight edit report: browser

Base model: `Qwen/Qwen3-1.7B`  
Edited: 98 matrices in layers 14-27 (down_proj, gate_proj, k_proj, o_proj, q_proj, up_proj, v_proj); rank 16, alpha 32; 8,716,288 trained numbers.

## Mean relative change ||dW||/||W|| by layer

| layer | mean | max |
|---|---|---|
| 14 | 0.3617% | 0.4338% |
| 15 | 0.3529% | 0.4144% |
| 16 | 0.3514% | 0.4134% |
| 17 | 0.3591% | 0.4219% |
| 18 | 0.3791% | 0.4329% |
| 19 | 0.3868% | 0.4619% |
| 20 | 0.3659% | 0.4302% |
| 21 | 0.3640% | 0.4339% |
| 22 | 0.3837% | 0.4487% |
| 23 | 0.3779% | 0.4436% |
| 24 | 0.3750% | 0.4450% |
| 25 | 0.3752% | 0.4226% |
| 26 | 0.3864% | 0.4837% |
| 27 | 0.3838% | 0.4254% |

## By module

| module | mean | max |
|---|---|---|
| down_proj | 0.2276% | 0.2457% |
| gate_proj | 0.4019% | 0.4219% |
| k_proj | 0.4203% | 0.4837% |
| o_proj | 0.4261% | 0.4522% |
| q_proj | 0.3599% | 0.4079% |
| up_proj | 0.3702% | 0.3901% |
| v_proj | 0.3955% | 0.4487% |

## 10 most-changed matrices

| tensor | rel change | effective rank |
|---|---|---|
| `model.layers.26.self_attn.k_proj.weight` | 0.4837% | 16 |
| `model.layers.19.self_attn.k_proj.weight` | 0.4619% | 16 |
| `model.layers.19.self_attn.o_proj.weight` | 0.4522% | 16 |
| `model.layers.19.self_attn.v_proj.weight` | 0.4487% | 16 |
| `model.layers.22.self_attn.k_proj.weight` | 0.4487% | 16 |
| `model.layers.24.self_attn.o_proj.weight` | 0.4450% | 16 |
| `model.layers.23.self_attn.k_proj.weight` | 0.4436% | 16 |
| `model.layers.26.self_attn.o_proj.weight` | 0.4355% | 16 |
| `model.layers.21.self_attn.o_proj.weight` | 0.4339% | 16 |
| `model.layers.14.self_attn.o_proj.weight` | 0.4338% | 16 |
