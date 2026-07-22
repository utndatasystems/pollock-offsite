# llm_hybrid_parser_gpt_5_4_clevercsv — small_sample

| | |
|---|---|
| Results file | `results/llm_hybrid_parser_gpt_5_4_clevercsv/small_sample/llm_hybrid_parser_gpt_5_4_clevercsv_results.csv` |
| Total files evaluated | 23 |
| Application errors | 0 |
| Wrong content | 2 |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 2 files

| N | Type |
|--:|------|
| 1 | Extra delimiter |
| 1 | Missing delimiter |


### Extra delimiter — 1 file

*Variants: rows 33 (1 unique); columns 5 (1 unique)*


#### `row_more_sep_row33_col5.csv`

- **Pollution:** Extra delimiter in row 33 at column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 26/03/2018,08:15,2,ON-7017,$0.9,"Quarter-Zip Hoodie, Camo","This camo quarter-zip hoodie is an extremely versa
  Got:      26/03/2018,08:15,2,ON-7017,$0.9,,"Quarter-Zip Hoodie, Camo","This camo quarter-zip hoodie is an extremely vers
  ```

  ```
  Exp. ctd: tile mid layer thats great for all hunting seasons. Its made from warm, breathable fleece and features an inno
  Got ctd.: atile mid layer thats great for all hunting seasons. Its made from warm, breathable fleece and features an inn
  ```

  ```
  Exp. ctd: vative lightweight hood with a built-in face mask.",https://www.example.com/product/ON_7017.html,
  Got ctd.: ovative lightweight hood with a built-in face mask.",https://www.example.com/product/ON_7017.html
  ```


### Missing delimiter — 1 file

*Variants: rows 0 (1 unique); columns 2 (1 unique)*


#### `row_less_sep_row0_col2.csv`

- **Pollution:** Missing delimiter in row 0 at column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

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
