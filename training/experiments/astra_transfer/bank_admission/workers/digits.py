import requests
from datetime import datetime

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def get_nth_prime(n):
    count = 0
    num = 2
    while True:
        if is_prime(num):
            count += 1
            if count == n:
                return num
        num += 1

def get_digit_sum(n):
    return sum(int(d) for d in str(n))

nth_prime = get_nth_prime(2566)
digit_sum = get_digit_sum(nth_prime)
print(f"Prime number 2566: {nth_prime}")
print(f"Sum of its digits: {digit_sum}")