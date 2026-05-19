!This is not the original readme but an attempt at explaining what is going on from Robin (Student Research Assistant at UTN's Data Systems Lab)


# Running the Benchmark

## 1. Install Dependencies

Make venv, source it and install the packages from requirements.txt
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
## 2. Pollution (skip this if you want to use the default benchmark source file and get comparable scores)
<details>
<summary>
more...
</summary>


Put your csv file file into ```data/<dataset_name>/```

Generate polluted variants (number depends on n_rows + n_cols of your file)

```bash
python3 pollute_main.py --source data/<dataset_name>/<your_csv_file>.csv --output data/<dataset_name>
```
**Note:** The explanations in ```Explanation of the Pollock Benchmark Structure```, the   ```dataset_name``` is ```polluted_files``` as it is the default one used by the original authors. This one is set in the ```.env``` file as the ```$DATASET``` variable default -> scripts default back to ```polluted_files``` if no other dataset name is passed.

</details>

## 3. Run custom SuTs

To run the template for your custom implementation on the same files used by the benchmark:
```
python3 ./sut/custom/custom-bench.py
```
or more generally:
```
DATASET=<dataset_name> python3 ./sut/<sut_name>/<sut_script>.py
```
to run a specific python sut against a custom dataset.

**Note1:** If you rerun this, make sure to **delete the old results output** before.  ```rm -r results/custom/<dataset_name>```.

### Run all python-only SUTs (no docker needed)

<details>
  <summary>more...</summary>

python suts: duckdbauto, duckdbparse, pandas, pycsv, clevercsv

```bash
scripts/run_python_suts.sh <dataset_name>
```

or just
```
scripts/run_python_suts.sh
```
to run on the default (polluted_files) folder in ```./data``` 
</details>

 

### Run all SUTS (Docker needed)

<details>
  <summary>more...</summary>

```
bash benchmark.sh
```
This will take a looong time, especially on the first pass as the docker images are sometimes > 300MB

</details>


## 4. Evaluation

```
python3 evaluate.py --sut <sut> --dataset <dataset_name>
```

evalates all suts if no sut is passed (takes long). dataset defaults to ```polluted_files```

### Take a look at already computed scores

```
python3 scripts/results_tables.py --dataset <dataset>
```  
If you want to get a table of SuTs and their respective scores without having to rerun the evaluate script (which can take some time), run the python file .
**This only works after evaluate has been run once before.**


### Looking at which files were read wrong 


```
python3 scripts/find_errors.py --sut <sut> 
```
This writes a .txt file containing information about what errors the given SUT made


# Getting Started with your own Approach

A template for a custom SuT is provided in ```sut/custom```. Just change the function in ```solution.py``` any way you like or substitute it entirely inside ```custom-bench.py```.
Since only you know what dependencies you need, no docker has been setup yet for this sut.

The score to beat with an automatic inference solution that does not use the provided dialect information is the one by DuckDB-Auto which is currently at: 9.646808 (unweighted). 

Have fun and happy hacking ;)




# Explanation of the Pollock Benchmark Structure 

## 0. Vanilla Benchmark Overview (read first)
1. The polluter writes polluted versions of the ```results/source.csv``` file into ```data/polluted_files/csv/```. It also writes the expected output of files that are read with the correct grammar (which is known by the polluter) into ```data/polluted_files/clean/```. These serve as the basis for comparison with what the SuTs have read from the polluted files later. On top of this, the polluter also writes the dialect information (e.g. delimiter, column datatypes, quote character etc.) into ```data/polluted_files/parameters/```
2. The different SuTs read the files from ```data/polluted_files/csv/```. 
3. The different SuTs write the content of their respective databases/dataframes etc. into ```results/<sut>/polluted_files/loading/``` 
4. The evaluation script ```evaluate.py``` uses Multi-Set operations to compare the outputs of the SuTs (```results/<sut>/polluted_files/loading/```) with the expected clean outputs in (```data/polluted_files/clean/```). It does so on a per-row (record) and per-cell basis. The final score is a mix of loading-success and recall + precision metrics (for formula, see the more detailed explanation of the Evaluation below)


