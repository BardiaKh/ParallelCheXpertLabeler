# Parallel CheXpert Labeler

This repository contains scripts to handle the multiprocessing for the CheXpert Labeler. It uses three main Python files: `config.py`, `label_concatenation.py`, `main.py`, and a bash script `label.sh`. The two later python files (`label_concatenation.py`, `main.py`) will be invoked internally and should not be changed.

## Files and Usage

### config.py

This file contains several constants which act as the configuration settings for the processing scripts. Here are the details of these parameters:

- `INPUT_DF_PATH`: Path to the input CSV file which contains the reports.
- `REPORT_COL`: Name of the column that contains the report text in the input CSV file.
- `ID_COLUMN`: Name of the column that will act as a unique identifier for each report.
- `SUPER_CAT_SIZE`: Number of rows to be processed in a single chunk (batch).
- `CHUNK_SIZE`: Number of reports to process in parallel within a super-category.
- `OUTPUT_DF_PATH`: Path where the final concatenated CSV file will be written.
- `CATEGORIES`: List of categories to be labelled by the CheXpert Labeler.

You can modify these constants to fit your needs. The constants are used by the other scripts in the project.

### label.sh

This is a bash script that automates the process of running the `main.py` script multiple times in parallel. The script accepts the number of workers as a command-line argument.

The crucial parameter in this script is `M`, which is calculated as the total number of rows in your dataset divided by the super-category size. 

#### Calculation of `M`


To calculate `M`, simply divide the total number of rows by the super-category size, **make sure you round uo the number**. For example, if you have 123,000 rows in your dataset and you want to process 5000 rows in each super-category, you would do the following:

```bash
# Define total number of rows and super-category size
TOTAL_ROWS=123000
SUPER_CAT_SIZE=5000

# Calculate M using bash and round up
M=$(echo "(($TOTAL_ROWS + $SUPER_CAT_SIZE - 1) / $SUPER_CAT_SIZE)" | bc)

# Print the calculated M value
echo $M
```

In this case, `M` would be 25. After calculating `M`, replace the placeholder in the `label.sh` script with your calculated value:

```bash
...
M=<your calculated value>
...
```

This allows the script to correctly partition your data into manageable chunks for labelling. 

The script first calculates the excluded numbers (i.e., the tasks which are already processed and hence should not be processed again). It then spawns a number of Python processes up to the specified limit, waits for them to finish, and spawns more until all tasks are complete.

You need to run this script from your command line:

```bash
bash label.sh [number_of_workers]
```

Replace `[number_of_workers]` with the number of parallel tasks you want to run. This typically depends on the resources (CPU cores, memory) available on your machine. 

This script will handle all the execution of `main.py` based on the constants set in `config.py`. 

**Example:** To start 40 parallel tasks, run:

```bash
bash label.sh 40
```

### Important Note:

You don't need to run `main.py` or `label_concatenation.py` manually. They are meant to be executed by `label.sh`. 

## Installation

Here are the steps for setting up the environment and required dependencies:

### 1. Clone Repositories

First, clone the required repositories into your working directory.

#### CheXpert Labeler

```bash
git clone https://github.com/stanfordmlgroup/chexpert-labeler.git
```

After cloning, rename the directory for consistency and to follow Python naming conventions:

```bash
mv chexpert-labeler chexpert_labeler
```

#### NegBio

```bash
git clone https://github.com/ncbi-nlp/NegBio.git
```

### 2. Set Python Path

Add the NegBio directory to your PYTHONPATH:

```bash
export PYTHONPATH=$(pwd)/NegBio:$PYTHONPATH
```

### 3. Virtual Environment

Create a virtual environment using the provided `environment.yml` file. You need to have Anaconda or Miniconda installed for this. If you don't have it installed, you can download it [here](https://www.anaconda.com/products/distribution).

```bash
conda env create -f chexpert_labeler/environment.yml
```

After creating the environment, activate it:

```bash
conda activate chexpert-label
```

### 4. Install NLTK Data

Once inside the virtual environment, install the required NLTK data:

```bash
python -m nltk.downloader universal_tagset punkt wordnet
```

### 5. Download the GENIA+PubMed parsing model

After setting up the environment and dependencies, open a Python shell and download the GENIA+PubMed parsing model:

```python
from bllipparser import RerankingParser
RerankingParser.fetch_and_load('GENIA+PubMed')
```

This process might take a while, depending on your internet connection speed.

### 6. Move Labeling Scripts

Move your `label.sh`, `main.py` and `config.py` files into your working directory:

Your final directory structure should look like this:

```bash
.
├── chexpert_labeler/
├── NegBio/
├── config.py
├── label_concatenation.py
├── label.sh
├── main.py
```

Now, you should be all set to run the labeling scripts! Make sure to adjust the constants in `config.py` according to your requirements before running `label.sh`. 

## Contributions

Please feel free to contribute to the improvement of this repository by creating a pull request or opening an issue. Any suggestions or contributions are highly appreciated!