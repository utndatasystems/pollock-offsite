import pandas as pd
import duckdb
import subprocess
import tempfile
import os
import re
import json


def call_llm(prompt: str) -> str:
    """Call kiro-cli chat in non-interactive mode. Returns '' on failure/timeout."""
    try:
        result = subprocess.run(
            ["kiro-cli", "chat", "--no-interactive", "--trust-tools=", "--wrap", "never",
             "--model", "claude-opus-4.8"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return ""
    output = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout).strip()
    if output.startswith("> "):
        output = output[2:]
    return output


def detect_dialect(content: str) -> dict:
    """Use LLM to detect CSV dialect."""
    lines = content.split('\n')
    sample = '\n'.join(lines[:35])

    prompt = f"""You are a CSV dialect detector. Analyze this CSV file and output ONLY a valid JSON object (no markdown, no explanation) with these keys:
"delimiter": the exact field separator string (e.g. "," or "\\t" or ", " or " " or ";")
"quotechar": the quoting character (e.g. "\\"" or "'")
"escapechar": the escape character used inside quotes (e.g. "\\"" or "\\\\" or "" for none/null)
"header_lines": integer - how many rows form the header (0=no header, 1=normal, 2+=multi-row where column names are joined with space)
"preamble_lines": integer - lines to skip before header (usually 0)
"n_columns": integer - number of columns
"column_names": array of strings - the column names (if multi-row header, join values with space)

CSV file:
{sample}"""

    response = call_llm(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    for match in re.finditer(r'\{.*\}', response, re.DOTALL):
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            continue
    return {}


def make_kw(dialect: dict) -> dict:
    """Build DuckDB read_csv kwargs."""
    n_cols = int(dialect['n_columns'])
    col_names = dialect.get('column_names', [])
    delimiter = dialect['delimiter']
    quotechar = dialect['quotechar']
    escapechar = dialect.get('escapechar', '"')
    header_lines = int(dialect['header_lines'])
    preamble_lines = int(dialect['preamble_lines'])

    if delimiter == '\\t':
        delimiter = '\t'
    if escapechar in ('', '\\0'):
        escapechar = '\x00'

    kw = {
        'delimiter': delimiter,
        'quotechar': quotechar,
        'escapechar': escapechar,
        'skiprows': preamble_lines + header_lines,
        'header': False,
        'auto_detect': False,
        'null_padding': True,
        'ignore_errors': True,
    }
    if col_names and len(col_names) == n_cols:
        kw['columns'] = {name: 'VARCHAR' for name in col_names}
    elif n_cols > 0:
        kw['columns'] = {f'col_{i}': 'VARCHAR' for i in range(n_cols)}
    return kw


def try_parse(filepath: str, dialect: dict) -> tuple:
    """Parse file with DuckDB, return (df, expected_rows)."""
    content_lines = open(filepath, 'r', encoding='ascii', errors='replace').read().split('\n')
    skip = int(dialect.get('preamble_lines', 0)) + int(dialect.get('header_lines', 1))
    expected = sum(1 for l in content_lines[skip:] if l.strip())

    kw = make_kw(dialect)
    con = duckdb.connect()
    df = con.read_csv(filepath, **kw).df()
    return df, expected


def find_broken_line_nums(filepath: str, content: str, dialect: dict) -> list:
    """Find broken lines by testing suspicious ones with DuckDB."""
    n_cols = int(dialect['n_columns'])
    delimiter = dialect['delimiter']
    quotechar = dialect['quotechar']
    escapechar = dialect.get('escapechar', '"')
    skip = int(dialect.get('preamble_lines', 0)) + int(dialect.get('header_lines', 1))

    if delimiter == '\\t':
        delimiter = '\t'
    if escapechar in ('', '\\0'):
        escapechar = '\x00'

    lines = content.split('\n')
    data_lines = [l for l in lines[skip:] if l.strip()]

    def has_stray_quote(line: str) -> bool:
        """A quotechar with non-delimiter, non-quote chars on both sides is a stray quote."""
        if not quotechar or len(quotechar) != 1:
            return False
        for p in range(len(line)):
            if line[p] != quotechar:
                continue
            before = line[p-1] if p > 0 else delimiter[0]
            after = line[p+1] if p + 1 < len(line) else delimiter[0]
            # Skip doubled quotes (escape)
            if before == quotechar or after == quotechar:
                continue
            # Stray if both neighbors are not the delimiter
            if before != delimiter[0] and after != delimiter[0]:
                return True
        return False

    # Strong signal: lines with a mid-field stray quote are always broken.
    # But if >30% of lines have "stray quotes", the quotechar collides with data
    # content (e.g. apostrophes when quotechar="'"), so the signal is unreliable.
    strong = set(i for i, line in enumerate(data_lines) if has_stray_quote(line))
    if len(strong) > len(data_lines) * 0.3:
        strong = set()

    # Weak signal: lines deviating from the majority delimiter count (need DuckDB confirmation)
    from collections import Counter
    weak = set()
    delim_counts = [line.count(delimiter) for line in data_lines]
    if delim_counts:
        most_common = Counter(delim_counts).most_common(1)[0][0]
        candidates = set(i for i, c in enumerate(delim_counts) if c != most_common) - strong
        if len(candidates) <= len(data_lines) * 0.3:
            weak = candidates

    if not strong and not weak:
        return []

    broken = set(i + 1 for i in strong)

    # Confirm weak signals with DuckDB single-line test
    for i in sorted(weak):
        line = data_lines[i]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp.write(line)
            tmp_path = tmp.name
        try:
            con = duckdb.connect()
            df = con.read_csv(tmp_path, delimiter=delimiter, quotechar=quotechar,
                            escapechar=escapechar, skiprows=0, header=False,
                            auto_detect=False, null_padding=True,
                            columns={f'c{j}': 'VARCHAR' for j in range(n_cols)}).df()
            if len(df) != 1 or df.iloc[0, :-1].isnull().any():
                broken.add(i + 1)
        except:
            broken.add(i + 1)
        finally:
            os.unlink(tmp_path)

    return sorted(broken)


def fix_lines_llm(broken_lines: list, good_line: str, dialect: dict) -> dict:
    """Ask LLM to parse broken CSV lines into correct field values."""
    n_cols = int(dialect['n_columns'])
    col_names = dialect.get('column_names', [])
    delimiter = dialect['delimiter']
    quotechar = dialect['quotechar']
    col_header = ', '.join(col_names) if col_names else f'{n_cols} columns'

    broken_text = '\n'.join([f"LINE {ln}: {text}" for ln, text in broken_lines])

    prompt = f"""Parse these broken CSV lines into exactly {n_cols} fields each.
File uses: delimiter={repr(delimiter)}, quotechar={repr(quotechar)}, {n_cols} columns: {col_header}

REFERENCE (a correct line from the same file):
{good_line}

RULES:
- Missing delimiter between two fields: split them (e.g. "11:1512" → "11:15" and "12")
- Extra delimiter splitting one field: merge the parts back
- Stray/extra quote not properly opening/closing a field: it becomes LITERAL text in that field value (preserve it)
- Row using a different delimiter (e.g. space instead of comma): re-parse with that delimiter
- Empty fields = empty string

OUTPUT FORMAT (exactly one line per broken input, nothing else):
LINE <number>: field1 | field2 | ... | fieldN
(exactly {n_cols} fields separated by " | ", no quotes around values)

{broken_text}"""

    response = call_llm(prompt)

    result = {}
    for line in response.split('\n'):
        line = line.strip()
        if (line.startswith('"') and line.endswith('"')) or (line.startswith("'") and line.endswith("'")):
            line = line[1:-1]
        m = re.match(r'LINE\s*(\d+)\s*:\s*(.*)', line)
        if m:
            ln = int(m.group(1))
            fields_str = m.group(2)
            fields = fields_str.split(' | ')
            # Handle trailing pipe indicating empty last field
            if fields and fields[-1].rstrip().endswith('|'):
                fields[-1] = fields[-1].rstrip()[:-1].rstrip()
                fields.append('')
            if len(fields) == n_cols:
                result[ln] = [f.strip() for f in fields]
            elif len(fields) == n_cols + 1 and fields[-1].strip() == '':
                result[ln] = [f.strip() for f in fields[:n_cols]]
            elif len(fields) == n_cols - 1:
                result[ln] = [f.strip() for f in fields] + ['']

    # Fallback for single line without LINE prefix
    if not result and len(broken_lines) == 1:
        for line in response.split('\n'):
            line = line.strip()
            if (line.startswith('"') and line.endswith('"')) or (line.startswith("'") and line.endswith("'")):
                line = line[1:-1]
            if not line or line.startswith('```'):
                continue
            m = re.match(r'LINE\s*\d+\s*:\s*(.*)', line)
            s = m.group(1) if m else line
            fields = s.split(' | ')
            if fields and fields[-1].rstrip().endswith('|'):
                fields[-1] = fields[-1].rstrip()[:-1].rstrip()
                fields.append('')
            if len(fields) == n_cols:
                result[broken_lines[0][0]] = [f.strip() for f in fields]
                break
            elif len(fields) == n_cols + 1 and fields[-1].strip() == '':
                result[broken_lines[0][0]] = [f.strip() for f in fields[:n_cols]]
                break
            elif len(fields) == n_cols - 1:
                result[broken_lines[0][0]] = [f.strip() for f in fields] + ['']
                break

    return result


def parse_csv(csv_path: str) -> pd.DataFrame:
    """Parse CSV: LLM dialect → DuckDB parse → detect errors → LLM fix → DuckDB re-parse."""
    with open(csv_path, 'r', encoding='ascii', errors='replace') as f:
        content = f.read()

    if not content.strip():
        return pd.DataFrame()

    # Step 1: Detect dialect via LLM
    dialect = detect_dialect(content)
    if not dialect.get('n_columns'):
        # LLM failed to detect - fallback to DuckDB auto
        con = duckdb.connect()
        return con.read_csv(csv_path, auto_detect=True, all_varchar=True).df()

    # Step 2: Parse with DuckDB (permissive)
    df, expected_rows = try_parse(csv_path, dialect)

    # Step 2b: Try null escape as alternative (handles files where escapechar detection is wrong)
    if dialect.get('escapechar', '"') not in ('', '\x00', '\\0'):
        dialect_alt = dict(dialect)
        dialect_alt['escapechar'] = ''
        df_alt, _ = try_parse(csv_path, dialect_alt)
        if len(df_alt) > len(df):
            df = df_alt
            dialect = dialect_alt
        elif len(df_alt) == len(df) == expected_rows:
            nulls_orig = df.isnull().sum().sum()
            nulls_alt = df_alt.isnull().sum().sum()
            if nulls_alt < nulls_orig:
                df = df_alt
                dialect = dialect_alt

    # Step 2c: If DuckDB completely fails (<50% rows), use Python csv module fallback
    if len(df) < expected_rows * 0.5:
        import csv as csv_mod
        import io
        delimiter = dialect['delimiter']
        quotechar = dialect['quotechar']
        if delimiter == '\\t':
            delimiter = '\t'
        skip = int(dialect['preamble_lines']) + int(dialect['header_lines'])
        lines = content.split('\n')
        data_lines = [l for l in lines[skip:] if l.strip()]
        n_cols = int(dialect['n_columns'])
        col_names = dialect.get('column_names', [])

        # Try both doublequote modes, pick the one with more correct rows
        best_rows = None
        best_good = -1
        best_broken = []
        best_dq = True
        for dq in [True, False]:
            rows = []
            good = 0
            broken = []
            for i, line in enumerate(data_lines):
                try:
                    reader = csv_mod.reader(io.StringIO(line), delimiter=delimiter,
                                           quotechar=quotechar, doublequote=dq)
                    fields = next(reader)
                    if len(fields) == n_cols:
                        good += 1
                        rows.append(fields)
                    else:
                        rows.append(None)
                        broken.append((i + 1, line))
                except:
                    rows.append(None)
                    broken.append((i + 1, line))
            if good > best_good:
                best_good = good
                best_rows = rows
                best_broken = broken
                best_dq = dq

        # Validate "good" rows with DuckDB single-line test (catch silent misparses).
        # Collect DuckDB-flagged lines separately; if too many, DuckDB's quotechar
        # interpretation collides with data (e.g. apostrophes), so ignore its verdict.
        escapechar_actual = dialect.get('escapechar', '"')
        if escapechar_actual in ('', '\\0'):
            escapechar_actual = '\x00'
        duckdb_flagged = []
        for i, line in enumerate(data_lines):
            if best_rows[i] is None:
                continue
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
                tmp.write(line)
                tmp_path = tmp.name
            try:
                con = duckdb.connect()
                tdf = con.read_csv(tmp_path, delimiter=delimiter, quotechar=quotechar,
                           escapechar=escapechar_actual, skiprows=0, header=False,
                           auto_detect=False, null_padding=True,
                           columns={f'c{j}': 'VARCHAR' for j in range(n_cols)}).df()
                if len(tdf) != 1 or tdf.iloc[0, :-1].isnull().any():
                    duckdb_flagged.append(i)
            except:
                duckdb_flagged.append(i)
            finally:
                os.unlink(tmp_path)

        if len(duckdb_flagged) <= len(data_lines) * 0.3:
            for i in duckdb_flagged:
                best_rows[i] = None
                best_broken.append((i + 1, data_lines[i]))

        # Fix broken rows via LLM
        if best_broken:
            good_line = next((data_lines[i] for i in range(len(data_lines))
                            if best_rows[i] is not None), None)
            if good_line:
                fixed = fix_lines_llm(best_broken, good_line, dialect)
                for ln, fields in fixed.items():
                    idx = ln - 1
                    if 0 <= idx < len(best_rows):
                        best_rows[idx] = fields

        for i in range(len(best_rows)):
            if best_rows[i] is None:
                best_rows[i] = [''] * n_cols

        cols = col_names if len(col_names) == n_cols else [f'col_{i}' for i in range(n_cols)]
        return pd.DataFrame(best_rows, columns=cols)

    # Step 3: Check for subtle errors (DuckDB got right row count but may have misparsed)
    if len(df) == expected_rows:
        # Parse without null_padding - if rows get dropped, they were broken
        kw_strict = make_kw(dialect)
        kw_strict['null_padding'] = False
        con_s = duckdb.connect()
        df_strict = con_s.read_csv(csv_path, **kw_strict).df()
        if len(df_strict) == expected_rows:
            # Also check heuristic for stray quotes etc.
            broken_nums = find_broken_line_nums(csv_path, content, dialect)
            if not broken_nums:
                return df
        else:
            # Rows were dropped - test ALL lines individually to find which ones
            n_cols = int(dialect['n_columns'])
            delimiter = dialect['delimiter']
            quotechar = dialect['quotechar']
            escapechar = dialect.get('escapechar', '"')
            if delimiter == '\\t':
                delimiter = '\t'
            if escapechar in ('', '\\0'):
                escapechar = '\x00'
            skip = int(dialect['preamble_lines']) + int(dialect['header_lines'])
            lines = content.split('\n')
            data_lines = [l for l in lines[skip:] if l.strip()]
            broken_nums = []
            for i, line in enumerate(data_lines):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
                    tmp.write(line)
                    tmp_path = tmp.name
                try:
                    con = duckdb.connect()
                    tdf = con.read_csv(tmp_path, delimiter=delimiter, quotechar=quotechar,
                                    escapechar=escapechar, skiprows=0, header=False,
                                    auto_detect=False, null_padding=True,
                                    columns={f'c{j}': 'VARCHAR' for j in range(n_cols)}).df()
                    # Broken if: no rows, or NULLs in non-last columns (last col NULL = trailing delimiter, normal)
                    if len(tdf) != 1 or tdf.iloc[0, :-1].isnull().any():
                        broken_nums.append(i + 1)
                except:
                    broken_nums.append(i + 1)
                finally:
                    os.unlink(tmp_path)
    else:
        broken_nums = find_broken_line_nums(csv_path, content, dialect)

    if not broken_nums:
        return df

    # Step 4: Get broken line content and fix via LLM
    lines = content.split('\n')
    skip = int(dialect['preamble_lines']) + int(dialect['header_lines'])
    data_lines = [l for l in lines[skip:] if l.strip()]
    n_cols = int(dialect['n_columns'])

    broken_lines = [(ln, data_lines[ln - 1]) for ln in broken_nums if ln - 1 < len(data_lines)]
    good_line = next((data_lines[i] for i in range(len(data_lines)) if (i + 1) not in set(broken_nums)), None)

    if not broken_lines or not good_line:
        return df

    fixed = fix_lines_llm(broken_lines, good_line, dialect)

    # Step 5: Replace broken lines and re-parse with DuckDB
    delimiter_actual = dialect['delimiter']
    if delimiter_actual == '\\t':
        delimiter_actual = '\t'
    quotechar_actual = dialect['quotechar']
    escapechar_actual = dialect.get('escapechar', '"')
    if escapechar_actual in ('', '\\0'):
        escapechar_actual = '\x00'

    fixed_data_lines = list(data_lines)
    for ln, fields in fixed.items():
        idx = ln - 1
        if 0 <= idx < len(fixed_data_lines):
            parts = []
            for field in fields:
                needs_quote = (delimiter_actual in field or
                             quotechar_actual in field or
                             '\n' in field or '\r' in field)
                if needs_quote:
                    if escapechar_actual == quotechar_actual:
                        escaped = field.replace(quotechar_actual, quotechar_actual + quotechar_actual)
                    elif escapechar_actual == '\x00':
                        escaped = field
                    else:
                        escaped = field.replace(quotechar_actual, escapechar_actual + quotechar_actual)
                    parts.append(f'{quotechar_actual}{escaped}{quotechar_actual}')
                else:
                    parts.append(field)
            fixed_data_lines[idx] = delimiter_actual.join(parts)

    header_content = '\n'.join(lines[:skip])
    new_content = (header_content + '\n' if header_content else '') + '\n'.join(fixed_data_lines)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write(new_content)
        tmp_path = tmp.name

    try:
        kw = make_kw(dialect)
        con = duckdb.connect()
        return con.read_csv(tmp_path, **kw).df()
    finally:
        os.unlink(tmp_path)
