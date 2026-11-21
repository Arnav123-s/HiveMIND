import requests
from datetime import date

# PART A
url = "https://pypi.org/pypi/pillow/json"
response = requests.get(url, timeout=30, headers={"User-Agent": "hive/1.0"})
data = response.json()
version = data["info"]["version"]
released = data["releases"][version][0]["upload_time"]
print("PART A")
print(version)
print(released)
print("It was released", (date.today() - date.fromisoformat(released[:10])).days, "days ago")

# PART B
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

result = is_prime(143)
if result:
    print("PART B")
    print("yes")
else:
    print("PART B")
    print("no")
    print("143 is not a prime number. It is divisible by 11.")