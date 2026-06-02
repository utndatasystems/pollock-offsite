#!/bin/bash
# Build the custom _csv C extension.
# Run this from sut/custom/ whenever you change Modules/_csv.c.
set -e

INCLUDES=$(python3-config --includes)
SUFFIX=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))")
OUT="_csv_custom${SUFFIX}"

gcc -shared -fPIC ${INCLUDES} -IModules \
    -O2 -Wall \
    -DPyInit__csv=PyInit__csv_custom \
    Modules/_csv.c \
    -o "${OUT}"

echo "Built ${OUT}"
