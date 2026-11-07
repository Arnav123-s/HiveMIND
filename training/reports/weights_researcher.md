# Weight edit report: researcher

Base model: `Qwen/Qwen3-1.7B`  
Edited: 98 matrices in layers 14-27 (down_proj, gate_proj, k_proj, o_proj, q_proj, up_proj, v_proj); rank 16, alpha 32; 8,716,288 trained numbers.

## Mean relative change ||dW||/||W|| by layer

| layer | mean | max |
|---|---|---|
| 14 | 0.3585% | 0.4476% |
| 15 | 0.3590% | 0.4325% |
| 16 | 0.3460% | 0.4280% |
| 17 | 0.3469% | 0.4189% |
| 18 | 0.3568% | 0.4284% |
| 19 | 0.3510% | 0.4239% |
| 20 | 0.3255% | 0.3875% |
| 21 | 0.3085% | 0.3740% |
| 22 | 0.3182% | 0.3741% |
| 23 | 0.3315% | 0.4022% |
| 24 | 0.3096% | 0.3736% |
| 25 | 0.3213% | 0.3823% |
| 26 | 0.3073% | 0.4451% |
| 27 | 0.2902% | 0.3249% |

## By module

| module | mean | max |
|---|---|---|
| down_proj | 0.2015% | 0.2383% |
| gate_proj | 0.3413% | 0.3774% |
| k_proj | 0.3761% | 0.4451% |
| o_proj | 0.3932% | 0.4476% |
| q_proj | 0.3154% | 0.3457% |
| up_proj | 0.3178% | 0.3710% |
| v_proj | 0.3699% | 0.4231% |

## 10 most-changed matrices

| tensor | rel change | effective rank |
|---|---|---|
| `model.layers.14.self_attn.o_proj.weight` | 0.4476% | 16 |
| `model.layers.26.self_attn.k_proj.weight` | 0.4451% | 16 |
| `model.layers.15.self_attn.o_proj.weight` | 0.4325% | 16 |
| `model.layers.18.self_attn.o_proj.weight` | 0.4284% | 16 |
| `model.layers.16.self_attn.o_proj.weight` | 0.4280% | 16 |
| `model.layers.19.self_attn.k_proj.weight` | 0.4239% | 16 |
| `model.layers.19.self_attn.o_proj.weight` | 0.4232% | 16 |
| `model.layers.19.self_attn.v_proj.weight` | 0.4231% | 16 |
| `model.layers.18.self_attn.v_proj.weight` | 0.4190% | 16 |
| `model.layers.17.self_attn.o_proj.weight` | 0.4189% | 16 |
