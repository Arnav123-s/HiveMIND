"""Measure wording overlap against the hive's checked solved-task memory."""


def familiar(task):
    from . import memory, solo
    mine = memory.words(task)
    for row in solo.solved():
        if row.get("checked") is True:
            prior = memory.words(row.get("task", ""))
            if len(mine & prior) >= 0.30 * max(1, len(mine | prior)):
                return True
    return False
