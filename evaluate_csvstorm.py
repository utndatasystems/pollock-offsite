"""Deprecated compatibility entry point for CSV-Storm evaluation."""

from evaluate import main


if __name__ == "__main__":
    print(
        "evaluate_csvstorm.py is deprecated; running the unified evaluate.py "
        "(strict accuracy and Pollock metrics)."
    )
    main(default_dataset="csv_storm")
