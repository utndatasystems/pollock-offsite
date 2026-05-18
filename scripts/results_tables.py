import argparse
import os
import pandas as pd

SUT_ORDER = ["clevercs", "csvcommons", "rhypoparsr",
             "opencsv", "pandas", "duckdbparse", "duckdbauto", "pycsv", "rcsv", "univocity",
             "mariadb", "mysql", "postgres", "sqlite", "libreoffice",
             "spreaddesktop", "spreadweb", "dataviz"]


def print_aggregate(dataset):
    path = f"results/aggregate_results_{dataset}.csv"
    if not os.path.exists(path):
        print(f"No aggregate results found for dataset '{dataset}' at {path}")
        return

    df = pd.read_csv(path, index_col='sut')
    present = [s for s in SUT_ORDER if s in df.index]
    extra = [s for s in df.index if s not in SUT_ORDER]
    missing = [s for s in SUT_ORDER if s not in df.index]

    if missing:
        print(f"Note: {len(missing)} SUT(s) from SUT_ORDER not in results and skipped: {missing}")
    if extra:
        print(f"Note: {len(extra)} SUT(s) not in SUT_ORDER, appended: {extra}")
        present += extra

    if dataset == 'polluted_files':
        subset_cols = [c for c in df.columns if '_' in c and c not in ('pollock_simple', 'pollock_weighted')]
        cols = ['pollock_simple', 'pollock_weighted'] + subset_cols
        out = df.loc[present][cols].sort_values('pollock_simple', ascending=False)
        print(out)
    else:
        out = df.loc[present][["pollock_simple", "success", "headerf1", "cellf1", "recordf1"]].sort_values('pollock_simple', ascending=False)
        print(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=None, help="Additional dataset to report (same metrics as survey_sample)")
    args = parser.parse_args()

    print("=== polluted_files ===")
    print_aggregate('polluted_files')
    print()
    print("=== survey_sample ===")
    print_aggregate('survey_sample')

    if args.dataset:
        print()
        print(f"=== {args.dataset} ===")
        print_aggregate(args.dataset)
