# llm_hybrid_parser_gpt_5_4_clevercsv — polluted_files

| | |
|---|---|
| Results file | `results/llm_hybrid_parser_gpt_5_4_clevercsv/polluted_files/llm_hybrid_parser_gpt_5_4_clevercsv_results.csv` |
| Total files evaluated | 2291 |
| Application errors | 0 |
| Wrong content | 266 |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 266 files

| N | Type |
|--:|------|
| 109 | Extra delimiter |
| 92 | Extra unescaped quote |
| 57 | Missing delimiter |
| 2 | Row uses space as field delimiter |
| 1 | Empty file (0 bytes) |
| 1 | No header row |
| 1 | Two tables with the same number of columns |
| 1 | Two tables, first has fewer columns |
| 1 | Two tables, first has more columns |
| 1 | Unknown |


### Extra delimiter — 109 files

*Variants: rows 0-2, 4-10, 12-19, 21-23, 25-28, 30-35, 37-60, 62-69, 71-73, 75-76, 79-81, 83 (72 unique); columns 0-2, 4-8 (8 unique)*

*Showing 3 example file(s); 106 more under this type.*


#### `row_more_sep_row0_col0.csv`

- **Pollution:** Extra delimiter in row 0 at column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['', 'DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 10 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

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
  Got ctd.: .example.com/product/MG_8769.html,
  ```

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
  Got ctd.: roduct/RI_3895.html,
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      ,30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make
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

#### `row_more_sep_row0_col1.csv`

- **Pollution:** Extra delimiter in row 0 at column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', '', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 10 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

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
  Got ctd.: .example.com/product/MG_8769.html,
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018,,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-u
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
  Got:      30/01/2018,,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make
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

#### `row_more_sep_row0_col2.csv`

- **Pollution:** Extra delimiter in row 0 at column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', '', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 10 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

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
  Got ctd.: .example.com/product/MG_8769.html,
  ```

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
  Got ctd.: roduct/RI_3895.html,
  ```

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018,00:30,,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make
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

### Extra unescaped quote — 92 files

*Variants: rows 1-2, 11-29, 31-83 (74 unique); columns 5, 8 (2 unique)*

*Showing 3 example file(s); 89 more under this type.*


#### `row_extra_quote1_col5.csv`

- **Pollution:** Extra unescaped quote in row 1, column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,"""Men's Waterproof Hiking Boots",These waterproof hiking boots for men are 
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,"Men's Waterproof Hiking Boots,",These waterproof hiking boots for men are r
  ```

  ```
  Exp. ctd: rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://
  Got ctd.: ugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://w
  ```

  ```
  Exp. ctd: www.example.com/product/MG_8769.html,
  Got ctd.: ww.example.com/product/MG_8769.html,
  ```


#### `row_extra_quote2_col5.csv`

- **Pollution:** Extra unescaped quote in row 2, column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,"""Light-Up Running Jacket","The next level of weather protection. This ligh
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,"Light-Up Running Jacket,","The next level of weather protection. This light
  ```

  ```
  Exp. ctd: t-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walkin
  Got ctd.: -up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking
  ```

  ```
  Exp. ctd: g the dog, the durable construction and innovative safety features won't let you down.",https://www.example.co
  Got ctd.:  the dog, the durable construction and innovative safety features won't let you down.",https://www.example.com
  ```

  ```
  Exp. ctd: m/product/RI_3895.html,
  Got ctd.: /product/RI_3895.html,
  ```


#### `row_extra_quote11_col5.csv`

- **Pollution:** Extra unescaped quote in row 11, column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 19/02/2018,02:30,1,BH-7885,$52.45,"""Women's No-Show Socks","The warmth and comfort of wool, these socks are d
  Got:      19/02/2018,02:30,1,BH-7885,$52.45,"Women's No-Show Socks,","The warmth and comfort of wool, these socks are de
  ```

  ```
  Exp. ctd: esigned in a minimal, no-show style that is of pure elegance and design.",https://www.example.com/product/BH_7
  Got ctd.: signed in a minimal, no-show style that is of pure elegance and design.",https://www.example.com/product/BH_78
  ```

  ```
  Exp. ctd: 885.html,
  Got ctd.: 85.html,
  ```


### Missing delimiter — 57 files

*Variants: rows 0, 3, 5-6, 8-10, 12-14, 16-22, 26, 28, 30, 32-34, 37-40, 45-47, 49-50, 53-58, 60-62, 64-65, 69, 71-72, 76-77, 80, 83 (50 unique); columns 1-3, 5-6 (5 unique)*

*Showing 3 example file(s); 54 more under this type.*


#### `row_less_sep_row0_col1.csv`

- **Pollution:** Missing delimiter in row 0 at column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATETIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018 00:00,2,MG-8769,$74.69,,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rug
  ```

  ```
  Exp. ctd: ed enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.
  Got ctd.: ged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www
  ```

  ```
  Exp. ctd: example.com/product/MG_8769.html,
  Got ctd.: .example.com/product/MG_8769.html
  ```

- ```
  Expected: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up
  Got:      29/01/2018 00:15,0,RI-3895,$29.81,,Light-Up Running Jacket,"The next level of weather protection. This light-u
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

- ```
  Expected: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make 
  Got:      30/01/2018 00:30,1,RI-8070,$80.08,,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.:  these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html
  ```


*… and 80 more*

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

#### `row_less_sep_row0_col5.csv`

- **Pollution:** Missing delimiter in row 0 at column 5
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'PriceProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 83*

*Cols: expected 9, got 8 (first data row)*

**Diff:** 83 expected-but-missing, 83 unexpected-extra

- ```
  Expected: 28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugg
  Got:      28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,https://www.example.com/product/MG_8769.html,
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
  Got:      29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,https://www.example.com/product/RI_3895.html,
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
  Got:      30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,https://www.example.com/product/RI_8070.html,
  ```

  ```
  Exp. ctd: these amazing ventilated hikers ideal for warm, dry conditions.",https://www.example.com/product/RI_8070.html,
  Got ctd.: 
  ```


*… and 80 more*

### Row uses space as field delimiter — 2 files

*Variants: rows 0, 33 (2 unique)*


#### `row_field_delimiter_0_0x20.csv`

- **Pollution:** Row 0 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

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

#### `row_field_delimiter_33_0x20.csv`

- **Pollution:** Row 33 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
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


### Empty file (0 bytes) — 1 file


#### `file_no_payload.csv`

- **Pollution:** Empty file (0 bytes)
- **Dialect:** `delimiter=''`, `quotechar=''`, `escapechar=''`, `row_delimiter=''`, `encoding='ascii'`, `header_lines=0`, `preamble_lines=0`, `n_columns=0`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=0`, `preamble_lines=0`

*Rows loaded: 0*


### No header row — 1 file


#### `file_no_header.csv`

- **Pollution:** No header row
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=0`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=0`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['28/01/2018', '00:00', '2', 'MG-8769', '$74.69', "Men's Waterproof Hiking Boots", 'These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.', 'https://www.example.com/product/MG_8769.html', '']`
- **Got:** `['date', 'time', 'quantity', 'product_code', 'price', 'product_name', 'description', 'url', '']`

*Rows loaded: 83 (expected 82)*

**Diff:** 0 expected-but-missing, 1 unexpected-extra

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


### Two tables with the same number of columns — 1 file


#### `file_multitable_same.csv`

- **Pollution:** Two tables with the same number of columns
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

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

### Unknown — 1 file


#### `file_quotation_char_none.csv`

- **Pollution:** Unknown
- **Dialect:** `delimiter=','`, `quotechar=''`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 3 expected-but-missing, 3 unexpected-extra

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.: n our 8\'9"""" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```

- ```
  Expected: 13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5"" Inseam","Perfect for a day on the bonefish flats, these bo
  Got:      13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5"""" Inseam","Perfect for a day on the bonefish flats, these 
  ```

  ```
  Exp. ctd: xers are breathable, quick drying and just may become your everyday underwear.",https://www.example.com/produc
  Got ctd.: boxers are breathable, quick drying and just may become your everyday underwear.",https://www.example.com/prod
  ```

  ```
  Exp. ctd: t/GN_9860.html,
  Got ctd.: uct/GN_9860.html,
  ```

- ```
  Expected: 24/07/2018,16:00,6,GN-2043,$23.25,"Men's Boots, 10"" Shearling-Lined","With waterproof leather outside and sof
  Got:      24/07/2018,16:00,6,GN-2043,$23.25,"Men's Boots, 10"""" Shearling-Lined","With waterproof leather outside and s
  ```

  ```
  Exp. ctd: t, plush shearling inside, our lined Boots are very possibly the coolest, warmest boots ever. Handcrafted righ
  Got ctd.: oft, plush shearling inside, our lined Boots are very possibly the coolest, warmest boots ever. Handcrafted ri
  ```

  ```
  Exp. ctd: t here.",https://www.example.com/product/GN_2043.html,
  Got ctd.: ght here.",https://www.example.com/product/GN_2043.html,
  ```

