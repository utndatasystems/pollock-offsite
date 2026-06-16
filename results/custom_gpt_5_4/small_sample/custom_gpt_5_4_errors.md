# custom_gpt_5_4 — small_sample

| | |
|---|---|
| Results file | `results/custom_gpt_5_4/small_sample/custom_gpt_5_4_results.csv` |
| Total files evaluated | 17 |
| Application errors | 0 |
| Wrong content | 2 |
| Malformed sidecars | 17 / 17 |


## Custom Malformed-Row Detection

*Scope: wrong-content files only*

| Metric | Value |
|--------|-------|
| Sidecar reports found | 2 / 2 |
| Files with detected malformed rows | 2 / 2 (100.0%) |
| Total malformed rows logged | 89 |

### Detection by Pollution Type

| Det | Total | % | Type | Rows logged |
|----:|------:|--:|------|------------:|
| 1 | 1 | 100.0% | Non-standard escape character (0x5C) | 6 |
| 1 | 1 | 100.0% | Non-standard field delimiter (0x20) | 83 |

### Malformed Row Reasons

| N | Reason |
|--:|--------|
| 34 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 22 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 18 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 7 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 4 | `UNQUOTED VALUE: Value with unterminated quote found.` |
| 2 | `TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 13; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 14; TOO MANY COLUMNS: Expected Number of Columns: 8 Found: 9` |
| 1 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; UNQUOTED VALUE: Value with unterminated quote found.` |
| 1 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; UNQUOTED VALUE: Value with unterminated quote found.` |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 2 files

| N | Type |
|--:|------|
| 1 | Non-standard escape character (0x5C) |
| 1 | Non-standard field delimiter (0x20) |


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

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.: n our 8\'9\"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```


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
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL Comments']`

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
