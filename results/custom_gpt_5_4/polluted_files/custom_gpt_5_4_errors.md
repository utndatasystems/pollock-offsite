# custom_gpt_5_4 — polluted_files

| | |
|---|---|
| Results file | `results/custom_gpt_5_4/polluted_files/custom_gpt_5_4_results.csv` |
| Total files evaluated | 2289 |
| Application errors | 0 |
| Wrong content | 744 |
| Malformed sidecars | 2289 / 2289 |


## Custom Malformed-Row Detection

*Scope: wrong-content files only*

| Metric | Value |
|--------|-------|
| Sidecar reports found | 744 / 744 |
| Files with detected malformed rows | 688 / 744 (92.5%) |
| Total malformed rows logged | 2496 |

### Detection by Pollution Type

| Det | Total | % | Type | Rows logged |
|----:|------:|--:|------|------------:|
| 597 | 603 | 99.0% | Extra unescaped quote | 925 |
| 67 | 68 | 98.5% | Extra delimiter | 477 |
| 15 | 63 | 23.8% | Missing delimiter | 670 |
| 3 | 3 | 100.0% | Row uses space as field delimiter | 85 |
| 0 | 1 | 0.0% | Empty file (0 bytes) |  |
| 1 | 1 | 100.0% | No header row | 83 |
| 1 | 1 | 100.0% | Non-standard escape character (0x5C) | 6 |
| 1 | 1 | 100.0% | Non-standard field delimiter (0x20) | 83 |
| 1 | 1 | 100.0% | Two tables with the same number of columns | 1 |
| 1 | 1 | 100.0% | Two tables, first has fewer columns | 83 |
| 1 | 1 | 100.0% | Two tables, first has more columns | 83 |

### Malformed Row Reasons

