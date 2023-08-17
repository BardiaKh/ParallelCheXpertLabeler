import pandas as pd
import glob
from tqdm import tqdm

from config import REPORT_COL, ID_COLUMN, CATEGORIES, INPUT_DF_PATH, OUTPUT_DF_PATH

processed_files = glob.glob(INPUT_DF_PATH.replace(".csv", "*_labeled.csv"))
processed_files.sort()
final_df = pd.DataFrame()
for file in tqdm(processed_files):
    df = pd.read_csv(file)[[REPORT_COL, ID_COLUMN] + CATEGORIES]
    final_df = pd.concat([final_df, df], ignore_index=True)
    
final_df.to_csv(OUTPUT_DF_PATH, index=False)
