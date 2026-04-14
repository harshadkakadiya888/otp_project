import random


def generate_numeric_otp(length=6):
    if length <= 0:
        return ""
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return str(random.randint(start, end))