| N | Reason |
|--:|--------|
| 1112 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 415 | `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9` |
| 146 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10` |
| 126 | `UNQUOTED VALUE: Value with unterminated quote found.` |
| 87 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 8` |
| 83 | `TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 5; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 6; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 7; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 8; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 9` |
| 81 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.` |
| 73 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.` |
| 69 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.` |
| 64 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.` |
| 45 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; UNQUOTED VALUE: Value with unterminated quote found.` |
| 39 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 13; UNQUOTED VALUE: Value with unterminated quote found.` |
| 30 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 4; MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.` |
| 27 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12; UNQUOTED VALUE: Value with unterminated quote found.` |
| 24 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; UNQUOTED VALUE: Value with unterminated quote found.` |
| 22 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 18 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 12 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 13; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 14; UNQUOTED VALUE: Value with unterminated quote found.` |
| 10 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 3; MISSING COLUMNS: Expected Number of Columns: 9 Found: 4; MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.` |
| 7 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 2 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 13; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 14; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 15; UNQUOTED VALUE: Value with unterminated quote found.` |
| 2 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 13; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 14; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 1 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8` |
| 1 | `MISSING COLUMNS: Expected Number of Columns: 9 Found: 2; MISSING COLUMNS: Expected Number of Columns: 9 Found: 3; MISSING COLUMNS: Expected Number of Columns: 9 Found: 4; MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8` |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 744 files

| N | Type |
|--:|------|
| 603 | Extra unescaped quote |
| 68 | Extra delimiter |
| 63 | Missing delimiter |
| 3 | Row uses space as field delimiter |
| 1 | Empty file (0 bytes) |
| 1 | No header row |
| 1 | Non-standard escape character (0x5C) |
| 1 | Non-standard field delimiter (0x20) |
| 1 | Two tables with the same number of columns |
| 1 | Two tables, first has fewer columns |
| 1 | Two tables, first has more columns |


### Extra unescaped quote — 603 files

*Variants: rows 0-83 (84 unique); columns 0-8 (9 unique)*

*Showing 15 example file(s); 588 more under this type.*


#### `row_extra_quote0_col0.csv`

- **Pollution:** Extra unescaped quote in row 0, column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


**Header mismatch**

- **Expected:** `['"DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote0_col1.csv`

- **Pollution:** Extra unescaped quote in row 0, column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


**Header mismatch**

- **Expected:** `['DATE', '"TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote0_col2.csv`

- **Pollution:** Extra unescaped quote in row 0, column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', '"Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty,PRODUCTID,Price,ProductType,ProductDescription', 'URL', 'Comments', '', '', '']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote0_col3.csv`

- **Pollution:** Extra unescaped quote in row 0, column 3
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', '"PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType ProductDescription', 'URL', 'Comments']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote0_col4.csv`

- **Pollution:** Extra unescaped quote in row 0, column 4
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', '"Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price,ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote0_col5.csv`

- **Pollution:** Extra unescaped quote in row 0, column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', '"ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType,"ProductDescription', 'URL', 'Comments']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote0_col6.csv`

- **Pollution:** Extra unescaped quote in row 0, column 6
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', '"ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', '"ProductDescription"', 'URL', 'Comments']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote0_col7.csv`

- **Pollution:** Extra unescaped quote in row 0, column 7
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', '"URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote0_col8.csv`

- **Pollution:** Extra unescaped quote in row 0, column 8
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', '"Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_extra_quote1_col0.csv`

- **Pollution:** Extra unescaped quote in row 1, column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 3; MISSING COLUMNS: Expected Number of Columns: 9 Found: 4; MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: "28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    """28/01/2018",00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged ...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: """28/01/2018",00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are 
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: www.example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html,
  ```


#### `row_extra_quote1_col1.csv`

- **Pollution:** Extra unescaped quote in row 1, column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 4; MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 28/01/2018,"00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,"""00:00",2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged ...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,"""00:00",2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are 
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: www.example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html,
  ```


#### `row_extra_quote1_col2.csv`

- **Pollution:** Extra unescaped quote in row 1, column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 28/01/2018,00:00,"2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,"""2",MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged ...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,"""2",MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are 
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: www.example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html,
  ```


#### `row_extra_quote1_col3.csv`

- **Pollution:** Extra unescaped quote in row 1, column 3
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 28/01/2018,00:00,2,"MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,2,"""MG-8769",$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged ...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,"""MG-8769",$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are 
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: www.example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html,
  ```


#### `row_extra_quote1_col5.csv`

- **Pollution:** Extra unescaped quote in row 1, column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 8; UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,"Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,"""Men's Waterproof Hiking Boots",These waterproof hiking boots for men are rugged ...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,"""Men's Waterproof Hiking Boots",These waterproof hiking boots for men are 
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: www.example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html,
  ```


#### `row_extra_quote1_col7.csv`

- **Pollution:** Extra unescaped quote in row 1, column 7
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,"""https://w
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: ww.example.com/product/MG_8769.html",
  Got ctd.: example.com/product/MG_8769.html,
  ```


### Extra delimiter — 68 files

*Variants: rows 0-10, 12, 22, 33, 35, 39, 41, 47, 49, 53-56, 80-81, 83 (26 unique); columns 0-8 (9 unique)*

*Showing 15 example file(s); 53 more under this type.*


#### `row_more_sep_row0_col1.csv`

- **Pollution:** Extra delimiter in row 0 at column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', '', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL']`

*Rows loaded: 83*


#### `row_more_sep_row0_col4.csv`

- **Pollution:** Extra delimiter in row 0 at column 4
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', '', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 10 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html,
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,,Light-Up Running Jacket,"The next level of weather protection. This light-u
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: p jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking t
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: he dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/p
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: roduct/RI_3895.html,
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.:  these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```

  ```
  Exp. ctd: 
  Got ctd.: ,
  ```


*… and 80 more*

#### `row_more_sep_row0_col5.csv`

- **Pollution:** Extra delimiter in row 0 at column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', '', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 10 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html,
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,,Light-Up Running Jacket,"The next level of weather protection. This light-u
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: p jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking t
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: he dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/p
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: roduct/RI_3895.html,
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.:  these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```

  ```
  Exp. ctd: 
  Got ctd.: ,
  ```


*… and 80 more*

#### `row_more_sep_row0_col6.csv`

- **Pollution:** Extra delimiter in row 0 at column 6
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', '', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 10 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html,
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,,"The next level of weather protection. This light-u
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: p jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking t
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: he dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/p
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: roduct/RI_3895.html,
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,,"Great grip and super extra breathability make
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.:  these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```

  ```
  Exp. ctd: 
  Got ctd.: ,
  ```


*… and 80 more*

#### `row_more_sep_row0_col7.csv`

- **Pollution:** Extra delimiter in row 0 at column 7
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', '', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 10 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html,
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",,https://www.example.com/p
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: roduct/RI_3895.html,
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",,https://www.example.com/product/RI_8070.html
  ```

  ```
  Exp. ctd: 
  Got ctd.: ,
  ```


*… and 80 more*

#### `row_more_sep_row0_col8.csv`

- **Pollution:** Extra delimiter in row 0 at column 8
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `MISSING COLUMNS: Expected Number of Columns: 10 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', '', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 10 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html,,
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html,,
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  ```

  ```
  Exp. ctd: 
  Got ctd.: ,
  ```


*… and 80 more*

#### `row_more_sep_row1_col0.csv`

- **Pollution:** Extra delimiter in row 1 at column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: ,28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      ,28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html
  ```


