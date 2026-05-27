import pandas as pd


def parse_csv(csv_input: str) -> pd.DataFrame:
    """
    Parse a CSV and return a pandas DataFrame 

    Args:
        csv_input: A filesystem path to a CSV file
                   as a string.

    Returns:
        A pandas DataFrame.
    """
    return pd.read_csv(csv_input)
    raise NotImplementedError("Implement parse_csv in this file")
