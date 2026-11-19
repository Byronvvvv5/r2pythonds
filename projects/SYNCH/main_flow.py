import pandas as pd
import numpy as np
import os
import sys
import traceback

# This tells Python where the root directory of your project is
basedir = os.path.abspath(__file__)
sys.path.append(basedir)
from Preprocessing import Cleaning
from PCA import PCAPrcomp
from PairedTTests import PairedTTests
from Corelation import Corelation
from Heatmap import CorrelationHeatmap
from Boxplot import Boxplot, ResponderAnalysis

def run():
    """
    This is the main flow of data analyse of Synch project, including 3 different datasets as sources.
    Step 1: Preprocessing: data scale and adding extra info to main dataframe;
            datasets preped for next steps are:
            - cleaned_lipids_treatment_complete, copy to PCA and Corelation modules;
            - cleaned_lipids_anova, currently not active;
            - cleaned_lipids_paired_ttest, copy to PairedTTest module;
    Step 2: PCA analyse on complete lipids dataset, results directly loaded and plotted within Module;
    Step 3: PairedTTest on cleaned lipids dataset, results loaded within Module and copy tp Boxplot;
    Step 4: Boxplot the PairedTTests results plus ResponderAnalysis, images loaded within Module;
    Step 5: Corelation analyse on 
            - copied cleaned lipids dataset
            - new loaded clinic dataset
            results loaded within Module and copy to Heatmap Module;
    Step 6: Heatmap plotting the Corelation results, images loaded within Module;
    """
    steps = [
        ("Step 1: Preprocessing", Cleaning),
        ("Step 2: PCA", PCAPrcomp),
        ("Step 3: PairedTTests", PairedTTests),
        ("Step 4a: Boxplot", Boxplot),
        ("Step 4b: Boxplot responder analysis", ResponderAnalysis),
        ("Step 5: Corelation", Corelation),
        ("Step 6: Heatmap", CorrelationHeatmap),
    ]

    for step_name, step_class in steps:
        print(f"\n===== {step_name} ({step_class.__name__}) =====")
        # Instantiate inside the try: some modules already read input files in __init__
        try:
            step_class().run()
        except Exception as e:
            print(f"\nFAILED at {step_name} ({step_class.__name__}): {type(e).__name__}: {e}\n")
            traceback.print_exc()
            # Later steps depend on this step's output, so stop here
            sys.exit(1)
        print(f"===== {step_name} completed =====")

    print("\nMain flow completed successfully.")


if __name__ == "__main__":
      run()