#### `row_more_sep_row1_col1.csv`

- **Pollution:** Extra delimiter in row 1 at column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 28/01/2018,,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html
  ```


#### `row_more_sep_row1_col2.csv`

- **Pollution:** Extra delimiter in row 1 at column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 28/01/2018,00:00,,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html
  ```


#### `row_more_sep_row1_col3.csv`

- **Pollution:** Extra delimiter in row 1 at column 3
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 28/01/2018,00:00,2,,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,"https://ww
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: w.example.com/product/MG_8769.html,"
  ```


#### `row_more_sep_row1_col5.csv`

- **Pollution:** Extra delimiter in row 1 at column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html
  ```


#### `row_more_sep_row1_col6.csv`

- **Pollution:** Extra delimiter in row 1 at column 6
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,,"These waterproof hiking boots for men are rugged en...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html
  ```


#### `row_more_sep_row1_col7.csv`

- **Pollution:** Extra delimiter in row 1 at column 7
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html
  ```


#### `row_more_sep_row2_col0.csv`

- **Pollution:** Extra delimiter in row 2 at column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: ,29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacke...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      ,29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-u
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: p jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking t
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: he dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/p
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: roduct/RI_3895.html
  ```


#### `row_more_sep_row2_col2.csv`

- **Pollution:** Extra delimiter in row 2 at column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 29/01/2018,00:15,,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacke...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-u
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: p jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking t
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: he dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/p
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: roduct/RI_3895.html
  ```


### Missing delimiter — 63 files

*Variants: rows 0-3, 5-10, 12-14, 16-22, 26, 28, 30, 32-33, 37-40, 45-47, 49-50, 53-55, 57-58, 60-62, 64-65, 69, 71-72, 76-77, 80, 83 (51 unique); columns 1-8 (8 unique)*

*Showing 15 example file(s); 48 more under this type.*


#### `row_less_sep_row0_col1.csv`

- **Pollution:** Missing delimiter in row 0 at column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATETIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

#### `row_less_sep_row0_col2.csv`

- **Pollution:** Missing delimiter in row 0 at column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIMEQty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

#### `row_less_sep_row0_col3.csv`

- **Pollution:** Missing delimiter in row 0 at column 3
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'QtyPRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

#### `row_less_sep_row0_col4.csv`

- **Pollution:** Missing delimiter in row 0 at column 4
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTIDPrice', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

#### `row_less_sep_row0_col5.csv`

- **Pollution:** Missing delimiter in row 0 at column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'PriceProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

#### `row_less_sep_row0_col6.csv`

- **Pollution:** Missing delimiter in row 0 at column 6
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType"ProductDescription"', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

#### `row_less_sep_row0_col7.csv`

- **Pollution:** Missing delimiter in row 0 at column 7
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription"URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

#### `row_less_sep_row0_col8.csv`

- **Pollution:** Missing delimiter in row 0 at column 8
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


*Rows loaded: 0 (expected 83)*

**Diff:** 83 expected-but-missing, 0 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      (absent)
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: 
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      (absent)
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: 
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      (absent)
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

#### `row_less_sep_row1_col3.csv`

- **Pollution:** Missing delimiter in row 1 at column 3
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 82**

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```

- **line 5:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can ...
  Clean:    31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,This lightweight fly rod delivers outstanding performance and can b...
  ```


*… and 79 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugge
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: d enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.e
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: xample.com/product/MG_8769.html,
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

#### `row_less_sep_row2_col6.csv`

- **Pollution:** Missing delimiter in row 2 at column 6
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket"The next level of weather protection. This light-up jacket ...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,"Light-Up Running Jacket""The next level of weather protection. This light-u
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: p jacket resists the elements and keeps you visible in low-light conditions. From running", biking or walking 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: the dog," the durable construction and innovative safety features won't let you down.""",https://www.example.c
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: om/product/RI_3895.html
  ```


#### `row_less_sep_row3_col6.csv`

- **Pollution:** Missing delimiter in row 3 at column 6
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,"Men's Ventilated Trail Shoes""Great grip and super extra breathability make
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.:  these amazing ventilated hikers ideal for warm"," dry conditions.""",https://www.example.com/product/RI_8070.
  ```

  ```
  Exp. ctd: 
  Got ctd.: html,
  ```


