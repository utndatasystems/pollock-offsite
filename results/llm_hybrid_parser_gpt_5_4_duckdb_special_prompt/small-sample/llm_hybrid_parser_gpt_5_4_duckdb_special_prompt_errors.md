# llm_hybrid_parser_gpt_5_4_duckdb_special_prompt — small-sample

| | |
|---|---|
| Results file | `results/llm_hybrid_parser_gpt_5_4_duckdb_special_prompt/small-sample/llm_hybrid_parser_gpt_5_4_duckdb_special_prompt_results.csv` |
| Total files evaluated | 2291 |
| Application errors | 2291 |
| Wrong content | 0 |


## Application Errors — 2291 files

| N | Type |
|--:|------|
| 756 | Extra delimiter |
| 756 | Extra unescaped quote |
| 672 | Missing delimiter |
| 84 | Row uses space as field delimiter |
| 2 | Unknown |
| 1 | Double trailing newline |
| 1 | Empty file (0 bytes) |
| 1 | Header row only, no data |
| 1 | Missing trailing newline |
| 1 | Multi-row header (2 rows) |
| 1 | Multi-row header (3 rows) |
| 1 | No header row |
| 1 | Non-standard escape character (0x00) |
| 1 | Non-standard escape character (0x5C) |
| 1 | Non-standard field delimiter (0x20) |
| 1 | Non-standard field delimiter (0x2C_0x20) |
| 1 | Non-standard field delimiter (0x3B) |
| 1 | Non-standard field delimiter (0x9) |
| 1 | Non-standard quotation character (0x27) |
| 1 | Non-standard record delimiter (0xA) |
| 1 | Non-standard record delimiter (0xD) |
| 1 | Preamble rows before header |
| 1 | Single data row |
| 1 | Two tables with the same number of columns |
| 1 | Two tables, first has fewer columns |
| 1 | Two tables, first has more columns |


### Extra delimiter — 756 files

*Variants: rows 0-83 (84 unique); columns 0-8 (9 unique)*

*Showing 3 example file(s); 753 more under this type.*


#### `row_more_sep_row0_col0.csv`

- **Pollution:** Extra delimiter in row 0 at column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
,DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

#### `row_more_sep_row0_col1.csv`

- **Pollution:** Extra delimiter in row 0 at column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

#### `row_more_sep_row0_col2.csv`

- **Pollution:** Extra delimiter in row 0 at column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Extra unescaped quote — 756 files

*Variants: rows 0-83 (84 unique); columns 0-8 (9 unique)*

*Showing 3 example file(s); 753 more under this type.*


#### `row_extra_quote0_col0.csv`

- **Pollution:** Extra unescaped quote in row 0, column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
"DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

#### `row_extra_quote0_col1.csv`

- **Pollution:** Extra unescaped quote in row 0, column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,"TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

#### `row_extra_quote0_col2.csv`

- **Pollution:** Extra unescaped quote in row 0, column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,"Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Missing delimiter — 672 files

*Variants: rows 0-83 (84 unique); columns 1-8 (8 unique)*

*Showing 3 example file(s); 669 more under this type.*


#### `row_less_sep_row0_col1.csv`

- **Pollution:** Missing delimiter in row 0 at column 1
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATETIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

#### `row_less_sep_row0_col2.csv`

- **Pollution:** Missing delimiter in row 0 at column 2
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIMEQty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

#### `row_less_sep_row0_col3.csv`

- **Pollution:** Missing delimiter in row 0 at column 3
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,QtyPRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Row uses space as field delimiter — 84 files

*Variants: rows 0-83 (84 unique)*

*Showing 3 example file(s); 81 more under this type.*


#### `row_field_delimiter_0_0x20.csv`

- **Pollution:** Row 0 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE TIME Qty PRODUCTID Price ProductType "ProductDescription" "URL" Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

#### `row_field_delimiter_1_0x20.csv`

- **Pollution:** Row 1 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018 00:00 2 MG-8769 $74.69 Men's Waterproof Hiking Boots "These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down." "https://www.example.com/product/MG_8769.html" 
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

#### `row_field_delimiter_2_0x20.csv`

- **Pollution:** Row 2 uses space as field delimiter (opposed to the correct delimiter defined by the grammar)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018 00:15 0 RI-3895 $29.81 Light-Up Running Jacket "The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down." "https://www.example.com/product/RI_3895.html" 
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Unknown — 2 files


