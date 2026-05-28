import random
import string


def randomString(min_length: int, max_length: int) -> str:
    return "".join(
        random.choice([*string.ascii_letters, *string.digits])
        for _ in range(random.randint(min_length, max_length))
    )
