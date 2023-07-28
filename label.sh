#!/bin/bash

# Number of workers. Default is 0 if not specified by the user.
N=${1:-0}

# Python script to run
SCRIPT="./main.py"

# Total number of tasks
M=500

# Starting point
START=0

# Excluded numbers
EXCLUDED_NUMBERS=$(python3 -c "
import os
from config import INPUT_DF_PATH
processed_files = os.listdir('/'.join(INPUT_DF_PATH.split('/')[:-1]))
processed_indices = []
for file in processed_files:
    if file.endswith('labeled.csv'):
        processed_indices.append(str(file.split('_')[-2]))
processed_indices = sorted(processed_indices)
ids = ' '.join(processed_indices)
print(ids)
")

# Count the number of processed files and print it
echo "Number of processed files: $(wc -w <<< "$EXCLUDED_NUMBERS")"

# If N is 0, just exit
if [ "$N" -eq 0 ]; then
    exit 0
fi

declare -A EXCLUDED
IFS=' ' read -r -a EXCLUDED_NUMBERS_ARRAY <<< "$EXCLUDED_NUMBERS"
for num in "${EXCLUDED_NUMBERS_ARRAY[@]}"; do
    EXCLUDED[$num]=1
done

# Function that will kill all running Python processes when this script is terminated
function cleanup {
    echo "Terminating running tasks..."
    for job in "${JOBS[@]}"; do
        if kill -0 $job 2> /dev/null; then
            kill $job
        fi
    done
}

# Register the cleanup function to be called when this script is terminated
trap cleanup SIGINT SIGTERM

# Function that manages the background jobs
function spawn_or_wait {
    local temp_jobs=()
    for job in "${JOBS[@]}"; do
        if kill -0 $job 2> /dev/null; then  # check if process is still running
            temp_jobs+=($job)
        fi
    done
    JOBS=("${temp_jobs[@]}")
}

function spawn_jobs {
    while [[ ${#JOBS[@]} -lt $N && $i -lt $M ]]; do
        if [[ -z "${EXCLUDED[$i]}" ]]; then  # If $i is not in the excluded list
            python $SCRIPT $i &
            JOBS+=($!)
            echo "Progress: Spawned task $(($i + 1)). Total tasks: $M."  # Print the progress
        fi
        i=$((i+1))
    done
}

JOBS=()  # Array to hold background job PIDs
i=$START

spawn_jobs  # Initial spawn

while [[ $i -lt $M || ${#JOBS[@]} -gt 0 ]]; do
    spawn_or_wait
    sleep 1  # To prevent checking job status immediately after spawning
    spawn_jobs  # Try spawning new jobs after checking the already running ones
done

echo "All tasks finished! Concatenating the results..."

python "./label_concatenation.py"

echo "File saved at the 'OUTPUT_DF_PATH' location from the config file!"