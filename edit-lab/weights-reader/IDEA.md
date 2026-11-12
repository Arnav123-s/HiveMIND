# Weights-reader specialist (Arnav, 2026-11-10 13:06 PT)

Arnav's idea: train a separate specialist ON WEIGHTS — it reads and maps the weights
of many LLMs, big ones included. The big LLMs are never used for inference; their
weights are the TRAINING DATA itself. The specialist learns weights as a language:
structure, meaning, what lives where.

Why now: the internals surgery round (SURGERY.md, 2026-11-10) concluded the models
were not the limit — the INSTRUMENT was. The ternary verdict model sat exactly at
its hand-crafted probe's ceiling (0.744 = 0.744). A reader that learns its own
features from raw weights is the direct answer: build a better ruler.

Status: pilot lab. Measured verdict first; nothing adopted anywhere on a claim.
