# PREFLIGHT-RESULTS — the mill's pre-first-run validations (Muse's work, Muse's side)

Run by mill/preflight.py at ts 1794566625; champion gen 0 (`--arm layered_half --rope`); code_sha dea7235bf294…

- (b) sweep parity: held_init 8.3138 vs expected 8.3138 -> PASS
- (a) probe noise: helds [6.0755, 5.8445, 5.5811], sample sd 0.2474, PROMOTE_DELTA 0.05 >= 2x sd: False -> FAIL

ACTION REQUIRED: raise PROMOTE_DELTA to 0.495 (mill/screen.py + mill/PROMOTE.md).