#### `row_less_sep_row5_col5.csv`

- **Pollution:** Missing delimiter in row 5 at column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 13/02/2018,01:00,9,CC-9259,$48.00,"Throw Pillow, Wooden Paddles","Add a pop of paddling fun to your bed, chair
  Got:      13/02/2018,01:00,9,CC-9259,"$48.00""Throw Pillow"," Wooden Paddles""","Add a pop of paddling fun to your bed, 
  ```

  ```
  Exp. ctd:  or sofa with this whimsical throw pillow, handhooked on front for a timeless style.",https://www.example.com/
  Got ctd.: chair or sofa with this whimsical throw pillow, handhooked on front for a timeless style.",https://www.example
  ```

  ```
  Exp. ctd: product/CC_9259.html,
  Got ctd.: .com/product/CC_9259.html,
  ```


#### `row_less_sep_row6_col6.csv`

- **Pollution:** Missing delimiter in row 6 at column 6
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 14/02/2018,01:15,1,CC-1697,$34.22,Men's Heavy-Duty Suspenders,"These tough Men's Heavy-Duty Suspenders are mad
  Got:      14/02/2018,01:15,1,CC-1697,$34.22,"Men's Heavy-Duty Suspenders""These tough Men's Heavy-Duty Suspenders are ma
  ```

  ```
  Exp. ctd: e to hold up heavy wool pants without stretching in any way, shape or form.",https://www.example.com/product/C
  Got ctd.: de to hold up heavy wool pants without stretching in any way"," shape or form.""",https://www.example.com/prod
  ```

  ```
  Exp. ctd: C_1697.html,
  Got ctd.: uct/CC_1697.html,
  ```


#### `row_less_sep_row7_col6.csv`

- **Pollution:** Missing delimiter in row 7 at column 6
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 8:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 15/02/2018,01:30,2,RI-6052,$89.34,Organic Textured Cotton Towel"All the softness and absorbency you've come to expect...
  Clean:    15/02/2018,01:30,2,RI-6052,$89.34,Organic Textured Cotton Towel,"All the softness and absorbency you've come to expec...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 15/02/2018,01:30,2,RI-6052,$89.34,Organic Textured Cotton Towel,"All the softness and absorbency you've come t
  Got:      15/02/2018,01:30,2,RI-6052,$89.34,"Organic Textured Cotton Towel""All the softness and absorbency you've come 
  ```

  ```
  Exp. ctd: o expect from our towels, in certified organic cotton for natural, ecofriendly comfort.",https://www.example.c
  Got ctd.: to expect from our towels", in certified organic cotton for natural," ecofriendly comfort.""",https://www.exam
  ```

  ```
  Exp. ctd: om/product/RI_6052.html,
  Got ctd.: ple.com/product/RI_6052.html
  ```


#### `row_less_sep_row8_col5.csv`

- **Pollution:** Missing delimiter in row 8 at column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 0**


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 16/02/2018,01:45,2,YY-3522,$19.34,"Cycling Jersey, Short-Sleeve","Designed with lots of performance features, 
  Got:      16/02/2018,01:45,2,YY-3522,"$19.34""Cycling Jersey"," Short-Sleeve""","Designed with lots of performance featu
  ```

  ```
  Exp. ctd: plus a semi-form-fitting profile, this cycling jersey delivers all-day comfort and serious style.",https://www
  Got ctd.: res, plus a semi-form-fitting profile, this cycling jersey delivers all-day comfort and serious style.",https:
  ```

  ```
  Exp. ctd: .example.com/product/YY_3522.html,
  Got ctd.: //www.example.com/product/YY_3522.html,
  ```


### Row uses space as field delimiter — 3 files

*Variants: rows 0, 12, 39 (3 unique)*


#### `row_field_delimiter_0_0x20.csv`

- **Pollution:** Row 0 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 5; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 6; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 7; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 8; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 5; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 6; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 7; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 8; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 5; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 6; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 7; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 8; TOO MANY COLUMNS: Expected Number of Columns: 4 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE TIME Qty PRODUCTID Price ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 4 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      "28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots",These waterproof hiking boots for men are ru
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: gged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://ww
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: w.example.com/product/MG_8769.html,
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      "29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket","The next level of weather protection. This light-
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking 
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: the dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: product/RI_3895.html,
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      "30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes","Great grip and super extra breathability mak
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: e these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.htm
  ```

  ```
  Exp. ctd: 
  Got ctd.: l,
  ```


