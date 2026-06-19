import json
import random
import sys

from datetime import datetime
from enum import Enum
from typing import Optional

from faker import Faker

faker = Faker(["en_US", "de_DE"])


class NumberLike(Enum):
    INT = "int"
    FLOAT = "float"
    CURRENCY = "currency"
    AS_TEXT = "as_text"


class RandomType(Enum):
    NUMBER = "number"
    DATE_STR = "date_str"
    STRING = "string"
    BOOL_STR = "bool_str"
    NULL = "null"


DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%d %b %Y",
    "%Y%m%d",
    "%A, %d %B %Y",
    "%I:%M %p %d-%m-%Y",
]


NULL_VALUES = [
    "N/A",
    "unknown",
    "NULL",
    "None",
    "NaN",
    "",
    "null",
    "undefined",
]


BOOL_VALUES = [
    "True",
    "False",
    "true",
    "false",
    "yes",
    "no",
    "y",
    "n",
    "1",
    "0",
    "wahr",
    "falsch",
]


def randomDate(
    start_date: datetime = datetime(2000, 1, 1),
    end_date: datetime = datetime(2030, 12, 31),
) -> datetime:
    return faker.date_time_between_dates(
        datetime_start=start_date,
        datetime_end=end_date,
    )


def randomDateStr(
    start_date: datetime = datetime(2000, 1, 1),
    end_date: datetime = datetime(2030, 12, 31),
    out_formats: Optional[list[str]] = None,
) -> str:
    formats = out_formats or DATE_FORMATS
    dt = randomDate(start_date, end_date)
    return dt.strftime(random.choice(formats))


def randomInt(
    min: int = -sys.maxsize,
    max: int = sys.maxsize,
) -> int:
    return faker.random_int(min=min, max=max)


def randomFloat(
    min_value: float = -1_000_000.0,
    max_value: float = 1_000_000.0,
    precision: int = 6,
) -> float:
    return round(random.uniform(min_value, max_value), precision)


def randomDigitText() -> str:
    return faker.random_element(
        elements=[
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
        ]
    )


def randomCurrency() -> str:
    return faker.random_element(
        elements=[
            "€",
            "$",
            "£",
            "¥",
            "฿",
            "Euro",
            "Dollar",
            "Baht",
        ]
    )


def randomNumberLike() -> str:
    case = faker.random_element(elements=list(NumberLike))

    if case == NumberLike.INT:
        return str(randomInt())
    elif case == NumberLike.FLOAT:
        return str(randomFloat())
    elif case == NumberLike.CURRENCY:
        value = str(randomInt()) if faker.boolean() else str(randomFloat())
        currency = randomCurrency()
        return f"{currency}{value}" if faker.boolean() else f"{value} {currency}"

    elif case == NumberLike.AS_TEXT:
        return " ".join(randomDigitText() for _ in range(random.randint(1, 4)))

    raise ValueError("Unhandled NumberLike case")


def randomString(
    min_length: int = 5,
    max_length: int = 30,
) -> str:
    target_length = random.randint(min_length, max_length)

    generators = [
        faker.word,
        faker.name,
        faker.email,
        faker.user_name,
        faker.company,
        faker.city,
        faker.uuid4,
    ]

    value = faker.random_element(generators)()

    return value[:target_length]


def randomBoolStr() -> str:
    return faker.random_element(elements=BOOL_VALUES)


def randomNull() -> str:
    return faker.random_element(elements=NULL_VALUES)


def randomType() -> str:
    random_type = faker.random_element(elements=list(RandomType))

    if random_type == RandomType.NUMBER:
        return randomNumberLike()
    elif random_type == RandomType.DATE_STR:
        return randomDateStr()
    elif random_type == RandomType.STRING:
        return randomString()
    elif random_type == RandomType.BOOL_STR:
        return randomBoolStr()
    elif random_type == RandomType.NULL:
        return randomNull()

    raise ValueError("Unhandled RandomType case")


def randomJson(
    depth: int = 0,
    max_depth: int = 3,
    max_object_size: int = 5,
    max_array_size: int = 5,
):
    """
    Generate random JSON-compatible Python objects.
    """

    def random_key():
        return faker.word()

    def random_primitive():
        PRIMITIVE_GENERATORS = [
            lambda: faker.name(),
            lambda: faker.email(),
            lambda: faker.word(),
            lambda: faker.uuid4(),
            lambda: faker.ipv4(),
            lambda: faker.url(),
            lambda: faker.phone_number(),
            lambda: faker.date(),
            lambda: faker.iso8601(),
            lambda: faker.pyint(),
            lambda: faker.pyfloat(),
            lambda: faker.boolean(),
            lambda: None,
        ]
        return random.choice(PRIMITIVE_GENERATORS)()

    # stop recursion
    if depth >= max_depth:
        return random_primitive()

    node_type = random.choice(["object", "array", "primitive"])
    if node_type == "primitive":
        return random_primitive()

    elif node_type == "array":
        return [
            randomJson(
                depth + 1,
                max_depth,
                max_object_size,
                max_array_size,
            )
            for _ in range(random.randint(1, max_array_size))
        ]

    elif node_type == "object":
        return {
            random_key(): randomJson(
                depth + 1,
                max_depth,
                max_object_size,
                max_array_size,
            )
            for _ in range(random.randint(1, max_object_size))
        }


def randomJsonStr(**kwargs) -> str:
    return json.dumps(randomJson(**kwargs))
