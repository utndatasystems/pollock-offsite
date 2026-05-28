import random
import string

from datetime import datetime, timedelta


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


def randomString(min_length: int, max_length: int) -> str:
    return "".join(
        random.choice([*string.ascii_letters, *string.digits])
        for _ in range(random.randint(min_length, max_length))
    )
