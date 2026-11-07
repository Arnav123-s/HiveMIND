# Weight edit report: verifier

Base model: `Qwen/Qwen3-1.7B`  
Edited: 98 matrices in layers 14-27 (down_proj, gate_proj, k_proj, o_proj, q_proj, up_proj, v_proj); rank 8, alpha 32; 4,358,144 trained numbers.

## Mean relative change ||dW||/||W|| by layer

| layer | mean | max |
|---|---|---|
| 14 | 0.6018% | 0.7028% |
| 15 | 0.6119% | 0.7285% |
| 16 | 0.6100% | 0.7366% |
| 17 | 0.6156% | 0.7306% |
| 18 | 0.6516% | 0.7910% |
| 19 | 0.6436% | 0.7738% |
| 20 | 0.6038% | 0.7185% |
| 21 | 0.5715% | 0.7058% |
| 22 | 0.5966% | 0.6837% |
| 23 | 0.5918% | 0.6890% |
| 24 | 0.5938% | 0.6960% |
| 25 | 0.5810% | 0.6845% |
| 26 | 0.5675% | 0.6943% |
| 27 | 0.5807% | 0.6608% |

## By module

| module | mean | max |
|---|---|---|
| down_proj | 0.3739% | 0.4230% |
| gate_proj | 0.6398% | 0.6934% |
| k_proj | 0.6774% | 0.7405% |
| o_proj | 0.6965% | 0.7910% |
| q_proj | 0.5859% | 0.6608% |
| up_proj | 0.5922% | 0.6513% |
| v_proj | 0.6449% | 0.7738% |

## 10 most-changed matrices

| tensor | rel change | effective rank |
|---|---|---|
| `model.layers.18.self_attn.o_proj.weight` | 0.7910% | 8 |
| `model.layers.19.self_attn.v_proj.weight` | 0.7738% | 8 |
| `model.layers.19.self_attn.o_proj.weight` | 0.7600% | 8 |
| `model.layers.19.self_attn.k_proj.weight` | 0.7405% | 8 |
| `model.layers.16.self_attn.o_proj.weight` | 0.7366% | 8 |
| `model.layers.17.self_attn.o_proj.weight` | 0.7306% | 8 |
| `model.layers.15.self_attn.o_proj.weight` | 0.7285% | 8 |
| `model.layers.20.self_attn.o_proj.weight` | 0.7185% | 8 |
| `model.layers.20.self_attn.k_proj.weight` | 0.7096% | 8 |
| `model.layers.21.self_attn.o_proj.weight` | 0.7058% | 8 |
