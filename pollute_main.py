import argparse
import os
import pollution.polluters_stdlib_v1 as pl
import pollution.polluters_stdlib_v2 as pl2
import random
import shutil
from copy import deepcopy

from pollution.CSVFile import CSVFile
from sut.utils import print
from tqdm import tqdm
from faker import Faker

from pollution.polluters_utils import _set_polluted_filename
from pollution.combinations import apply_pollution_combination

parser = argparse.ArgumentParser()

parser.add_argument(
    "--source",
    required=True,
    choices=[
        "./results/source.csv",
    ],
    help="Path to the source CSV file to pollute",
)

parser.add_argument(
    "--output",
    required=True,
    choices=[
        "./data/polluted_files",
        "./data/original_pollock_polluted_files",
        "./data/data_gov",
        "./data/csv_storm",
        "./data/eurostat",
        "./data/survey_sample",
    ],
    help="Root output directory for polluted files",
)

parser.add_argument(
    "--polluters",
    required=False,
    choices=["pollock1.0", "pollock2.0"],
    default="pollock1.0",
    help="Which polluters to use for pollution process. Use pollock1.0 for original pollock pollutions only.",
)

parser.add_argument(
    "--per-cell-pollutions",
    action="store_true",
    help=(
        "Also generate the per-row/per-column pollutions from the original pollock 1.0 "
        "benchmark (add/remove one separator, extra quote mark, and per-row field delimiter "
        "for every row x column). Generates A LOT of files (~2272 for the default source). "
        "Required to fully reproduce the original pollock 1.0 dataset."
    ),
)

parser.add_argument(
    "--combinations",
    action="store_true",
    help=(
        "Generate curated artifacts containing interacting pollutions. "
        "Requires --polluters pollock2.0."
    ),
)

parser.add_argument(
    "--rng-seed",
    required=False,
    default="1337",
    help="RNG seed",
)

parser.add_argument(
    "--overwrite",
    action="store_true",
    help="Remove the output directory before creating polluted files",
)

args = parser.parse_args()
if args.combinations and args.polluters != "pollock2.0":
    parser.error("--combinations requires --polluters pollock2.0")

OUT_CSV_PATH = os.path.join(args.output, "csv/")
OUT_CLEAN_PATH = os.path.join(args.output, "clean/")
OUT_GROUND_TRUTH_PATH = os.path.join(args.output, "ground_truth/")
OUT_PARAMETERS_PATH = os.path.join(args.output, "parameters/")

def execute_polluter(file: CSVFile, polluter, new_filename=None, *args, **kwargs):
    """
    Executes a polluter on a CSVFile object and saves the polluted file, clean file, and parameters.
    Args:
        file: CSVFile object to pollute
        polluter: The polluter function to execute
        new_filename: Optional new filename for the polluted file
        *args: Additional positional arguments for the polluter
        **kwargs: Additional keyword arguments for the polluter
    """
    t = deepcopy(file)
    print(
        "Executing",
        polluter.__name__,
        "with arguments",
        tuple(map(lambda x: str(x)[:300], [f"{k}:{v}" for k, v in kwargs.items()])),
    )
    polluter(t, *args, **kwargs)
    if new_filename is not None:
        t.filename = new_filename
        t.xml.getroot().attrib["filename"] = new_filename
    t.write_csv(OUT_CSV_PATH)
    t.write_clean_csv(OUT_CLEAN_PATH)
    t.write_ground_truths(OUT_GROUND_TRUTH_PATH)
    t.write_parameters(OUT_PARAMETERS_PATH)


def execute_polluter_combination(
    file: CSVFile,
    *,
    steps,
):
    """Apply several polluters to one copy and persist the combined artifact."""
    combined = apply_pollution_combination(
        file,
        steps,
    )
    print(
        "Executing combination",
        combined.filename,
        "with polluters",
        tuple(polluter.__name__ for polluter, _ in steps),
    )
    combined.write_csv(OUT_CSV_PATH)
    combined.write_clean_csv(OUT_CLEAN_PATH)
    combined.write_ground_truths(OUT_GROUND_TRUTH_PATH)
    combined.write_parameters(OUT_PARAMETERS_PATH)

if args.overwrite and os.path.exists(args.output):
    if not os.path.isdir(args.output) or os.path.islink(args.output):
        raise ValueError(f"Refusing to overwrite non-directory output path: {args.output}")
    print(f"Removing existing output directory: {args.output}")
    shutil.rmtree(args.output)

os.makedirs(OUT_CSV_PATH, exist_ok=True)
os.makedirs(OUT_CLEAN_PATH, exist_ok=True)
os.makedirs(OUT_GROUND_TRUTH_PATH, exist_ok=True)
os.makedirs(OUT_PARAMETERS_PATH, exist_ok=True)

