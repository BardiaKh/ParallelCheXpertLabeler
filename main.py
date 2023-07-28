import sys
sys.path.append('./NegBio/')
sys.path.append('./chexpert_labeler/')
import re
import bioc
import pandas as pd
import numpy as np
from pathlib import Path
from negbio.pipeline import text2bioc, ssplit
from stages import Extractor, Classifier, Aggregator
from constants import CATEGORIES
from tqdm import tqdm
import argparse

from config import REPORT_COL, INPUT_DF_PATH, SUPER_CAT_SIZE, CHUNK_SIZE

def process_dataframe(df):
    # Escaping quotes and wrapping in quotes (if already not)
    df[REPORT_COL] = df[REPORT_COL].apply(lambda x: x if ((str(x).startswith('"') and str(x).endswith('"')) or (str(x).startswith("'") and str(x).endswith("'"))) else '"{}"'.format(str(x).replace('"', '\\"')))
    
    # Replace multiple dots with single dot and strip leading/trailing whitespaces
    df[REPORT_COL] = df[REPORT_COL].apply(lambda x: re.sub(r"\.{2,}", ".", x).strip())

    # Replace dots that are preceeded by newline with a single dot
    df[REPORT_COL] = df[REPORT_COL].apply(lambda x: re.sub(r"\n\.", ".", x).strip())

    # Now, to split sentences without getting empty ones,
    # we can split on dots that are followed by whitespace or the end of the string:
    df[REPORT_COL] = df[REPORT_COL].apply(lambda x: [i for i in re.split(r'\.(\s|$)', x) if i.strip()])

    # Keep processing until no entries contain 10 or more dots in a row:
    while df[REPORT_COL].str.contains("..........", regex=False).any():
        df[REPORT_COL] = df[REPORT_COL].apply(lambda x: re.sub(r"\.{2,}", ".", x).strip())
        df[REPORT_COL] = df[REPORT_COL].apply(lambda x: re.sub(r"\n\.", ".", x).strip())
        df[REPORT_COL] = df[REPORT_COL].apply(lambda x: [i for i in re.split(r'\.(\s|$)', x) if i.strip()])

    df[REPORT_COL] = df[REPORT_COL].apply(lambda x: x[0])
    return df

def collection_from_list(report_list):
    """Load and clean the reports."""
    collection = bioc.BioCCollection()
    splitter = ssplit.NegBioSSplitter(newline=False)
    assert isinstance(report_list, list), 'report_list must be a list'

    for i, report in enumerate(report_list):
        cleaned_report = process_report(report)
        document = text2bioc.text2document(str(i), cleaned_report)

        split_document = splitter.split_doc(document)

        assert len(split_document.passages) == 1,\
            ('Each document must be given as a single passage.')

        collection.add_document(split_document)

    return collection

def process_report(report):
    """Clean the report text."""
    lower_report = report.lower()
    # Change `and/or` to `or`.
    corrected_report = re.sub('and/or',
                                'or',
                                lower_report)
    # Change any `XXX/YYY` to `XXX or YYY`.
    corrected_report = re.sub('(?<=[a-zA-Z])/(?=[a-zA-Z])',
                                ' or ',
                                corrected_report)
    # Clean double periods
    clean_report = corrected_report.replace("..", ".")
    # Insert space after commas and periods.
    punctuation_spacer = str.maketrans({key: f"{key} "
                                                for key in ".,"})
    clean_report = clean_report.translate(punctuation_spacer)
    # Convert any multi white spaces to single white spaces.
    clean_report = ' '.join(clean_report.split())
    # Remove empty sentences
    clean_report = re.sub(r'\.\s+\.', '.', clean_report)

    return clean_report

def process_chunk(start_idx):
    global df
    global EXTRACTOR
    global CLASSIFIER
    global AGGREGATOR
    end_idx = min(start_idx + CHUNK_SIZE, len(df))
    
    reports = df[REPORT_COL].iloc[start_idx:end_idx].tolist()
    collection = collection_from_list(reports)
    EXTRACTOR.extract(collection)
    # Classify mentions in place.
    CLASSIFIER.classify(collection)
    # Aggregate mentions to obtain one set of labels for each report.
    labels = AGGREGATOR.aggregate(collection)
    
    return start_idx, labels;


if __name__ == "__main__":
    # Parse arguments from command line
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('super_cat_idx', type=int, help='Super category index')
    args = parser.parse_args()

    SUPER_CAT_IDX = args.super_cat_idx

    mention_phrases_dir = Path("./chexpert_labeler/phrases/mention")
    unmention_phrases_dir = Path("./chexpert_labeler/phrases/unmention")
    pre_negation_uncertainty_path = Path("./chexpert_labeler/patterns/pre_negation_uncertainty.txt")
    negation_path = Path("./chexpert_labeler/patterns/negation.txt")
    post_negation_uncertainty_path = Path("./chexpert_labeler/patterns/post_negation_uncertainty.txt")

    EXTRACTOR = Extractor(
        mention_phrases_dir,
        unmention_phrases_dir,
        verbose=False
    )
    CLASSIFIER = Classifier(
        pre_negation_uncertainty_path,
        negation_path,
        post_negation_uncertainty_path,
        verbose=False
    )
    AGGREGATOR = Aggregator(
        CATEGORIES,
        verbose=False
    )
    
    df = pd.read_csv(INPUT_DF_PATH)
    if SUPER_CAT_IDX * SUPER_CAT_SIZE >= len(df):
        print(f"Error: super_cat_idx of {SUPER_CAT_IDX} results in out of bounds access on dataframe.")
        sys.exit(1)
    
    df = df.iloc[SUPER_CAT_IDX * SUPER_CAT_SIZE:min(len(df),(SUPER_CAT_IDX + 1) * SUPER_CAT_SIZE)]
    df = process_dataframe(df)
    df.reset_index(inplace=True, drop=True)
    start_ids = list(range(0, len(df), CHUNK_SIZE))

    results = []
    for start_idx in tqdm(start_ids):
        results.append(process_chunk(start_idx))
        
    for cat in CATEGORIES:
        df[cat] = np.nan
        
    for start_idx, labels in results:
        end_idx = min(start_idx + CHUNK_SIZE, len(df))
        for cat_idx, cat in enumerate(CATEGORIES):
            df.iloc[start_idx:end_idx, df.columns.get_loc(cat)] = labels[:, cat_idx]
            
    df.to_csv(INPUT_DF_PATH.replace(".csv", f"_{SUPER_CAT_IDX}_labeled.csv"), index=False)