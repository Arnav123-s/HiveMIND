# Weight edit report: coordinator

Base model: `Qwen/Qwen3-1.7B`  
Edited: 98 matrices in layers 14-27 (down_proj, gate_proj, k_proj, o_proj, q_proj, up_proj, v_proj); rank 16, alpha 32; 8,716,288 trained numbers.

## Mean relative change ||dW||/||W|| by layer

| layer | mean | max |
|---|---|---|
| 14 | 0.4043% | 0.4922% |
| 15 | 0.4075% | 0.4775% |
| 16 | 0.3931% | 0.4852% |
| 17 | 0.3940% | 0.4681% |
| 18 | 0.4036% | 0.5023% |
| 19 | 0.3815% | 0.4687% |
| 20 | 0.3617% | 0.4354% |
| 21 | 0.3415% | 0.4266% |
| 22 | 0.3382% | 0.4154% |
| 23 | 0.3413% | 0.4121% |
| 24 | 0.3421% | 0.4233% |
| 25 | 0.3398% | 0.4136% |
| 26 | 0.3356% | 0.4264% |
| 27 | 0.3396% | 0.3955% |

## By module

| module | mean | max |
|---|---|---|
| down_proj | 0.2337% | 0.2823% |
| gate_proj | 0.3641% | 0.4147% |
| k_proj | 0.4175% | 0.4554% |
| o_proj | 0.4412% | 0.5023% |
| q_proj | 0.3512% | 0.3805% |
| up_proj | 0.3451% | 0.4221% |
| v_proj | 0.4091% | 0.4572% |

## 10 most-changed matrices

| tensor | rel change | effective rank |
|---|---|---|
| `model.layers.18.self_attn.o_proj.weight` | 0.5023% | 16 |
| `model.layers.14.self_attn.o_proj.weight` | 0.4922% | 16 |
| `model.layers.16.self_attn.o_proj.weight` | 0.4852% | 16 |
| `model.layers.15.self_attn.o_proj.weight` | 0.4775% | 16 |
| `model.layers.19.self_attn.o_proj.weight` | 0.4687% | 16 |
| `model.layers.17.self_attn.o_proj.weight` | 0.4681% | 16 |
| `model.layers.15.self_attn.v_proj.weight` | 0.4572% | 16 |
| `model.layers.18.self_attn.k_proj.weight` | 0.4554% | 16 |
| `model.layers.18.self_attn.v_proj.weight` | 0.4544% | 16 |
| `model.layers.19.self_attn.v_proj.weight` | 0.4539% | 16 |
