# llm_hybrid_parser_gpt_4o_duckdb — small_sample

| | |
|---|---|
| Results file | `results/llm_hybrid_parser_gpt_4o_duckdb/small_sample/llm_hybrid_parser_gpt_4o_duckdb_results.csv` |
| Total files evaluated | 17 |
| Application errors | 0 |
| Wrong content | 6 |


## Application Errors — 0 files

*(none)*

*(none)*

## Wrong Content — 6 files

| N | Type |
|--:|------|
| 1 | Multi-row header (3 rows) |
| 1 | Non-standard escape character (0x00) |
| 1 | Non-standard escape character (0x5C) |
| 1 | Non-standard field delimiter (0x20) |
| 1 | Non-standard field delimiter (0x2C_0x20) |
| 1 | Non-standard quotation character (0x27) |


### Multi-row header (3 rows) — 1 file


#### `file_header_multirow_3.csv`

- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Header mismatch**

- **Expected:** `['DATE DATE DATE', 'TIME TIME TIME', 'Qty Qty Qty', 'PRODUCTID PRODUCTID PRODUCTID', 'Price Price Price', 'ProductType ProductType ProductType', 'ProductDescription ProductDescription ProductDescription', 'URL URL URL', 'Comments Comments Comments']`
- **Got:** `['DATE', 'TIME', 'Qty', 'PRODUCTID', 'Price', 'ProductType', 'ProductDescription', 'URL', 'Comments']`

*Rows loaded: 85 (expected 83)*

**Diff:** 0 expected-but-missing, 2 unexpected-extra

- ```
  Expected: (absent)
  Got:      DATE,TIME,Qty,PRODUCTID,Price,ProductType,ProductDescription,URL,Comments
  ```


*… and 1 more*

### Non-standard escape character (0x00) — 1 file


#### `file_escape_char_0x00.csv`

- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel in
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.:  our 8'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```


### Non-standard escape character (0x5C) — 1 file


#### `file_escape_char_0x5C.csv`

- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='\\'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='\\'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.: n our 8'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```


### Non-standard field delimiter (0x20) — 1 file


#### `file_field_delimiter_0x20.csv`

- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 83*

**Diff:** 1 expected-but-missing, 1 unexpected-extra

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel in
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.:  our 8'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```


### Non-standard field delimiter (0x2C_0x20) — 1 file


#### `file_field_delimiter_0x2C_0x20.csv`

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

### Non-standard quotation character (0x27) — 1 file


#### `file_quotation_char_0x27.csv`

- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar="'"`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

*Rows loaded: 81 (expected 83)*

**Diff:** 5 expected-but-missing, 3 unexpected-extra

- ```
  Expected: 20/02/2018,02:45,1,BH-7531,$48.08,Women's  Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel i
  Got:      20/02/2018,02:45,1,BH-7531,$48.08,Women's Fly Rod 8 Wt.,"Amazingly crisp action and a remarkably light feel in
  ```

  ```
  Exp. ctd: n our 8\'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  Got ctd.:  our 8'9 length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```

- ```
  Expected: 13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5"" Inseam","Perfect for a day on the bonefish flats, these bo
  Got:      13/03/2018,05:00,0,GN-9860,$24.86,"Men's Boxer, 5 Inseam","Perfect for a day on the bonefish flats, these boxe
  ```

  ```
  Exp. ctd: xers are breathable, quick drying and just may become your everyday underwear.",https://www.example.com/produc
  Got ctd.: rs are breathable, quick drying and just may become your everyday underwear.",https://www.example.com/product/
  ```

  ```
  Exp. ctd: t/GN_9860.html,
  Got ctd.: GN_9860.html,
  ```

- ```
  Expected: 14/03/2018,05:15,1,YY-2600,$90.99,"Kids' Mountain Bike, 24""","An easy-to-ride mountain bike that not only pro
  Got:      24/07/2018,16:00,6,GN-2043,$23.25,"Men's Boots, 10 Shearling-Lined","With waterproof leather outside and soft,
  ```

  ```
  Exp. ctd: ves to be great fun for all the kids, but also offers great durability and stability.",https://www.example.com
  Got ctd.:  plush shearling inside, our lined Boots are very possibly the coolest, warmest boots ever. Handcrafted right 
  ```

  ```
  Exp. ctd: /product/YY_2600.html,
  Got ctd.: here.",https://www.example.com/product/GN_2043.html,
  ```


*… and 2 more*
