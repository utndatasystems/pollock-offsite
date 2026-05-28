import random
import string
import sys

from datetime import datetime, timedelta
from enum import Enum


def randomDate(
    start_date=datetime(2000, 1, 1), end_date=datetime(2030, 12, 31)
) -> datetime:
    return start_date + timedelta(
        seconds=random.randint(0, int((end_date - start_date).total_seconds()))
    )


def randomDateStr(
    start_date=datetime(2000, 1, 1),
    end_date=datetime(2030, 12, 31),
    out_formats=[
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%Y%m%d",
        "%A, %d %B %Y",
        "%I:%M %p %d-%m-%Y",
    ],
) -> str:
    return randomDate(start_date=start_date, end_date=end_date).strftime(
        random.choice(out_formats)
    )


def randomFloat(min: float = -13374201337.123, max: float = 4201337420.321) -> float:
    return min + random.random() * (max - min)


def randomDigitText() -> str:
    return random.choice(
        ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    )


def randomCurrency() -> str:
    return random.choice(["€", "Euro", "Eur", "$", "Dollar", "฿", "Baht"])


def randomNumberLike() -> str:
    class NumberLike(Enum):
        INT = 1
        FLOAT = 2
        CURRENCY = 3
        AS_TEXT = 4

    case = random.choice(list(NumberLike))
    if case == NumberLike.INT:
        return str(random.randint(-sys.maxsize, sys.maxsize))
    elif case == NumberLike.FLOAT:
        return str(randomFloat())
    elif case == NumberLike.CURRENCY:
        num = (
            str(random.randint(-sys.maxsize, sys.maxsize))
            if random.randint(0, 1) == 1
            else str(randomFloat())
        )
        curr = randomCurrency()
        space = random.choice(["", " "])
        return space.join([num, curr] if random.randint(0, 1) == 1 else [curr, num])
    elif case == NumberLike.AS_TEXT:
        return "".join(randomDigitText() for _ in range(random.randint(1, 3)))


def randomString(min_length: int = 0, max_length: int = 20) -> str:
    return "".join(
        random.choice([*string.ascii_letters, *string.digits])
        for _ in range(random.randint(min_length, max_length))
    )


def randomBoolStr() -> str:
    return random.choice(
        [
            str(True),
            str(False),
            "true",
            "false",
            "y",
            "n",
            "yes",
            "no",
            "wahr",
            "falsch",
        ]
    )


def randomNull() -> str:
    return random.choice(["N/A", "unknown", "0", "NULL", "None", "NaN", "", "NUL"])


def randomType() -> str:
    class Types(Enum):
        NUMBER = 1
        DATE_STR = 2
        STRING = 3
        BOOL_STR = 4
        NULL = 5

    type = random.choice(list(Types))
    if type == Types.NUMBER:
        return randomNumberLike()
    elif type == Types.DATE_STR:
        return randomDateStr()
    elif type == Types.STRING:
        return randomString()
    elif type == Types.BOOL_STR:
        return randomBoolStr()
    elif type == Types.NULL:
        return randomNull()
