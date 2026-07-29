"""Deprecated compatibility entry point for the unified evaluator."""

from evaluate import main

if __name__ == "__main__":
    print(
        "evaluate_pollock.py is deprecated; running the unified evaluate.py "
        "(strict accuracy and Pollock metrics)."
    )
    main(default_dataset="polluted_files")
