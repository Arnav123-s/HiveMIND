import math

# PART A
def to_base(n, b):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n > 0:
        out = digits[n % b] + out
        n = n // b
    return out


def from_base(s, b):
    return int(s, b)


# PART B
guitar_price = 340
price_rises_by = 10
price_falls_by = 15

guitar_price *= (1 + price_rises_by / 100)
guitar_price *= (1 - price_falls_by / 100)

# the answers
print("PART A")
print(to_base(95826, 30))
print(from_base('bn9', 25))
print("PART B")
print(guitar_price)