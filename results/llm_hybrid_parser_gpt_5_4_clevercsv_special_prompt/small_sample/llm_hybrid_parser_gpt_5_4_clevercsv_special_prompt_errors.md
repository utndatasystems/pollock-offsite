# llm_hybrid_parser_gpt_5_4_clevercsv_special_prompt — small_sample

| | |
|---|---|
| Results file | `results/llm_hybrid_parser_gpt_5_4_clevercsv_special_prompt/small_sample/llm_hybrid_parser_gpt_5_4_clevercsv_special_prompt_results.csv` |
| Total files evaluated | 23 |
| Application errors | 0 |
| Wrong content | 5 |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 5 files

| N | Type |
|--:|------|
| 4 | Extra unescaped quote |
| 1 | Multi-row header (3 rows) |


### Extra unescaped quote — 4 files

*Variants: rows 0, 3, 36 (3 unique); columns 0, 2-3, 5 (4 unique)*

*Showing 3 example file(s); 1 more under this type.*


#### `row_extra_quote0_col2.csv`

- **Pollution:** Extra unescaped quote in row 0, column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE', 'TIME', '"Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*


#### `row_extra_quote3_col0.csv`

- **Pollution:** Extra unescaped quote in row 3, column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: """30/01/2018",00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability m
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: ake these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.h
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  ```

  ```
  Exp. ctd: tml,
  Got ctd.: 
  ```


#### `row_extra_quote3_col5.csv`

- **Pollution:** Extra unescaped quote in row 3, column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,"""Men's Ventilated Trail Shoes","Great grip and super extra breathability m
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  ```

  ```
  Exp. ctd: ake these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.h
  Got ctd.: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  ```

  ```
  Exp. ctd: tml,
  Got ctd.: 
  ```


### Multi-row header (3 rows) — 1 file


#### `file_header_multirow_3.csv`

- **Pollution:** Multi-row header (3 rows)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=3`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=3`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE DATE DATE', 'TIME TIME TIME', 'Qty Qty Qty', 'PRODUCTID PRODUCTID PRODUCTID', 'Price Price Price', 'ProductType ProductType ProductType', 'ProductDescription ProductDescription ProductDescription', 'URL URL URL', 'Comments Comments Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