print(f"Seeding RNG: {args.rng_seed}")
random.seed(args.rng_seed)
Faker.seed(args.rng_seed)


f = CSVFile(args.source, quote_all=True)

# =============================================================================
# ORIGINAL POLLOCK 1.0 POLLUTIONS
# The block below reproduces exactly the pollutions of the original pollute_main
# These run for BOTH pollock1.0 and pollock2.0 (pollock2.0 = 1.0 + extra).
# =============================================================================

# Returns the source file : 1 file
execute_polluter(f, pl.dummyPolluter, "source.csv")

# File payload polluters : 3 files
execute_polluter(
    f, pl.changeDimension, target_dimension=0, new_filename="file_no_payload.csv"
)
execute_polluter(
    f,
    pl.changeRowRecordDelimiter,
    row=-1,
    target_delimiter="",
    new_filename="file_no_trailing_newline.csv",
)
execute_polluter(
    f,
    pl.changeRowRecordDelimiter,
    row=-1,
    target_delimiter="\r\n\r\n",
    new_filename="file_double_trailing_newline.csv",
)

# Header and preamble polluters : 7 files
execute_polluter(
    f,
    pl.changeNumberRows,
    target_number_rows=f.row_count,
    remove_header=True,
    new_filename="file_no_header.csv",
)
execute_polluter(f, pl.expandColumnHeader, extra_rows=1, new_filename="file_header_multirow_2.csv")
execute_polluter(f, pl.expandColumnHeader, extra_rows=2, new_filename="file_header_multirow_3.csv")

# two program branches as the params differ between original
# pollock and CSVStorm
if args.polluters == "pollock1.0":
    execute_polluter(
        f,
        pl.addPreamble,
        n_rows=1,
        delimiters=True,
        emptyrow=True,
        new_filename="file_preamble.csv",
    )
    execute_polluter(
        f,
        pl.addTable,
        new_filename="file_multitable_less.csv",
        n_rows=f.row_count - 1,
        n_cols=f.col_count - 1,
        empty_boundary=False,
    )
    execute_polluter(
        f,
        pl.addTable,
        new_filename="file_multitable_same.csv",
        n_rows=f.row_count - 1,
        n_cols=f.col_count,
        empty_boundary=False,
    )
    execute_polluter(
        f,
        pl.addTable,
        new_filename="file_multitable_more.csv",
        n_rows=f.row_count - 1,
        n_cols=f.col_count + 1,
        empty_boundary=False,
    )
else:
    # Pollock 2.0 preamble + multitable sizing (richer preamble, larger deltas).
    execute_polluter(
        f,
        pl.addPreamble,
        n_rows=1,
        delimiters=True,
        emptyrow=True,
        new_filename="file_preamble.csv",
        cell_content=(
            " Export: product_activity_sample.csv\n"
            " Source system: Retail catalog / order activity reporting\n"
            " Generated by: Merchandising Analytics\n"
            " Export date: 2018-07-25\n"
            " Description:\n"
            " This file contains sampled product activity records for selected catalog items."
        ),
    )
    
    # execute_polluter(
    #     f,
    #     pl.addTable,
    #     new_filename="file_multitable_less.csv",
    #     n_rows=f.row_count - 10,
    #     n_cols=f.col_count - 2,
    #     empty_boundary=False,
    # )
    # execute_polluter(
    #     f,
    #     pl.addTable,
    #     new_filename="file_multitable_same.csv",
    #     n_rows=f.row_count - 1,
    #     n_cols=f.col_count,
    #     empty_boundary=False,
    # )
    # execute_polluter(
    #     f,
    #     pl.addTable,
    #     new_filename="file_multitable_more.csv",
    #     n_rows=f.row_count - 1,
    #     n_cols=f.col_count + 10,
    #     empty_boundary=False,
    # )

# Data rows: 2 files
execute_polluter(
    f, pl.changeNumberRows, new_filename="file_header_only.csv", target_number_rows=1
)
execute_polluter(
    f, pl.changeNumberRows, new_filename="file_one_data_row.csv", target_number_rows=2
)

# per cell pollutions
if args.per_cell_pollutions:

    # Manually decrease row_count for pollutions
    old_row_count = f.row_count
    f.row_count = min(f.row_count, 2)

    for i in tqdm(range(1, f.row_count)):
        for j in range(f.col_count):
            execute_polluter(f, pl.addRowFieldDelimiter, new_filename=f"row_more_sep_row{i}_col{j}.csv", row=i, col=j)  # row 1, empty
            if j > 0:
                execute_polluter(f, pl.deleteRowFieldDelimiter, new_filename=f"row_less_sep_row{i}_col{j}.csv", row=i, col=j)  # row 1, empty
            execute_polluter(f, pl.addRowQuoteMark, new_filename=f"row_extra_quote{i}_col{j}.csv", row=i, col=j)  # row 1, empty

        vals = [ord(x) for x in " "]
        del_string = ''.join([f'_0x{v:X}' for v in vals])
        target_filename = f"row_field_delimiter_{i}{del_string}.csv"
        execute_polluter(f, pl.changeRowFieldDelimiter, new_filename=target_filename, row=i, target_delimiter=" ")

    # Restore: later polluters rely on the real row_count
    f.row_count = old_row_count # TODO: remove after manually decrease rowcount above is removed again

