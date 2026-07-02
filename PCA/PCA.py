# Third step of this project: performs Principal Components Analysis (PCA) on the imputed dataset and generates PCA plots.

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Ellipse

# This tells Python where the root directory of your project is
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
from DataProcessor.ProcessorClass import ProcessorClass

from Helpers import enforce_numeric_datatype


class PCAPrcomp(ProcessorClass):
    """This class includes methods for Principal Components Analysis.
    Find orthogonal directions (principal components) that capture maximum variance in the data and project observations onto them."""

    def __init__(self):
        super().__init__(__file__)
        # self.output_copy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'PCA', 'input')

    def pca_plot_variance(self, pca, scores, df):
        """Create a PCA plot."""
        # Variance explained
        variance_explained = pca.explained_variance_ratio_
        cumulative_variance = np.cumsum(variance_explained)
        variance_data = pd.DataFrame({
            'Principal_Component': np.arange(1, len(variance_explained) + 1),
            'Variance_Explained': variance_explained,
            'Cumulative_Variance': cumulative_variance,
        })

        # Plot proportion of variance explained by principal components
        plt.figure(figsize=(8, 6))
        plt.plot(variance_data['Principal_Component'], variance_data['Variance_Explained'], marker='o', linestyle='-')
        plt.title("Proportion of Variance Explained by Principal Components")
        plt.xlabel("Principal Component")
        plt.ylabel("Proportion of Variance Explained")
        plt.grid(True)

        output_file_name = "variance_explained_plot.png"  # Default filename
        output_file_path = os.path.join(self.output_path, output_file_name)
        plt.savefig(output_file_path, dpi=300, bbox_inches='tight')  # Save with high resolution
        plt.show()
    

    def pca_summary(self, pca):
        # Standard deviation, proportion, and cumulative proportion
        sdev = np.sqrt(pca.explained_variance_)
        prop = pca.explained_variance_ratio_
        cumprop = np.cumsum(prop)

        # Combine summary statistics and loadings
        summary = pd.DataFrame(
            {"StdDev": sdev, "Proportion": prop, "Cumulative": cumprop},
            index=[f"PC{i+1}" for i in range(pca.n_components_)]
        )

        return summary
    
    def run(self):
        # Step 0: Load imputed data
        df = self.extract_csv('merged_imputed_output.csv')
        # Step 1: Perform PCA and save result
        pca, scores = self.pca_prcomp(df, slicing_nr=3)
        # Optional, print PCA summary
        summary_df = self.pca_summary(pca)
        self.load_csv(f"PCA_summary_output.csv", summary_df)
        # Step 2: Plot PCA results
        self.pca_plot_variance(pca, scores, df)
        self.pca_plot_pc1_pc2(pca, scores, df, ellipse_identity='Group', highlight_identity='SampleID')

    
if __name__ == "__main__":
    PCAPrcomp().run()
