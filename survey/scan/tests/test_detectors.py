"""Unit tests for survey.scan detectors.

Run with::

    /home/jkossmann/pollock-offsite/.venv/bin/python -m unittest \\
        survey.scan.tests.test_detectors -v

Each detector has a positive case (correct line numbers) and a negative
case (clean CSV → empty result). A handful of edge cases protect against
the false-positive traps we anticipated during planning.
"""

from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path

from survey.scan.detectors import (
    DEFAULT_LONG_FIELD_CHARS,
    DEFAULT_MAX_BYTES,
    POLLUTION_NAMES,
    scan_file,
)
from survey.scan.runner import run_scan


def _write(tmp: Path, name: str, content: str | bytes) -> Path:
    p = tmp / name
    if isinstance(content, str):
        p.write_text(content, encoding="utf-8")
    else:
        p.write_bytes(content)
    return p


# ---------------------------------------------------------------------------
# Per-detector positive + negative tests
# ---------------------------------------------------------------------------


class TestComments(unittest.TestCase):
    def test_leading_hash_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "# CO2 melting data\n"
                "# Communicated by Smith 2004\n"
                "name,age,role\n"
                "Alice,30,eng\n"
                "Bob,40,manager\n"
                "Carol,25,intern\n"
                "Dave,35,sci\n"
                "Eve,45,sci\n"
            )
            p = _write(tmp, "comments.csv", csv_text)
            r, _ = scan_file(p)
            self.assertIn(1, r["comments"])
            self.assertIn(2, r["comments"])
            self.assertEqual(r["long_fields"], [])

    def test_dashdash_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "-- preamble line\n"
                "name,age\n"
                "Alice,30\n"
                "Bob,40\n"
                "Carol,25\n"
                "Dave,35\n"
                "Eve,45\n"
            )
            p = _write(tmp, "dd.csv", csv_text)
            r, _ = scan_file(p)
            self.assertIn(1, r["comments"])

    def test_dashdash_alone_is_null_not_comment(self):
        # "--" appearing as a standalone cell is a null token, not a comment.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,age\n"
                "Alice,30\n"
                "Bob,--\n"
                "Carol,25\n"
                "Dave,35\n"
                "Eve,45\n"
            )
            p = _write(tmp, "dd_null.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["comments"], [])

    def test_clean_no_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,age\n"
                "Alice,30\n"
                "Bob,40\n"
                "Carol,25\n"
                "Dave,35\n"
                "Eve,45\n"
            )
            p = _write(tmp, "clean.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["comments"], [])


class TestLongFields(unittest.TestCase):
    def test_long_field_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            blob = "x" * 3000
            csv_text = (
                "name,note\n"
                "a,short\n"
                f'b,"{blob}"\n'
                "c,short\n"
                "d,short\n"
                "e,short\n"
            )
            p = _write(tmp, "long.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["long_fields"], [3])

    def test_short_fields_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,note\n"
                "a,short\n"
                "b,medium-content-here\n"
                "c,bigger but still nowhere near the threshold\n"
                "d,short\n"
                "e,short\n"
            )
            p = _write(tmp, "short.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["long_fields"], [])

    def test_threshold_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,note\n"
                "a,short\n"
                "b,1234567890\n"
                "c,short\n"
                "d,short\n"
                "e,short\n"
            )
            p = _write(tmp, "thresh.csv", csv_text)
            r, _ = scan_file(p, long_field_chars=5)
            # row 2 ("1234567890" = 10 chars) and the header itself ("note"=4
            # is fine, "name"=4 is fine). Only b's note is over 5 chars.
            self.assertIn(3, r["long_fields"])


class TestVariableColumns(unittest.TestCase):
    def test_jagged_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "a,b,c\n"
                "1,2,3\n"
                "4,5,6\n"
                "7,8\n"          # jagged at line 4
                "9,10,11\n"
                "12,13,14\n"
                "15,16,17\n"
            )
            p = _write(tmp, "jagged.csv", csv_text)
            r, _ = scan_file(p)
            self.assertIn(4, r["variable_columns"])

    def test_consistent_no_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "a,b,c\n"
                "1,2,3\n"
                "4,5,6\n"
                "7,8,9\n"
                "10,11,12\n"
                "13,14,15\n"
            )
            p = _write(tmp, "ok.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["variable_columns"], [])

    def test_too_few_rows_no_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = "a,b\n1,2\n3,4,5\n"
            p = _write(tmp, "tiny.csv", csv_text)
            r, _ = scan_file(p)
            # Below _MIN_DATA_ROWS_FOR_MODE: not flagged.
            self.assertEqual(r["variable_columns"], [])


class TestMixedDelimiter(unittest.TestCase):
    def test_no_mix_for_clean_comma_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,age,city\n"
                "Alice,30,NYC\n"
                "Bob,40,LA\n"
                "Carol,25,SF\n"
                "Dave,35,DC\n"
                "Eve,45,NYC\n"
            )
            p = _write(tmp, "comma.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["mixed_delimiter"], [])

    def test_secondary_delim_only_inside_quotes_not_mixed(self):
        # Comma is the field delimiter; semicolons appear only inside
        # quoted cells — must not be flagged as mixed.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                'id,authors,title\n'
                '1,"Alice; Bob; Carol",Paper one\n'
                '2,"Dave; Eve; Frank; Grace",Paper two\n'
                '3,"Helen; Igor",Paper three\n'
                '4,"Jane; Karl; Laila",Paper four\n'
                '5,"Mira; Nora",Paper five\n'
                '6,"Oscar",Paper six\n'
            )
            p = _write(tmp, "quoted_semi.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["mixed_delimiter"], [])

    def test_european_decimal_comma_not_flagged(self):
        # Semicolon-delimited file with European-locale decimal commas
        # inside numeric values; not mixed.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "code;a;b;c\n"
                "x1;0,00;1,50;2,75\n"
                "x2;3,14;1,41;2,72\n"
                "x3;0,01;0,02;0,03\n"
                "x4;9,99;8,88;7,77\n"
                "x5;1,11;2,22;3,33\n"
                "x6;4,44;5,55;6,66\n"
            )
            p = _write(tmp, "eu_decimals.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["mixed_delimiter"], [])

    def test_clean_semicolon_not_mixed(self):
        # Semicolon-only, no commas in data → not flagged.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name;age;city\n"
                "Alice;30;NYC\n"
                "Bob;40;LA\n"
                "Carol;25;SF\n"
                "Dave;35;DC\n"
                "Eve;45;NYC\n"
            )
            p = _write(tmp, "semi.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["mixed_delimiter"], [])

    def test_unquoted_prose_with_commas_not_mixed(self):
        # ;-delimited file where unquoted prose cells contain commas as
        # punctuation. The sniffer correctly picks ';'; ',' splits most
        # rows consistently enough (~70%) to look plausible under the old
        # gate, but its modal frequency is well below ';''s, so the
        # tightened gate must reject it.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "uid;authority;position;unit;value\n"
                "1;Ministry of Energy, Coal, and Natural Resources;Director;Dept of Strategy, Policy, Planning;1\n"
                "2;Ministry of Energy, Coal, and Natural Resources;Deputy;Dept of Operations;1\n"
                "3;Ministry of Energy, Coal, and Natural Resources;Head;Dept of Strategy, Policy;1\n"
                "4;Ministry of Energy, Coal, and Natural Resources;Lead;Section A, Group 2;1\n"
                "5;Ministry of Energy, Coal, and Natural Resources;Officer;Dept of Strategy, Policy;1\n"
                "6;Ministry of Energy, Coal, and Natural Resources;Specialist;Section A;1\n"
            )
            p = _write(tmp, "prose_commas.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["mixed_delimiter"], [])

    def test_coordinate_comma_not_mixed(self):
        # ;-delimited file with unquoted "lat, lon" in last column.
        # The single comma per row is cell content, not a delimiter.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "id;name;type;lat;lon;location\n"
                "1;Station A;Type X;52.637;-1.131;52.637, -1.131\n"
                "2;Station B;Type Y;52.774;-1.207;52.774, -1.207\n"
                "3;Station C;Type X;52.581;-1.103;52.581, -1.103\n"
                "4;Station D;Type Z;52.638;-1.131;52.638, -1.131\n"
                "5;Station E;Type X;52.762;-1.196;52.762, -1.196\n"
                "6;Station F;Type Y;52.800;-1.200;52.800, -1.200\n"
            )
            p = _write(tmp, "coords.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["mixed_delimiter"], [])


class TestHeaderMismatch(unittest.TestCase):
    def test_header_too_few_cols(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # Header has 2 cols; data has 3 cols.
            csv_text = (
                "name,age\n"
                "Alice,30,NYC\n"
                "Bob,40,LA\n"
                "Carol,25,SF\n"
                "Dave,35,DC\n"
                "Eve,45,NYC\n"
                "Frank,50,DC\n"
            )
            p = _write(tmp, "hdr.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["header_mismatch"], [1])

    def test_header_after_comment_preamble_not_flagged(self):
        # Regression: comment lines before the real header must not be
        # mistaken for the header. Real header (line 2) matches data.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "# leading comment\n"
                "name,age\n"
                "Alice,30\n"
                "Bob,40\n"
                "Carol,25\n"
                "Dave,35\n"
                "Eve,45\n"
            )
            p = _write(tmp, "hdr_comment.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["header_mismatch"], [])

    def test_header_matches_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "a,b,c\n"
                "1,2,3\n"
                "4,5,6\n"
                "7,8,9\n"
                "10,11,12\n"
                "13,14,15\n"
            )
            p = _write(tmp, "ok.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["header_mismatch"], [])


class TestLineMapping(unittest.TestCase):
    """Regression tests for the row-start line-number state machine.

    The previous naive impl counted quote chars per line and toggled
    state on odd parity; it broke on doubled-quote escapes and on quote
    chars appearing in unquoted cells. These tests pin down both cases
    so any future regression is visible.
    """

    def test_doubled_quote_escapes_dont_break_mapping(self):
        # Row 2's quoted cell contains "" (escaped quote). Old naive impl
        # would toggle quote state mid-line and misalign every following
        # row; new state machine handles it.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                'id,note\n'
                '1,"He said ""hi"" then left"\n'
                '2,plain\n'
                '3,"another ""quoted"" word"\n'
                '4,plain\n'
                '5,plain\n'
                '6,plain\n'
            )
            p = _write(tmp, "doubled.csv", csv_text)
            r, _ = scan_file(p)
            # No spurious flags from misaligned mapping
            self.assertEqual(r["null_mismatch"], [])
            self.assertEqual(r["variable_columns"], [])
            self.assertEqual(r["comments"], [])

    def test_multiline_quoted_cell_keeps_subsequent_lines_aligned(self):
        # Row 2's quoted cell spans two raw lines. Subsequent rows must
        # still map to their correct line numbers.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                'id,note\n'
                '1,"line1\nline2"\n'
                '2,plain\n'
                '3,plain\n'
                '4,plain\n'
                '5,plain\n'
                '6,plain\n'
            )
            p = _write(tmp, "multi.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["unquoted_multiline"], [])
            self.assertEqual(r["variable_columns"], [])

    def test_bare_cr_line_endings_advance_line_counter(self):
        # Mac-classic line endings (bare \r). Earlier impl had a no-op
        # ``line_no += 0`` in the \r branch, collapsing every row to
        # line 1 and producing spurious flags downstream.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_bytes = (
                b"id,note\r"
                b"1,plain\r"
                b"2,plain\r"
                b"3,plain\r"
                b"4,plain\r"
                b"5,plain\r"
                b"6,plain\r"
            )
            p = _write(tmp, "cr.csv", csv_bytes)
            r, _ = scan_file(p)
            self.assertEqual(r["comments"], [])
            self.assertEqual(r["null_mismatch"], [])
            self.assertEqual(r["variable_columns"], [])

    def test_unquoted_quote_char_does_not_toggle_state(self):
        # A `"` appearing in an unquoted cell (e.g., 5'9") is a literal
        # to clevercsv. Old impl toggled state on the lone `"`; new impl
        # only treats `"` as opening when it's at the cell start.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                'id,height\n'
                '1,5\'9"\n'
                '2,6\'1"\n'
                '3,5\'7"\n'
                '4,5\'10"\n'
                '5,6\'0"\n'
                '6,5\'8"\n'
            )
            p = _write(tmp, "heights.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["null_mismatch"], [])
            self.assertEqual(r["variable_columns"], [])


class TestHeaderMismatchEdgeCases(unittest.TestCase):
    def test_string_heavy_first_data_row_does_not_force_mismatch_flag(self):
        # First data row is all strings (e.g., text-only categorical
        # row). The detector's heuristic might extend the header into
        # row 2, but column counts match so no mismatch should be flagged.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "label,category,description\n"
                "alpha,low,first row text\n"
                "beta,high,second row text\n"
                "gamma,low,third row text\n"
                "delta,high,fourth row text\n"
                "epsilon,low,fifth row text\n"
                "zeta,high,sixth row text\n"
            )
            p = _write(tmp, "string_heavy.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["header_mismatch"], [])

    def test_id_like_header_with_numeric_data_no_false_positive(self):
        # ID-like first column followed by numeric data; header detection
        # must still get the right shape.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "user_id,score,rank\n"
                "u001,42,3\n"
                "u002,55,1\n"
                "u003,48,2\n"
                "u004,30,5\n"
                "u005,38,4\n"
                "u006,22,6\n"
            )
            p = _write(tmp, "ids.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["header_mismatch"], [])


class TestUnquotedMultiline(unittest.TestCase):
    def test_quoted_multiline_not_flagged(self):
        # Properly-quoted multiline value: not flagged.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                'a,b\n'
                '1,"hello\nworld"\n'
                '2,"foo"\n'
                '3,"bar"\n'
                '4,"baz"\n'
                '5,"qux"\n'
            )
            p = _write(tmp, "quoted.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["unquoted_multiline"], [])

    def test_clean_no_multiline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = "a,b\n1,2\n3,4\n5,6\n7,8\n9,10\n"
            p = _write(tmp, "clean.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["unquoted_multiline"], [])


class TestEncodingIssues(unittest.TestCase):
    def test_invalid_utf8_flagged(self):
        # A valid cp1252 byte ("é" = 0xE9) by itself is invalid UTF-8.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            content = b"name,note\nAlice,caf\xe9\nBob,plain\nCarol,plain\nDave,plain\nEve,plain\n"
            p = _write(tmp, "bad.csv", content)
            r, _ = scan_file(p)
            self.assertTrue(any(line == 2 for line in r["encoding_issues"]))

    def test_clean_utf8_no_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = "name,note\nAlice,café\nBob,plain\nCarol,plain\nDave,plain\nEve,plain\n"
            p = _write(tmp, "good.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["encoding_issues"], [])

    def test_mojibake_flagged(self):
        # "café" mojibaked to "cafÃ©" (UTF-8 bytes from cp1252-as-UTF-8).
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = "name,note\nAlice,cafÃ©\nBob,plain\nCarol,plain\nDave,plain\nEve,plain\n"
            p = _write(tmp, "moji.csv", csv_text)
            r, _ = scan_file(p)
            self.assertIn(2, r["encoding_issues"])


class TestNullMismatch(unittest.TestCase):
    def test_two_distinct_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,age,city\n"
                "Alice,30,NYC\n"
                "Bob,N/A,LA\n"
                "Carol,25,NULL\n"
                "Dave,35,DC\n"
                "Eve,45,NYC\n"
                "Frank,50,DC\n"
            )
            p = _write(tmp, "null2.csv", csv_text)
            r, _ = scan_file(p)
            self.assertTrue(len(r["null_mismatch"]) >= 2)
            # First N/A on line 3, first NULL on line 4.
            self.assertIn(3, r["null_mismatch"])
            self.assertIn(4, r["null_mismatch"])

    def test_one_token_plus_empties(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,age,city\n"
                "Alice,30,NYC\n"
                "Bob,,LA\n"          # empty
                "Carol,N/A,SF\n"     # N/A
                "Dave,35,DC\n"
                "Eve,45,NYC\n"
            )
            p = _write(tmp, "null_mix.csv", csv_text)
            r, _ = scan_file(p)
            self.assertTrue(len(r["null_mismatch"]) >= 1)

    def test_only_empty_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,age,city\n"
                "Alice,30,NYC\n"
                "Bob,,LA\n"
                "Carol,,SF\n"
                "Dave,35,DC\n"
                "Eve,,NYC\n"
            )
            p = _write(tmp, "only_empty.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["null_mismatch"], [])


# ---------------------------------------------------------------------------
# End-to-end runner test
# ---------------------------------------------------------------------------


class TestRunnerE2E(unittest.TestCase):
    def test_runner_writes_per_defect_jsons(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            in_dir = tmp / "in"
            in_dir.mkdir()
            out_dir = tmp / "out"

            # File A: comments only
            _write(
                in_dir,
                "a.csv",
                "# leading comment\n"
                "name,age\nAlice,30\nBob,40\nCarol,25\nDave,35\nEve,45\n",
            )
            # File B: null mismatch only
            _write(
                in_dir,
                "b.csv",
                "name,age\nAlice,N/A\nBob,NULL\nCarol,30\nDave,40\nEve,50\n",
            )
            # File C: clean
            _write(
                in_dir,
                "c.csv",
                "name,age\n1,2\n3,4\n5,6\n7,8\n9,10\n",
            )

            args = types.SimpleNamespace(
                in_dir=in_dir,
                out_dir=out_dir,
                jobs=1,
                long_field_chars=DEFAULT_LONG_FIELD_CHARS,
                max_bytes=DEFAULT_MAX_BYTES,
                force=False,
                dataset_prefix="",
            )
            rc = run_scan(args)
            self.assertEqual(rc, 0)

            scan_dir = out_dir / "scan"
            for n in POLLUTION_NAMES:
                self.assertTrue((scan_dir / f"{n}.json").exists())
            self.assertTrue((scan_dir / "summary.json").exists())

            comments = json.loads((scan_dir / "comments.json").read_text())
            self.assertIn("a.csv", comments)
            self.assertEqual(comments["a.csv"], [1])

            nulls = json.loads((scan_dir / "null_mismatch.json").read_text())
            self.assertIn("b.csv", nulls)

            # c.csv should not appear in any defect file
            for n in POLLUTION_NAMES:
                d = json.loads((scan_dir / f"{n}.json").read_text())
                self.assertNotIn("c.csv", d)


class TestRunnerForceGuard(unittest.TestCase):
    """Pin the --force / 'output already populated' branch."""

    def _args(self, in_dir: Path, out_dir: Path, *, force: bool):
        return types.SimpleNamespace(
            in_dir=in_dir,
            out_dir=out_dir,
            jobs=1,
            long_field_chars=DEFAULT_LONG_FIELD_CHARS,
            max_bytes=DEFAULT_MAX_BYTES,
            force=force,
            dataset_prefix="",
        )

    def test_second_run_without_force_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            in_dir = tmp / "in"
            in_dir.mkdir()
            out_dir = tmp / "out"
            _write(in_dir, "a.csv", "name,age\n1,2\n3,4\n5,6\n7,8\n9,10\n")

            # First run populates output.
            self.assertEqual(run_scan(self._args(in_dir, out_dir, force=False)), 0)
            scan_dir = out_dir / "scan"
            sentinel = scan_dir / "comments.json"
            self.assertTrue(sentinel.exists())

            # Stash a stale marker we'd notice if it were overwritten.
            sentinel.write_text('{"STALE": [99]}', encoding="utf-8")
            stale_text = sentinel.read_text()

            # Second run without --force: must early-return without touching files.
            self.assertEqual(run_scan(self._args(in_dir, out_dir, force=False)), 0)
            self.assertEqual(sentinel.read_text(), stale_text)

    def test_second_run_with_force_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            in_dir = tmp / "in"
            in_dir.mkdir()
            out_dir = tmp / "out"
            _write(in_dir, "a.csv", "name,age\n1,2\n3,4\n5,6\n7,8\n9,10\n")

            self.assertEqual(run_scan(self._args(in_dir, out_dir, force=False)), 0)
            sentinel = out_dir / "scan" / "comments.json"
            sentinel.write_text('{"STALE": [99]}', encoding="utf-8")

            # --force=True: must overwrite.
            self.assertEqual(run_scan(self._args(in_dir, out_dir, force=True)), 0)
            self.assertNotIn("STALE", sentinel.read_text())


class TestCompressedInputs(unittest.TestCase):
    """End-to-end through ``io_utils.open_decompressed`` for zstd / gzip."""

    _CSV_TEXT = (
        "# real comment\n"
        "name,age,city\n"
        "Alice,N/A,NYC\n"
        "Bob,NULL,LA\n"
        "Carol,30,SF\n"
        "Dave,40,DC\n"
        "Eve,50,NYC\n"
    )

    def test_zstd_input(self):
        try:
            import zstandard as zstd
        except ImportError:
            self.skipTest("zstandard not installed")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            raw = self._CSV_TEXT.encode("utf-8")
            comp = zstd.ZstdCompressor().compress(raw)
            p = tmp / "data.csv.zstd"
            p.write_bytes(comp)
            r, _ = scan_file(p)
            # The leading comment line is line 1.
            self.assertIn(1, r["comments"])
            # N/A and NULL across rows trigger null-mismatch.
            self.assertTrue(len(r["null_mismatch"]) >= 2)

    def test_gzip_input(self):
        import gzip
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            p = tmp / "data.csv.gz"
            with gzip.open(p, "wb") as f:
                f.write(self._CSV_TEXT.encode("utf-8"))
            r, _ = scan_file(p)
            self.assertIn(1, r["comments"])
            self.assertTrue(len(r["null_mismatch"]) >= 2)


class TestBigFileSampledPath(unittest.TestCase):
    """Force the head/tail-sampled path and verify SAMPLE_GAP_TOKEN is skipped."""

    def test_big_file_sampling(self):
        # SAMPLE_BYTES_THRESHOLD is 5 MB. Build ~7 MB of CSV: header,
        # then a comment line at line 2 (in the head sample), then enough
        # data rows to push over the threshold.
        from survey.config import SAMPLE_BYTES_THRESHOLD
        from survey.detect.parser import SAMPLE_GAP_TOKEN, parse_csv_sample

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            p = tmp / "big.csv"
            row = "1,xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"
            n_rows = (SAMPLE_BYTES_THRESHOLD // len(row)) + 50_000
            with open(p, "w", encoding="utf-8") as f:
                f.write("id,note\n")             # header (line 1)
                f.write("# real comment\n")       # comment (line 2)
                for _ in range(n_rows):
                    f.write(row)
            self.assertGreater(p.stat().st_size, SAMPLE_BYTES_THRESHOLD)

            # Verify the sampled path is actually exercised.
            self.assertTrue(parse_csv_sample(p).sampled)

            r, _ = scan_file(p)
            # Real comment in head sample is flagged.
            self.assertIn(2, r["comments"])
            # The gap-sentinel line itself must NOT be reported as a comment.
            from survey.scan.detectors import _build_raw_lines
            sample = parse_csv_sample(p)
            gap_idx = next(
                (i + 1 for i, ln in enumerate(_build_raw_lines(sample.raw_text))
                 if SAMPLE_GAP_TOKEN in ln),
                None,
            )
            self.assertIsNotNone(gap_idx, "expected gap sentinel in sampled text")
            self.assertNotIn(gap_idx, r["comments"])


class TestUnquotedMultilinePositive(unittest.TestCase):
    """Pin the orphan-fragment heuristic so bug #1 doesn't silently regress."""

    def test_unquoted_newline_in_cell_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "id,name,note\n"
                "1,Alice,short\n"
                "2,Bob,this note has\nan unquoted newline\n"
                "3,Carol,short\n"
                "4,Dave,short\n"
                "5,Eve,short\n"
                "6,Frank,short\n"
            )
            p = _write(tmp, "ml.csv", csv_text)
            r, _ = scan_file(p)
            # The orphan continuation lands on line 4 of the raw text.
            self.assertTrue(len(r["unquoted_multiline"]) >= 1)

    def test_quoted_multiline_does_not_trigger_orphan_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                'id,name,note\n'
                '1,Alice,short\n'
                '2,Bob,"line1\nline2"\n'
                '3,Carol,short\n'
                '4,Dave,short\n'
                '5,Eve,short\n'
                '6,Frank,short\n'
            )
            p = _write(tmp, "quoted.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["unquoted_multiline"], [])


class TestNoDoubleFlag(unittest.TestCase):
    """Header rows reported by header_mismatch must NOT also appear in
    variable_columns. Pins bug #6."""

    def test_header_only_in_header_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # Header has 2 cols, data has 3 cols. Real header_mismatch case.
            csv_text = (
                "name,age\n"
                "Alice,30,NYC\n"
                "Bob,40,LA\n"
                "Carol,25,SF\n"
                "Dave,35,DC\n"
                "Eve,45,NYC\n"
                "Frank,50,DC\n"
            )
            p = _write(tmp, "hdr.csv", csv_text)
            r, _ = scan_file(p)
            self.assertIn(1, r["header_mismatch"])
            self.assertNotIn(1, r["variable_columns"])


class TestTSVNotMixedDelimiter(unittest.TestCase):
    """Tab-delimited file with commas inside cell values must not be
    flagged as mixed_delimiter. Pins bug #2 from the FP angle."""

    def test_tsv_with_embedded_commas_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "id\tnote\tcity\n"
                "1\thello, world\tNYC\n"
                "2\tfoo, bar, baz\tLA\n"
                "3\tplain note\tSF\n"
                "4\tone, two\tDC\n"
                "5\ta, b, c, d\tNYC\n"
                "6\tplain\tDC\n"
            )
            p = _write(tmp, "tsv.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["mixed_delimiter"], [])


class TestUTF16Detection(unittest.TestCase):
    """UTF-16 LE files have NULs that pass strict UTF-8 — we must flag
    them via BOM and via NUL-ratio. Pins bug #3."""

    def test_utf16_le_with_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            text = "name,age\nAlice,30\nBob,40\n"
            content = text.encode("utf-16-le")
            content = b"\xff\xfe" + content  # UTF-16 LE BOM
            p = tmp / "u16.csv"
            p.write_bytes(content)
            r, _ = scan_file(p)
            self.assertIn(1, r["encoding_issues"])

    def test_utf16_le_no_bom_high_nul_ratio(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # UTF-16 LE without BOM. ASCII content => every other byte is NUL.
            text = "name,age\nAlice,30\nBob,40\nCarol,25\nDave,35\n"
            content = text.encode("utf-16-le")
            p = tmp / "u16_noB.csv"
            p.write_bytes(content)
            r, _ = scan_file(p)
            self.assertIn(1, r["encoding_issues"])


class TestDenseRowNotComment(unittest.TestCase):
    """Dense data rows whose first cell coincidentally starts with a
    comment marker must NOT be flagged. Pins bug #4."""

    def test_slash_star_in_dense_data_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "syntax,language,frequency\n"
                "/* comment marker,C,common\n"
                "// inline marker,Java,common\n"
                "# pragma,C,common\n"
                "<? tag,PHP,rare\n"
                "<%,JSP,rare\n"
                "{},JSON,common\n"
            )
            p = _write(tmp, "dense.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["comments"], [])

    def test_two_col_notes_field_not_inline_comment(self):
        # Pins bug #5: two-col file with notes-style data must not get
        # inline-comment-flagged for cells starting with "# ".
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,note\n"
                "apple,# special edition\n"
                "banana,plain\n"
                "carrot,# limited\n"
                "dill,plain\n"
                "egg,# rare\n"
                "fig,plain\n"
            )
            p = _write(tmp, "twocol.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["comments"], [])


class TestRunnerParallel(unittest.TestCase):
    """Exercise the jobs > 1 dispatch path."""

    def test_jobs_2_produces_same_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            in_dir = tmp / "in"
            in_dir.mkdir()
            out_dir = tmp / "out"
            _write(
                in_dir,
                "a.csv",
                "# leading\nname,age\nAlice,30\nBob,40\nCarol,25\nDave,35\nEve,45\n",
            )
            _write(
                in_dir,
                "b.csv",
                "name,age\nAlice,N/A\nBob,NULL\nCarol,30\nDave,40\nEve,50\n",
            )
            args = types.SimpleNamespace(
                in_dir=in_dir,
                out_dir=out_dir,
                jobs=2,
                long_field_chars=DEFAULT_LONG_FIELD_CHARS,
                max_bytes=DEFAULT_MAX_BYTES,
                force=False,
                no_sampling=False,
                dataset_prefix="",
            )
            self.assertEqual(run_scan(args), 0)
            comments = json.loads((out_dir / "scan" / "comments.json").read_text())
            self.assertIn("a.csv", comments)
            nulls = json.loads((out_dir / "scan" / "null_mismatch.json").read_text())
            self.assertIn("b.csv", nulls)


class TestNoSamplingFlag(unittest.TestCase):
    """The --no-sampling flag forces the parser to read the whole file."""

    def test_no_sampling_disables_sampled_flag(self):
        from survey.config import SAMPLE_BYTES_THRESHOLD

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            p = tmp / "big.csv"
            row = "1,xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"
            n_rows = (SAMPLE_BYTES_THRESHOLD // len(row)) + 50_000
            with open(p, "w", encoding="utf-8") as f:
                f.write("id,note\n")
                for _ in range(n_rows):
                    f.write(row)
            self.assertGreater(p.stat().st_size, SAMPLE_BYTES_THRESHOLD)

            _, sampled_default = scan_file(p)
            self.assertTrue(sampled_default)

            _, sampled_off = scan_file(p, no_sampling=True)
            self.assertFalse(sampled_off)


# ---------------------------------------------------------------------------
# Regression tests for the second-round fixes.
# ---------------------------------------------------------------------------


class TestJaggedRowNotUnquotedMultiline(unittest.TestCase):
    """A merely-jagged data row (one trailing column missing) parses as ≥2
    cells and must NOT trigger the orphan-fragment heuristic. Only true
    1-cell suffixes — the structural signature of an unquoted-newline split
    — should fire."""

    def test_two_cell_jagged_row_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "name,age,role\n"
                "Alice,30,eng\n"
                "Bob,40\n"  # jagged: 2 cells in a 3-col modal file
                "Carol,25,intern\n"
                "Dave,35,sci\n"
                "Eve,45,sci\n"
                "Frank,50,sci\n"
            )
            p = _write(tmp, "jagged.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["unquoted_multiline"], [])
            # variable_columns is the right detector for this shape.
            self.assertIn(3, r["variable_columns"])


class TestPreambleProseComment(unittest.TestCase):
    """Prose comment lines containing commas land in the preamble (before
    the detected header) — they parse as multiple cells but are still real
    comments. Pre-header leniency in detect_comments handles this."""

    def test_prose_comment_with_commas_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "# Source: Smith et al. 2004, Cambridge MA, USA\n"
                "# Field definitions follow,,,\n"
                "name,age,city\n"
                "Alice,30,NYC\n"
                "Bob,40,LA\n"
                "Carol,25,SF\n"
                "Dave,35,DC\n"
                "Eve,45,NYC\n"
            )
            p = _write(tmp, "prose.csv", csv_text)
            r, _ = scan_file(p)
            self.assertIn(1, r["comments"])
            self.assertIn(2, r["comments"])

    def test_dense_post_header_row_still_not_flagged(self):
        # The pre-header leniency must NOT extend past the header.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                "syntax,language,frequency\n"
                "/* comment marker,C,common\n"
                "// inline marker,Java,common\n"
                "# pragma,C,common\n"
                "<? tag,PHP,rare\n"
                "<%,JSP,rare\n"
                "{},JSON,common\n"
            )
            p = _write(tmp, "dense.csv", csv_text)
            r, _ = scan_file(p)
            self.assertEqual(r["comments"], [])


class TestMixedQuotedAndUnquotedMultiline(unittest.TestCase):
    """Files containing a legitimate quoted multiline cell AND an
    unquoted-newline split must still flag the unquoted split — the two
    signals are independent."""

    def test_quoted_does_not_disable_orphan_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_text = (
                'a,b,c\n'
                '1,Alice,"properly\nquoted"\n'
                '2,Bob,split here\nthis is orphan\n'
                '3,Carol,3\n'
                '4,Dave,4\n'
                '5,Eve,5\n'
                '6,Frank,6\n'
            )
            p = _write(tmp, "mixed.csv", csv_text)
            r, _ = scan_file(p)
            self.assertTrue(len(r["unquoted_multiline"]) >= 1)


class TestForceNoSamplingParameter(unittest.TestCase):
    """``parse_csv_sample(force_no_sampling=True)`` is the clean parameter
    path that replaced the previous module-attribute monkey-patch."""

    def test_force_no_sampling_kwarg(self):
        from survey.config import SAMPLE_BYTES_THRESHOLD
        from survey.detect.parser import parse_csv_sample

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            p = tmp / "big.csv"
            row = "1,xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"
            n_rows = (SAMPLE_BYTES_THRESHOLD // len(row)) + 50_000
            with open(p, "w", encoding="utf-8") as f:
                f.write("id,note\n")
                for _ in range(n_rows):
                    f.write(row)

            self.assertTrue(parse_csv_sample(p).sampled)
            self.assertFalse(parse_csv_sample(p, force_no_sampling=True).sampled)


class TestScanContextMemoization(unittest.TestCase):
    """row_starts() and header_indices() should compute once per ScanContext."""

    def test_memoization_caches_results(self):
        from survey.scan.detectors import (
            ScanContext,
            _build_raw_lines,
            header_indices,
            row_starts,
        )
        from survey.detect.parser import parse_csv_sample

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            p = _write(
                tmp,
                "m.csv",
                "name,age\nAlice,30\nBob,40\nCarol,25\nDave,35\nEve,45\n",
            )
            sample = parse_csv_sample(p)
            ctx = ScanContext(
                sample=sample,
                raw_lines=_build_raw_lines(sample.raw_text),
                raw_text=sample.raw_text,
                raw_bytes=p.read_bytes(),
                long_field_chars=DEFAULT_LONG_FIELD_CHARS,
            )
            self.assertIsNone(ctx._row_starts)
            self.assertIsNone(ctx._header_indices)
            r1 = row_starts(ctx)
            self.assertIs(row_starts(ctx), r1)  # same object on second call
            h1 = header_indices(ctx)
            self.assertIs(header_indices(ctx), h1)


if __name__ == "__main__":
    unittest.main()