## 1. Pollution - more details

The file ```results/source.csv``` with 83 data rows + a header is the ONLY file that is polluted. 
Every polluted file is derived from ```results/source.csv```.
The file properties were chosen to include various datatypes and a length that matches the median of the survey done on government CSV-files in the Pollock Paper.

The paper describes the pollution process further but basically it works like this:  
**Take the base-dialect of the ```results/source.csv``` file and change things about this dialect. Think: separator, quote character, escape character, header/no header/multi-header.**
Sometimes this is done on a per-line or even per-line + per-column level. The type of pollution is indicated in the filename of the csv file.
**Additionally, it does things like adding additional stray quote characters into fields or leave out a separator**. These pollutions can change what the semantic content of a file is, which is why the benchmark has to save a clean version of each polluted file in ```data/polluted_files/clean/```.


In a few cases, the mapping from a pollution to "What should be the actual expected clean outcome" can be ambiguous. e.g. What is the correct way of parsing a header with 3 rows?

```
col1, col2
col1, col2
col1, col2
```
According to the benchmark, the resulting header should look like this ```"col1 col1 col1", "col2 col2 col2"```. While this is not illogical, it is just a convention and thus up for debates. Who is to say that there should not be ```\n``` or any other delimiter other than spaces between the occurrences of "col1"?

Another example that basically every SuT gets wrong is that the benchmark tries to emulate CSVs with multiple files


## 2 + 3 SuT CSV parsing - more details

Every SuT tries to read the polluted files in ```data/polluted_files/csv/```. After it is read into the SuT, it is dumped to ```results/<sut>/polluted_files/loading/``` using a shared csv-dialect (the one by pandas .to_csv() function).

**Some of the systems (e.g. duckdbparse) are given the dialect** info from ```data/polluted_files/parameters/```, others (e.g. duckdbauto or clevercsv) infer them automatically. In general, the benchmark tried to be a "best effort" benchmark, meaning that the benchmark score directly correlates with the number of settings a given SuT has to deal with different dialects. In general comparisons between SuTs only make sense if they are either both using the supplied metadata (e.g. duckdbparse, sqlite) or not using it at all (e.g. duckdbauto, clevercsv).

This is heavily dockerized (one docker for every SuT) in the default Pollock  [GitHub repo](https://github.com/HPI-Information-Systems/Pollock). Which does not mean it runs for every SuT as many struggle from a pandas<->numpy dependency conflict due to non-pinned versions. This problem is probably fixed by now in this version of the repo. At least for the SuTs that seem useful to re-run, as the already loaded csvs per SuT are already provided in the repo.

## 4 Evaluation - more details

The final Benchmark score is calculated as follows:

```
Score = mean(success)
  + mean(header_precision) + mean(header_recall) + mean(header_f1)
  + mean(record_precision) + mean(record_recall) + mean(record_f1)
  + mean(cell_precision)   + mean(cell_recall)   + mean(cell_f1)
```
Each component is from [0,1], so the maximum score is 10.

The evaluation script writes the scores per file into ```results/<sut>/polluted_files```.

Since not every pollution is equally likely to be found "in the wild", the Pollock score also comes in a weighted variant, which bases its weightings on a survey of governmental csv files done for the Pollock paper. Note: This weighted score is only accurate when using the original ```results/source.csv``` since the number times a pollution is used depends on the row + column counts of the polluted file and the weights are were hardcoded by the authors in ```pollock_weights.json```




# Boring Section:
## Things to note / limitations

1. Some dependency versions were changed compared to the original Pollock Benchmark (e.g. Pandas is now 3.x and not 1.x anymore). This might lead to different scores
2. DuckDB-Auto had a bug where it correctly read datetime but wrote it in a different format than expected by the benchmark, which is why its score in the original repo is lower.
3. Most non-python SuTs require Docker. Their original and mostly broken dependencies were updated and they should run now. However, the score might have moved slightly due to changes in how csvs are parsed between the old and new versions of the suts as some legacy docker containers were not distributed anymore.

