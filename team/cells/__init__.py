"""Cells: the hive's smallest specialists.

Every cell is one tiny model trained for ONE micro-skill (route a step, spot a purchase order, check one claim,
pick one element...). It does nothing else, and is allowed to be bad at everything else: other cells cover that.
All cells share one small frozen base model in memory; each cell owns only a few small weight deltas, placed on
the modules the locator found carry its skill (`training/cells.py`). The `gate` cell routes free-form inputs to
cells, like the gate of a mixture of experts, and a new skill gets a cell by cloning the nearest one and editing
the clone's weights (`training/cells.py factory`).
"""