# Change record Delimiter : 2 files
execute_polluter(f, pl.changeRecordDelimiter, target_delimiter="\n")
execute_polluter(f, pl.changeRecordDelimiter, target_delimiter="\r")

# Change delimiter everywhere : 4 files
execute_polluter(f, pl.changeFieldDelimiter, target_delimiter=";")
execute_polluter(f, pl.changeFieldDelimiter, target_delimiter="\t")
execute_polluter(f, pl.changeFieldDelimiter, target_delimiter=", ")
execute_polluter(f, pl.changeFieldDelimiter, target_delimiter=" ")

# Change quotation mark everywhere : 1 file
execute_polluter(f, pl.changeQuotationChar, target_char="'")

# Change escape character : 2 files
execute_polluter(f, pl.changeEscapeCharacter, target_escape="\u005C")   # backslash
execute_polluter(f, pl.changeEscapeCharacter, target_escape="")         # no escape character
#execute_polluter(f, pl.changeEscapeCharacter, target_escape="WATCHOUT")     # Test Case for check if pollution works


# --- NEW POLLUTIONS FOR POLLOCK 2.0 ---

if args.polluters == "pollock2.0":

    execute_polluter(f, pl.changeQuotationChar, target_char="")  # deleted quotation character everywhere

    # Null values
    # Removed this because this is dangerously close to data repair 
    #execute_polluter(f, pl2.differentNullValues, null_values=["NULL", "N/A", "NaN", "", "None", "undefined"])

    # Multi-table / layout structure
    #execute_polluter(f, pl2.addTableSideways, n_rows=min(f.row_count, 5), n_cols=min(f.col_count, 5))
    execute_polluter(f, pl2.multilineHeader, header_rows=3) # checked

    # removed because duplicate to fileheadeMultirow(2)
    #execute_polluter(f, pl2.duplicateHeaderIntoRows) 
    execute_polluter(f, pl2.superheader, 
        groups={
            "Transaction Info": [0, 1],
            "Product Info": [2, 3, 4, 5, 6, 7],
            "Notes": [8],
        },
        sparse=True,
    )

    # Footnote
    # Simple
    execute_polluter(f, pl2.addFootnote, n_rows=1, blank_line=False)
    # Multi-line
    execute_polluter(f, pl2.addFootnote, n_rows=3, blank_line=False)
    # Multi-line with blank line to separate
    execute_polluter(f, pl2.addFootnote, n_rows=3, blank_line=True)

    # Row / column irregularities
    execute_polluter(f, pl2.moveHeaderRow)
    execute_polluter(f, pl2.extremelyLongFields, row=3 if f.row_count >= 3 else 3, col=6, length=10000)  # For the final evaluation, we have to make sure th insert something extremely long of the same data type as the original cell
    #execute_polluter(f, pl2.addTrailingCommentToFile, comment="This article is no longer being sold.")

    # Comments in Rows (row location is set random, but can be set with param e.g. row = 3)
    execute_polluter(f, pl2.commentRow, comment_marker="#") 
    execute_polluter(f, pl2.commentRow, comment_marker="//")
    execute_polluter(f, pl2.commentRow, comment_marker="<!--")
    # Variable-width rows: split into explicit wider and narrower cases so
    # deleted-value ground truth can be handled differently from extra fields.
    for i in range(5):
        execute_polluter(f, pl2.moreColumns)
        execute_polluter(f, pl2.lessColumnsDeletedValues)

    execute_polluter(f, pl2.unquotedList, max_list_len=5) # automatically chooses safe row/column

    # Delimiter / quoting / escaping edge cases
    # Mixed delimiters, unescaped delimiters, double escaping, unquoted lists, whitespace-formatted tables
    execute_polluter(
        f,
        pl2.mixedDelimiters,
        row=2 if f.row_count >= 2 else 1,
        delimiters=[";"],
        mode="within_row",
    )
    execute_polluter(
        f,
        pl2.mixedDelimiters,
        row=2 if f.row_count >= 2 else 1,
        delimiters=[";"],
        mode="within_row",
        range_within_row=3,
    )
    execute_polluter(
        f,
        pl2.mixedDelimiters,
        row=2 if f.row_count >= 2 else 1,
        delimiters=[";"],
        mode="whole_row",
    )

    execute_polluter(f, pl2.unescapedMultiLineString, row=2 if f.row_count >= 2 else 1, col=1)
    execute_polluter(f, pl2.doubleEscaping, row=2 if f.row_count >= 2 else None, col=7, escaping="double_quote",)
    execute_polluter(f, pl2.doubleEscaping, row=3 if f.row_count >= 3 else None, col=7, escaping="backslash",)
    execute_polluter(f, pl2.tableToWhitespaceFormattedTable, pad_cells=False)
    execute_polluter(f, pl2.tableToWhitespaceFormattedTable, pad_cells=True, quote_strings=True)
    execute_polluter(f, pl2.tableToWhitespaceFormattedTable, pad_cells=True, quote_strings=False)

    # Spreadsheet / Excel-style edge cases
    execute_polluter(f, pl2.excelExportAutoformat)
    execute_polluter(f, pl2.exelExportFormulas)

    # Type ambiguity / mixed values
    execute_polluter(f, pl2.typeAmbiguity)
    #execute_polluter(f, pl2.mixedTypes) unsure if this makes sense
    execute_polluter(f, pl2.mixedTimeformats)

    # Embedded semi-structured payloads
    execute_polluter(f, pl2.embeddedJSON, row=2, start_col=1, l_col=4)
    execute_polluter(f, pl2.embeddedCSV)

    # changeRowQuotationMark() - originally missing in Pollock benchmark 
    execute_polluter(f, pl.changeRowQuotationMark, row=2 if f.row_count >= 2 else 1, target_quotation="'")

    # Structural Stress Tests
    execute_polluter(f, pl.changeNumberColumns, target_number_cols = 1000, pad_with_random_ints=True) # extreme width (TODO make larger after code-iteration is over, currently not even 1MB)
    execute_polluter(f, pl.changeNumberColumns, target_number_cols = 1000, pad_with_random_ints=False) # repeats last column
    execute_polluter(f, pl.changeNumberRows, target_number_rows=1000, repeat_file = True) # Long CSV # TODO make number larger after code-iteration is over




