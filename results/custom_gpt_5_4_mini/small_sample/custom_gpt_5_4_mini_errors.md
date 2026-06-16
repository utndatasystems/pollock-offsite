# custom_gpt_5_4_mini — small_sample

| | |
|---|---|
| Results file | `results/custom_gpt_5_4_mini/small_sample/custom_gpt_5_4_mini_results.csv` |
| Total files evaluated | 2289 |
| Application errors | 2272 |
| Wrong content | 4 |
| Malformed sidecars | 17 / 2289 |


## Custom Malformed-Row Detection

*Scope: wrong-content files only*

| Metric | Value |
|--------|-------|
| Sidecar reports found | 4 / 4 |
| Files with detected malformed rows | 4 / 4 (100.0%) |
| Total malformed rows logged | 153 |

### Detection by Pollution Type

| Det | Total | % | Type | Rows logged |
|----:|------:|--:|------|------------:|
| 1 | 1 | 100.0% | Extra delimiter | 1 |
| 1 | 1 | 100.0% | Non-standard escape character (0x5C) | 6 |
| 1 | 1 | 100.0% | Non-standard field delimiter (0x2C_0x20) | 73 |
| 1 | 1 | 100.0% | Non-standard quotation character (0x27) | 73 |

### Malformed Row Reasons

| N | Reason |
|--:|--------|
| 51 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10` |
| 20 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11` |
| 20 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11` |
| 19 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12` |
| 19 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12` |
| 7 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 13` |
| 7 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 13` |
| 4 | `UNQUOTED VALUE: Value with unterminated quote found.` |
| 2 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 15` |
| 2 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 13; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 14; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 15` |
| 1 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; UNQUOTED VALUE: Value with unterminated quote found.` |
| 1 | `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; UNQUOTED VALUE: Value with unterminated quote found.` |


## Application Errors — 2272 files

| N | Type |
|--:|------|
| 754 | Extra delimiter |
| 754 | Extra unescaped quote |
| 669 | Missing delimiter |
| 82 | Row uses space as field delimiter |
| 1 | Double trailing newline |
| 1 | Empty file (0 bytes) |
| 1 | Header row only, no data |
| 1 | Missing trailing newline |
| 1 | Multi-row header (2 rows) |
| 1 | No header row |
| 1 | Non-standard record delimiter (0xA) |
| 1 | Non-standard record delimiter (0xD) |
| 1 | Preamble rows before header |
| 1 | Single data row |
| 1 | Two tables with the same number of columns |
| 1 | Two tables, first has fewer columns |
| 1 | Two tables, first has more columns |


### Extra delimiter — 754 files

*Variants: rows 0-83 (84 unique); columns 0-8 (9 unique)*

*Showing 3 example file(s); 751 more under this type.*


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

### Extra unescaped quote — 754 files

*Variants: rows 0-83 (84 unique); columns 0-8 (9 unique)*

*Showing 3 example file(s); 751 more under this type.*


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

### Missing delimiter — 669 files

*Variants: rows 0-83 (84 unique); columns 1-8 (8 unique)*

*Showing 3 example file(s); 666 more under this type.*


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

### Row uses space as field delimiter — 82 files

*Variants: rows 0-2, 4-33, 35-83 (82 unique)*

*Showing 3 example file(s); 79 more under this type.*


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

## Wrong Content — 4 files

| N | Type |
|--:|------|
| 1 | Extra delimiter |
| 1 | Non-standard escape character (0x5C) |
| 1 | Non-standard field delimiter (0x2C_0x20) |
| 1 | Non-standard quotation character (0x27) |


### Extra delimiter — 1 file

*Variants: rows 3 (1 unique); columns 0 (1 unique)*


#### `row_more_sep_row3_col0.csv`

- **Pollution:** Extra delimiter in row 3 at column 0
- **Dialect:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 1**

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: ,30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these ...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```


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
  Got ctd.: n our 8'9"" length fly rod, impeccably designed for her.",https://www.example.com/product/BH_7531.html,
  ```


### Non-standard field delimiter (0x2C_0x20) — 1 file


#### `file_field_delimiter_0x2C_0x20.csv`

- **Pollution:** Non-standard field delimiter (0x2C_0x20)
- **Dialect:** `delimiter=', '`, `quotechar='"'`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 73**

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11`

  ```
  Polluted: 29/01/2018, 00:15, 0, RI-3895, $29.81, Light-Up Running Jacket, "The next level of weather protection. This light-up ...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 30/01/2018, 00:30, 1, RI-8070, $80.08, Men's Ventilated Trail Shoes, "Great grip and super extra breathability make t...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```

- **line 6:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12`

  ```
  Polluted: 13/02/2018, 01:00, 9, CC-9259, $48.00, "Throw Pillow, Wooden Paddles", "Add a pop of paddling fun to your bed, chair ...
  Clean:    13/02/2018,01:00,9,CC-9259,$48.00,"Throw Pillow, Wooden Paddles","Add a pop of paddling fun to your bed, chair or sof...
  ```


*… and 70 more*

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

- **Pollution:** Non-standard quotation character (0x27)
- **Dialect:** `delimiter=','`, `quotechar="'"`, `escapechar='"'`, `row_delimiter='\r\n'`, `encoding='ascii'`, `header_lines=1`, `preamble_lines=0`, `n_columns=9`
- **Sniffed:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`
- **Refined:** `delimiter=','`, `quotechar='"'`, `escapechar='"'`, `row_delimiter=None`, `header_lines=1`, `preamble_lines=0`

**Malformed rows detected: 73**

- **line 3:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11`

  ```
  Polluted: 29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,'The next level of weather protection. This light-up jacket...
  Clean:    29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection. This light-up jacket...
  ```

- **line 4:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10`

  ```
  Polluted: 30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,'Great grip and super extra breathability make these a...
  Clean:    30/01/2018,00:30,1,RI-8070,$80.08,Men's Ventilated Trail Shoes,"Great grip and super extra breathability make these a...
  ```

- **line 6:** `TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 10; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 11; TOO MANY COLUMNS: Expected Number of Columns: 9 Found: 12`

  ```
  Polluted: 13/02/2018,01:00,9,CC-9259,$48.00,'Throw Pillow, Wooden Paddles','Add a pop of paddling fun to your bed, chair or sof...
  Clean:    13/02/2018,01:00,9,CC-9259,$48.00,"Throw Pillow, Wooden Paddles","Add a pop of paddling fun to your bed, chair or sof...
  ```


*… and 70 more*

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