*… and 80 more*

#### `row_field_delimiter_12_0x20.csv`

- **Pollution:** Row 12 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 13:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 2; MISSING COLUMNS: Expected Number of Columns: 9 Found: 3; MISSING COLUMNS: Expected Number of Columns: 9 Found: 4; MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8`

  ```
  Polluted: 20/02/2018 02:45 1 BH-7531 $48.08 Women's  Fly Rod 8 Wt. "Amazingly crisp action and a remarkably light feel in our 8...
  Clean:    20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel in our 8...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.: n our 8\'9"""" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```


#### `row_field_delimiter_39_0x20.csv`

- **Pollution:** Row 39 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 40:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 5; MISSING COLUMNS: Expected Number of Columns: 9 Found: 6; MISSING COLUMNS: Expected Number of Columns: 9 Found: 7; MISSING COLUMNS: Expected Number of Columns: 9 Found: 8`

  ```
  Polluted: 13/04/2018 11:00 4 YY-9611 $3.79 "Women's Hunting Shoes, 10""" "The original boot, made since 1912. Now with even mor...
  Clean:    13/04/2018,11:00,4,YY-9611,$3.79,"Women's Hunting Shoes, 10""","The original boot, made since 1912. Now with even mor...
  ```


*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 13/04/2018,11:00,4,YY-9611,$3.79,"Women's Hunting Shoes, 10""","The original boot, made since 1912. Now with e
  Got:      13/04/2018,11:00,4,YY-9611,$3.79,"Women's Hunting Shoes, 10""""""","The original boot, made since 1912. Now wi
  ```

  ```
  Exp. ctd: ven more protection from cold, wet weather, with the addition of a waterproof liner and warm insulation.",http
  Got ctd.: th even more protection from cold, wet weather, with the addition of a waterproof liner and warm insulation.",
  ```

  ```
  Exp. ctd: s://www.example.com/product/YY_9611.html,
  Got ctd.: https://www.example.com/product/YY_9611.html,
  ```


### Empty file (0 bytes) — 1 file


#### `file_no_payload.csv`

- **Pollution:** Empty file (0 bytes)
- **Dialect:** `delimiter=''`, `quotechar=''`, `escapechar=''`, `row_delimiter=''`, `encoding='ascii'`, `header_lines=0`, `preamble_lines=0`, `n_columns=0`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=0`, `preamble_lines=0`

**Malformed rows detected: 0**


*Rows loaded: 0*


### No header row — 1 file


#### `file_no_header.csv`

- **Pollution:** No header row
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=0`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=0`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 1:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['28/01/2018', '00:00', '2', 'MG-8769', '$74.69', "Men's Waterproof Hiking Boots", 'These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.', 'https://www.example.com/product/MG_8769.html', '']`
- **Got:** `['', '', '', '', '', '', '', '']`

*Rows loaded: 83 (expected 82)*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 82 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: example.com/product/MG_8769.html
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: 
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: 
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,This lightweight fly rod delivers outstanding performance an
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: d can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is idea
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```

  ```
  Exp. ctd: l for larger rivers and situations where there isn't space for a backcast.,https://www.example.com/product/RI_
  Got ctd.: 
  ```

  ```
  Exp. ctd: 9546.html,
  Got ctd.: 
  ```


*… and 80 more*

### Non-standard escape character (0x5C) — 1 file


#### `file_escape_char_0x5C.csv`

- **Pollution:** Non-standard escape character (0x5C)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='\\'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 6**

- **line 11:** `UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 18/02/2018,02:15,2,BH-9827,$78.07,"All-Weather Dining Table, Round 48\"","Made in the USA to our exacting standards, ...
  Clean:    18/02/2018,02:15,2,BH-9827,$78.07,"All-Weather Dining Table, Round 48""","Made in the USA to our exacting standards, ...
  ```

- **line 13:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel in our 8...
  Clean:    20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel in our 8...
  ```

- **line 22:** `UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5\" Inseam","Perfect for a day on the bonefish flats, these boxers ar...
  Clean:    13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5"" Inseam","Perfect for a day on the bonefish flats, these boxers ar...
  ```


*… and 3 more*

*Rows loaded: 83*

**Diff:** 6 expected-but-missing, 6 unexpected-extra