if args.combinations:
    # Two interacting pollutions.
    execute_polluter_combination(
        f,
        steps=[
            (pl2.moveHeaderRow, {"row": 5}),
            (
                pl.addPreamble,
                {
                    "n_rows": 2,
                    "emptyrow": True,
                    "cell_content": [
                        "Export: product_activity_sample.csv",
                        "Section: catalog activity",
                    ],
                },
            ),
        ],
    )
    execute_polluter_combination(
        f,
        steps=[
            (pl2.multilineHeader, {"header_rows": 3}),
            (
                pl2.addFootnote,
                {
                    "n_rows": 2,
                    "blank_line": True,
                    "cell_content": "Source: catalog activity export",
                },
            ),
        ],
    )
    execute_polluter_combination(
        f,
        steps=[
            (pl2.moreColumns, {"row": 10}),
            (
                pl2.mixedDelimiters,
                {
                    "row": 11,
                    "delimiters": [";"],
                    "mode": "within_row",
                    "range_within_row": 3,
                },
            ),
        ],
    )
    execute_polluter_combination(
        f,
        steps=[
            (
                pl.changeRowQuotationMark,
                {"row": 2, "target_quotation": "'"},
            ),
            (
                pl2.mixedDelimiters,
                {
                    "row": 2,
                    "delimiters": [";"],
                    "mode": "within_row",
                    "range_within_row": 3,
                },
            ),
        ],
    )

    # Three interacting syntactic and semantic pollutions.
    execute_polluter_combination(
        f,
        steps=[
            (pl2.moveHeaderRow, {"row": 5}),
            (
                pl.addPreamble,
                {
                    "n_rows": 2,
                    "emptyrow": True,
                    "cell_content": [
                        "Export: product_activity_sample.csv",
                        "Section: catalog activity",
                    ],
                },
            ),
            (
                pl2.addFootnote,
                {
                    "n_rows": 2,
                    "blank_line": True,
                    "cell_content": "Source: catalog activity export",
                },
            ),
        ],
    )
    execute_polluter_combination(
        f,
        steps=[
            (pl2.multilineHeader, {"header_rows": 3}),
            (
                pl2.mixedDelimiters,
                {
                    "row": 4,
                    "delimiters": [";"],
                    "mode": "within_row",
                    "range_within_row": 3,
                },
            ),
            (
                pl2.addFootnote,
                {
                    "n_rows": 2,
                    "blank_line": True,
                    "cell_content": "Source: catalog activity export",
                },
            ),
        ],
    )

print("Pollution process complete.")
