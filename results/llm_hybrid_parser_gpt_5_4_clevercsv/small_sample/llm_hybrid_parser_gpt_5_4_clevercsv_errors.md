# llm_hybrid_parser_gpt_5_4_clevercsv — small_sample

| | |
|---|---|
| Results file | `results/llm_hybrid_parser_gpt_5_4_clevercsv/small_sample/llm_hybrid_parser_gpt_5_4_clevercsv_results.csv` |
| Total files evaluated | 17 |
| Application errors | 0 |
| Wrong content | 4 |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 4 files

| N | Type |
|--:|------|
| 2 | Extra unescaped quote |
| 1 | Non-standard field delimiter (0x20) |
| 1 | Non-standard field delimiter (0x2C_0x20) |


### Extra unescaped quote — 2 files

*Variants: rows 3 (1 unique); columns 0, 5 (2 unique)*


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


### Non-standard field delimiter (0x20) — 1 file


#### `file_field_delimiter_0x20.csv`

- **Pollution:** Non-standard field delimiter (0x20)
- **Dialect:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType ProductDescription', 'URL', 'Comments']`

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

### Non-standard field delimiter (0x2C_0x20) — 1 file


#### `file_field_delimiter_0x2C_0x20.csv`

- **Pollution:** Non-standard field delimiter (0x2C_0x20)
- **Dialect:** `delimiter=', '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018, 00:00, 2, MG-8769, $74.69, Men's Waterproof Hiking Boots,These waterproof hiking boots for men are
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.:  rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https:/
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: /www.example.com/product/MG_8769.html, 
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018, 00:15, 0, RI-3895, $29.81, Light-Up Running Jacket,"The next level of weather protection. This lig
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: ht-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walki
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: ng the dog, the durable construction and innovative safety features won't let you down.",https://www.example.c
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: om/product/RI_3895.html, 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018, 00:30, 1, RI-8070, $80.08, Men's Ventilated Trail Shoes,"Great grip and super extra breathability 
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: make these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.
  ```

  ```
  Exp. ctd: 
  Got ctd.: html, 
  ```


*… and 80 more*
