"""Extract Python from a model response without loading any model runtime."""

import re


def extract_code(text):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    if blocks:
        return max(blocks, key=len).strip()
    if "```" in text:
        return text.split("```", 1)[1].partition("\n")[2].strip()
    return text.strip()
