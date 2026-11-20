def to_seconds(s):
    import re
    return sum(int(n) * {"h": 3600, "m": 60, "s": 1}.get(c, 1) for n, c in re.findall(r"(\d+)([hms])", s))

def to_text(n):
    if n == 0:
        return "0s"
    hours = n // 3600
    minutes = (n % 3600) // 60
    seconds = n % 60
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return "".join(parts)
