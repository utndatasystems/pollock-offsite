Remove:
rm results/duckdbauto/polluted_files/loading/*_converted.csv

My benchmark:
python3 sut/custom/custom-bench.py

Evaluate my benchmark:
python3 evaluate.py --sut custom

Replot:
python3 scripts/results_tables.py

See errors:
python3 scripts/find_errors.py custom

Small bench:
DATASET=small_sample python3 evaluate.py --sut custom --dataset small_sample