#### `file_quotation_char_none.csv`

- **Pollution:** Unknown
- **Dialect:** `delimiter=','`, `quotechar=''`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,ProductDescription,URL,Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.,https://www.example.com/product/MG_8769.html,
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.,https://www.example.com/product/RI_3895.html,
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.,https://www.example.com/product/RI_8070.html,
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.,https://www.example.com/product/RI_9546.html,
```

#### `source.csv`

- **Pollution:** Unknown
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Double trailing newline — 1 file


#### `file_double_trailing_newline.csv`

- **Pollution:** Double trailing newline
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Empty file (0 bytes) — 1 file


#### `file_no_payload.csv`

- **Pollution:** Empty file (0 bytes)
- **Dialect:** `delimiter=''`, `quotechar=''`, `escapechar=''`, `row_delimiter=''`, `encoding='ascii'`, `header_lines=0`, `preamble_lines=0`, `n_columns=0`

**SUT failed to load the file.**

First lines of polluted input:

```





```

### Header row only, no data — 1 file


#### `file_header_only.csv`

- **Pollution:** Header row only, no data
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar=''`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=0`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments




```

### Missing trailing newline — 1 file


#### `file_no_trailing_newline.csv`

- **Pollution:** Missing trailing newline
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Multi-row header (2 rows) — 1 file


#### `file_header_multirow_2.csv`

- **Pollution:** Multi-row header (2 rows)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=2`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,ProductDescription,URL,Comments
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
```

### Multi-row header (3 rows) — 1 file


#### `file_header_multirow_3.csv`

- **Pollution:** Multi-row header (3 rows)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=3`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,ProductDescription,URL,Comments
DATE,TIME,Qty,PRODUCTID,Price,ProductType,ProductDescription,URL,Comments
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
```

### No header row — 1 file


#### `file_no_header.csv`

- **Pollution:** No header row
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=0`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
13/02/2018,01:00,9,CC-9259,$48.00,"Throw Pillow, Wooden Paddles","Add a pop of paddling fun to your bed, chair or sofa with this whimsical throw pillow, handhooked on front for a timeless style.","https://www.example.com/product/CC_9259.html",
```

### Non-standard escape character (0x00) — 1 file


#### `file_escape_char_0x00.csv`

- **Pollution:** Non-standard escape character (0x00)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar=''`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Non-standard escape character (0x5C) — 1 file


#### `file_escape_char_0x5C.csv`

- **Pollution:** Non-standard escape character (0x5C)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='\\'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Non-standard field delimiter (0x20) — 1 file


#### `file_field_delimiter_0x20.csv`

- **Pollution:** Non-standard field delimiter (0x20)
- **Dialect:** `delimiter=' '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE TIME Qty PRODUCTID Price ProductType "ProductDescription" "URL" Comments
28/01/2018 00:00 2 MG-8769 $74.69 Men's Waterproof Hiking Boots "These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down." "https://www.example.com/product/MG_8769.html" 
29/01/2018 00:15 0 RI-3895 $29.81 Light-Up Running Jacket "The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down." "https://www.example.com/product/RI_3895.html" 
30/01/2018 00:30 1 RI-8070 $80.08 Men's Ventilated Trail Shoes "Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions." "https://www.example.com/product/RI_8070.html" 
31/01/2018 00:45 1 RI-9546 $25.55 Switch Fly Rods "This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast." "https://www.example.com/product/RI_9546.html" 
```

### Non-standard field delimiter (0x2C_0x20) — 1 file


#### `file_field_delimiter_0x2C_0x20.csv`

- **Pollution:** Non-standard field delimiter (0x2C_0x20)
- **Dialect:** `delimiter=', '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE, TIME, Qty, PRODUCTID, Price, ProductType, "ProductDescription", "URL", Comments
28/01/2018, 00:00, 2, MG-8769, $74.69, Men's Waterproof Hiking Boots, "These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.", "https://www.example.com/product/MG_8769.html", 
29/01/2018, 00:15, 0, RI-3895, $29.81, Light-Up Running Jacket, "The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.", "https://www.example.com/product/RI_3895.html", 
30/01/2018, 00:30, 1, RI-8070, $80.08, Men's Ventilated Trail Shoes, "Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.", "https://www.example.com/product/RI_8070.html", 
31/01/2018, 00:45, 1, RI-9546, $25.55, Switch Fly Rods, "This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.", "https://www.example.com/product/RI_9546.html", 
```

### Non-standard field delimiter (0x3B) — 1 file


#### `file_field_delimiter_0x3B.csv`

- **Pollution:** Non-standard field delimiter (0x3B)
- **Dialect:** `delimiter=';'`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE;TIME;Qty;PRODUCTID;Price;ProductType;"ProductDescription";"URL";Comments
28/01/2018;00:00;2;MG-8769;$74.69;Men's Waterproof Hiking Boots;"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.";"https://www.example.com/product/MG_8769.html";
29/01/2018;00:15;0;RI-3895;$29.81;Light-Up Running Jacket;"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.";"https://www.example.com/product/RI_3895.html";
30/01/2018;00:30;1;RI-8070;$80.08;Men's Ventilated Trail Shoes;"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.";"https://www.example.com/product/RI_8070.html";
31/01/2018;00:45;1;RI-9546;$25.55;Switch Fly Rods;"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.";"https://www.example.com/product/RI_9546.html";
```

