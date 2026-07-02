# llm_hybrid_parser_gpt_5_4_duckdb_special_prompt — small_sample

| | |
|---|---|
| Results file | `results/llm_hybrid_parser_gpt_5_4_duckdb_special_prompt/small_sample/llm_hybrid_parser_gpt_5_4_duckdb_special_prompt_results.csv` |
| Total files evaluated | 17 |
| Application errors | 0 |
| Wrong content | 3 |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 3 files

| N | Type |
|--:|------|
| 1 | Extra delimiter |
| 1 | Extra unescaped quote |
| 1 | Non-standard field delimiter (0x20) |


### Extra delimiter — 1 file

*Variants: rows 3 (1 unique); columns 0 (1 unique)*


#### `row_more_sep_row3_col0.csv`

- **Pollution:** Extra delimiter in row 3 at column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      ,30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.:  these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


### Extra unescaped quote — 1 file

*Variants: rows 3 (1 unique); columns 5 (1 unique)*


#### `row_extra_quote3_col5.csv`

- **Pollution:** Extra unescaped quote in row 3, column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,"""Men's Ventilated Trail Shoes","Great grip and super extra breathability m
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,"""Men's Ventilated Trail Shoes","Great grip and super extra breathability m
  ```

  ```
  Exp. ctd: ake these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.h
  Got ctd.: ake these amazing ventilated hikers ideal for warm, dry conditions.""",https://www.example.com/product/RI_8070
  ```

  ```
  Exp. ctd: tml,
  Got ctd.: .html,
  ```


### Non-standard field delimiter (0x20) — 1 file


#### `file_field_delimiter_0x20.csv`

- **Pollution:** Non-standard field delimiter (0x20)
- **Dialect:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 2 expected-but-missing, 2 unexpected-extra

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.: n our 8\'9"""" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```

- ```
  Expected: 22/02/2018,03:15,3,HK-3372,$6.45,Tropic Cap,"Made with the same tropical fabric as our bestselling shirts, thi
  Got:      22/02/2018,03:15,3,HK-3372,$6.45,Tropic,Cap,"Made with the same tropical fabric as our bestselling shirts, thi
  ```

  ```
  Exp. ctd: s wonderful cap provides UPF 50+ sun protection.",https://www.example.com/product/HK_3372.html,
  Got ctd.: s wonderful cap provides UPF 50+ sun protection.",https://www.example.com/product/HK_3372.html
  ```

