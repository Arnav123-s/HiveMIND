def to_base(n, b):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        out = digits[n % b] + out
        n //= b
        if not n:
            return out


def from_base(s, b):
    return int(s, b)


if __name__ == "__main__":
    import shutil

    shutil.copy(__file__, 'bases.py')
    assert from_base(to_base(255, 16), 16) == 255
    print(to_base(29965, 12))
    print(from_base('5ccm', 25))