### Non-standard field delimiter (0x9) — 1 file


#### `file_field_delimiter_0x9.csv`

- **Pollution:** Non-standard field delimiter (0x9)
- **Dialect:** `delimiter='\t'`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE	TIME	Qty	PRODUCTID	Price	ProductType	"ProductDescription"	"URL"	Comments
28/01/2018	00:00	2	MG-8769	$74.69	Men's Waterproof Hiking Boots	"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down."	"https://www.example.com/product/MG_8769.html"	
29/01/2018	00:15	0	RI-3895	$29.81	Light-Up Running Jacket	"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down."	"https://www.example.com/product/RI_3895.html"	
30/01/2018	00:30	1	RI-8070	$80.08	Men's Ventilated Trail Shoes	"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions."	"https://www.example.com/product/RI_8070.html"	
31/01/2018	00:45	1	RI-9546	$25.55	Switch Fly Rods	"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast."	"https://www.example.com/product/RI_9546.html"	
```

### Non-standard quotation character (0x27) — 1 file


#### `file_quotation_char_0x27.csv`

- **Pollution:** Non-standard quotation character (0x27)
- **Dialect:** `delimiter=','`, `quotechar="'"`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,'ProductDescription','URL',Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,'These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.','https://www.example.com/product/MG_8769.html',
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,'The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.','https://www.example.com/product/RI_3895.html',
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,'Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.','https://www.example.com/product/RI_8070.html',
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,'This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.','https://www.example.com/product/RI_9546.html',
```

### Non-standard record delimiter (0xA) — 1 file


#### `file_record_delimiter_0xA.csv`

- **Pollution:** Non-standard record delimiter (0xA)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Non-standard record delimiter (0xD) — 1 file


#### `file_record_delimiter_0xD.csv`

- **Pollution:** Non-standard record delimiter (0xD)
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Preamble rows before header — 1 file


#### `file_preamble.csv`

- **Pollution:** Preamble rows before header
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=2`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
PREAMBLE,,,,,,,,
,,,,,,,,
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
```

### Single data row — 1 file


#### `file_one_data_row.csv`

- **Pollution:** Single data row
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar=''`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",



```

### Two tables with the same number of columns — 1 file


#### `file_multitable_same.csv`

- **Pollution:** Two tables with the same number of columns
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Two tables, first has fewer columns — 1 file


#### `file_multitable_less.csv`

- **Pollution:** Two tables, first has fewer columns
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

### Two tables, first has more columns — 1 file


#### `file_multitable_more.csv`

- **Pollution:** Two tables, first has more columns
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`

**SUT failed to load the file.**

First lines of polluted input:

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance yet light and quick enough to keep feet from feeling weighed down.","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket resists the elements and keeps you visible in low-light conditions. From running, biking or walking the dog, the durable construction and innovative safety features won't let you down.","https://www.example.com/product/RI_3895.html",
30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these amazing ventilated hikers ideal for warm, dry conditions.","https://www.example.com/product/RI_8070.html",
31/01/2018,00:45,1,RI-9546,$25.55,Switch Fly Rods,"This lightweight fly rod delivers outstanding performance and can be used as either a traditional one-handed rod or as a two-handed spey rod. Two-handed technique is ideal for larger rivers and situations where there isn't space for a backcast.","https://www.example.com/product/RI_9546.html",
```

## Wrong Content — 0 files

*(none)*

*(none)*