- ```
  Expected: 18/02/2018,02:15,2,BH-9827,$78.07,"All-Weather Dining Table, Round 48""","Made in the USA to our exacting stan
  Got:      18/02/2018,02:15,2,BH-9827,$78.07,"All-Weather Dining Table, Round 48\""","Made in the USA to our exacting sta
  ```

  ```
  Exp. ctd: dards, this round patio table is durable enough to weather the elements year-round.",https://www.example.com/p
  Got ctd.: ndards, this round patio table is durable enough to weather the elements year-round.",https://www.example.com/
  ```

  ```
  Exp. ctd: roduct/BH_9827.html,
  Got ctd.: product/BH_9827.html,
  ```

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.: n our 8\'9\"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```

- ```
  Expected: 13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5"" Inseam","Perfect for a day on the bonefish flats, these bo
  Got:      13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5\"" Inseam","Perfect for a day on the bonefish flats, these b
  ```

  ```
  Exp. ctd: xers are breathable, quick drying and just may become your everyday underwear.",https://www.example.com/produc
  Got ctd.: oxers are breathable, quick drying and just may become your everyday underwear.",https://www.example.com/produ
  ```

  ```
  Exp. ctd: t/GN_9860.html,
  Got ctd.: ct/GN_9860.html,
  ```


*… and 3 more*

### Non-standard field delimiter (0x20) — 1 file


#### `file_field_delimiter_0x20.csv`

- **Pollution:** Non-standard field delimiter (0x20)
- **Dialect:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 2:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 28/01/2018 00:00 2 MG-8769 $74.69 Men's Waterproof Hiking Boots "These waterproof hiking boots for men are rugged eno...
  Clean:    28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 29/01/2018 00:15 0 RI-3895 $29.81 Light-Up Running Jacket "The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9`

  ```
  Polluted: 30/01/2018 00:30 1 RI-8070 $80.08 Men's Ventilated Trail Shoes "Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


*… and 80 more*

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: oduct/RI_3895.html
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

### Two tables with the same number of columns — 1 file


#### `file_multitable_same.csv`

- **Pollution:** Two tables with the same number of columns
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 106:** `UNQUOTED VALUE: Value with unterminated quote found.`

  ```
  Polluted: 13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5","" Inseam,"Perfect for a day on the bonefish flats, these boxers a...
  ```


*Rows loaded: 166 (expected 83)*

**Diff:** 0 expected-but-missing, 83 unexpected-extra

- ```
  Expected: (absent)
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: 
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: 
  Got ctd.: example.com/product/MG_8769.html,
  ```

- ```
  Expected: (absent)
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd: 
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: 
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: 
  Got ctd.: oduct/RI_3895.html,
  ```

- ```
  Expected: (absent)
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: 
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  ```


*… and 80 more*

### Two tables, first has fewer columns — 1 file


#### `file_multitable_less.csv`

- **Pollution:** Two tables, first has fewer columns
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 85:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 8`

  ```
  Polluted: DATE,TIME,Qty,PRODUCTID,Price,ProductType,ProductDescription,URL
  ```

- **line 86:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 8`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 87:** `MISSING COLUMNS: Expected Number of Columns: 9 Found: 8`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```


*… and 80 more*

*Rows loaded: 166 (expected 83)*

**Diff:** 0 expected-but-missing, 83 unexpected-extra

- ```
  Expected: (absent)
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: 
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: 
  Got ctd.: example.com/product/MG_8769.html,
  ```

- ```
  Expected: (absent)
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd: 
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: 
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: 
  Got ctd.: oduct/RI_3895.html,
  ```

- ```
  Expected: (absent)
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: 
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  ```


*… and 80 more*

### Two tables, first has more columns — 1 file


#### `file_multitable_more.csv`

- **Pollution:** Two tables, first has more columns
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 83**

- **line 85:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: DATE,TIME,Qty,PRODUCTID,Price,ProductType,ProductDescription,URL,Comments,col1
  ```

- **line 86:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enou...
  ```

- **line 87:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```


*… and 80 more*

*Rows loaded: 166 (expected 83)*

**Diff:** 0 expected-but-missing, 83 unexpected-extra

- ```
  Expected: (absent)
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  ```

  ```
  Exp. ctd: 
  Got ctd.: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  ```

  ```
  Exp. ctd: 
  Got ctd.: example.com/product/MG_8769.html,
  ```

- ```
  Expected: (absent)
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  ```

  ```
  Exp. ctd: 
  Got ctd.:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  ```

  ```
  Exp. ctd: 
  Got ctd.: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  ```

  ```
  Exp. ctd: 
  Got ctd.: oduct/RI_3895.html,
  ```

- ```
  Expected: (absent)
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: 
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  ```


*… and 80 more*
