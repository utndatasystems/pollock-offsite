# llm_hybrid_parser_gpt_5_4_mini_duckdb_special_prompt — small_sample

| | |
|---|---|
| Results file | `results/llm_hybrid_parser_gpt_5_4_mini_duckdb_special_prompt/small_sample/llm_hybrid_parser_gpt_5_4_mini_duckdb_special_prompt_results.csv` |
| Total files evaluated | 17 |
| Application errors | 0 |
| Wrong content | 4 |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 4 files

| N | Type |
|--:|------|
| 1 | Extra delimiter |
| 1 | Non-standard field delimiter (0x2C_0x20) |
| 1 | Non-standard quotation character (0x27) |
| 1 | Row uses space as field delimiter |


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
  Got:      29/01/2018, 00:15, 0, RI-3895, $29.81, Light-Up Running Jacket," ""The next level of weather protection. This 
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or wa
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: lking the dog, the durable construction and innovative safety features won't let you down."""," ""https://www.
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: example.com/product/RI_3895.html""", 
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018, 00:30, 1, RI-8070, $80.08, Men's Ventilated Trail Shoes," ""Great grip and super extra breathabili
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: ty make these amazing ventilated hikers ideal for warm, dry conditions."""," ""https://www.example.com/product
  ```

  ```
  Exp. ctd: 
  Got ctd.: /RI_8070.html""", 
  ```


*… and 80 more*

### Non-standard quotation character (0x27) — 1 file


#### `file_quotation_char_0x27.csv`

- **Pollution:** Non-standard quotation character (0x27)
- **Dialect:** `delimiter=','`, `quotechar="'"`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', "'ProductDescription'", "'URL'", 'Comments']`

*Rows loaded: 83*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,'These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.','https://w
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: ww.example.com/product/MG_8769.html',
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"'The next level of weather protection. This light-u
  ```

  ```
  Exp. ctd:  jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking th
  Got ctd.: p jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking t
  ```

  ```
  Exp. ctd: e dog, the durable construction and innovative safety features won't let you down.",https://www.example.com/pr
  Got ctd.: he dog, the durable construction and innovative safety features won't let you down.'",'https://www.example.com
  ```

  ```
  Exp. ctd: oduct/RI_3895.html,
  Got ctd.: /product/RI_3895.html',
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"'Great grip and super extra breathability make
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.:  these amazing ventilated hikers ideal for warm, dry conditions.'",'https://www.example.com/product/RI_8070.ht
  ```

  ```
  Exp. ctd: 
  Got ctd.: ml',
  ```


*… and 80 more*

### Row uses space as field delimiter — 1 file

*Variants: rows 34 (1 unique)*


#### `row_field_delimiter_34_0x20.csv`

- **Pollution:** Row 34 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 27/03/2018,08:30,3,ON-1026,$20.65,"Tee, Traditional Fit, Short-Sleeve","Made of soft cotton that resists wrink
  Got:      "27/03/2018 08:30 3 ON-1026 $20.65 ""Tee",Traditional Fit,"Short-Sleeve"" ""Made of soft cotton that resists w
  ```

  ```
  Exp. ctd: les, stains, shrinking, fading and pilling, our resilient tee keeps its shape wash after wash.",https://www.ex
  Got ctd.: rinkles",stains,shrinking,fading and pilling,"our resilient tee keeps its shape wash after wash."" ""https://w
  ```

  ```
  Exp. ctd: ample.com/product/ON_1026.html,
  Got ctd.: ww.example.com/product/ON_1026.html"" ",,
  ```

