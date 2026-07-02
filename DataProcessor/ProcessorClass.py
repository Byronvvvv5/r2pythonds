# DataProcessor/ProcessorClass.py
import os
import shutil
import pandas as pd
import numpy as np
import sys
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Ellipse

# This tells Python where the root directory of your project is
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)

from Helpers import enforce_numeric_datatype


class ProcessorClass:
    """Base class for shared path setup and file I/O helpers."""

    def __init__(self, current_file):
        module_dir = os.path.dirname(os.path.abspath(current_file))
        self.input_path = os.path.join(module_dir, "input")
        self.output_path = os.path.join(module_dir, "output")
        os.makedirs(self.output_path, exist_ok=True)

    def extract_excel(self, file_name, **kwargs):
        full_path = os.path.join(self.input_path, file_name)
        return pd.read_excel(full_path, **kwargs)

    def extract_csv(self, file_name, **kwargs):
        full_path = os.path.join(self.input_path, file_name)
        return pd.read_csv(full_path, **kwargs)
    
    def extract_txt(self, file_name, **kwargs):
        """
        Encoding should be provided in kwargs if the text file is not in UTF-8.
        e.g.:utf-8
            utf-8-sig
            cp1252
            latin1
        """
        full_path = os.path.join(self.input_path, file_name)
        return pd.read_csv(full_path, sep="\t", **kwargs)

    def load_csv(self, file_name, df, **kwargs):
        """For both comma-separated and semicolon-separated CSV files."""
        os.makedirs(self.output_path, exist_ok=True)
        output_file = os.path.join(self.output_path, file_name)
        df.to_csv(output_file, index=False, **kwargs)
        return output_file

    def load_txt(self, file_name, df, **kwargs):
        """For both tab-separated and space-separated text files."""
        os.makedirs(self.output_path, exist_ok=True)
        output_file = os.path.join(self.output_path, file_name)
        df.to_csv(output_file, index=False, sep="\t", encoding="utf-8-sig", **kwargs)
        return output_file
    
    def load_excel(self, file_name, df, **kwargs):
        os.makedirs(self.output_path, exist_ok=True)
        output_file = os.path.join(self.output_path, file_name)
        df.to_excel(output_file, index=False, **kwargs)
        return output_file

    def copy_output_file(self, file_name, destination_dir):
        os.makedirs(destination_dir, exist_ok=True)
        source_file = os.path.join(self.output_path, file_name)
        destination_file = os.path.join(destination_dir, file_name)
        shutil.copy2(source_file, destination_file)
        return destination_file
    
    def pca_prcomp(self, df, slicing_nr: int = 3):
        """Perform PCA using the sklearn PCA prcomp method in python."""
        df = df.iloc[:, slicing_nr:]
        feature_cols = list(df.columns)
        df = enforce_numeric_datatype(df, (feature_cols))

        # Standardize (prcomp(scale.=TRUE))
        scaler = StandardScaler()
        Xz = scaler.fit_transform(df)

        # PCA (all components)
        pca = PCA()  # or PCA(n_components=0.95) to keep 95% variance
        scores = pca.fit_transform(Xz)  # like prcomp$x

        return pca, scores
    
    def pca_plot_pc1_pc2(self, pca, scores, df, ellipse_identity: str = 'Group', highlight_identity: str = 'SampleID'):
        """Create a PCA plot."""
        # Variance explained
        variance_explained = pca.explained_variance_ratio_

        # Plot PC1 vs PC2
        scores_df = pd.DataFrame({
            'PC1': scores[:, 0],
            'PC2': scores[:, 1],
            'ellipse_identity': df[ellipse_identity],
            'highlight_identity': df[highlight_identity]
        })

        # Convert 'ellipse_identity' to a categorical variable
        scores_df['ellipse_identity'] = pd.Categorical(scores_df['ellipse_identity'])

        # Identify the points with the highest PC1 and PC2 values
        highest_PC1 = scores_df.loc[scores_df['PC1'].idxmax()]
        highest_PC2 = scores_df.loc[scores_df['PC2'].idxmin()]

        # Plot PC1 vs PC2 with improvements
        plt.figure(figsize=(10, 6))
        sns.scatterplot(data=scores_df, x='PC1', y='PC2', hue='ellipse_identity', style='ellipse_identity', s=100, edgecolor='black')

        # Add confidence ellipses for each group
        for group, data in scores_df.groupby('ellipse_identity'):
            cov = np.cov(data[['PC1', 'PC2']].T)
            mean = data[['PC1', 'PC2']].mean()
            ellipse = Ellipse(xy=mean, width=2*np.sqrt(cov[0, 0]), height=2*np.sqrt(cov[1, 1]),
                              edgecolor='black', fc='none')
            plt.gca().add_patch(ellipse)

        # Highlight highest PC1 and lowest PC2 points
        plt.scatter(highest_PC1['PC1'], highest_PC1['PC2'], color='red', label='Highest PC1', edgecolor='black', zorder=5)
        plt.scatter(highest_PC2['PC1'], highest_PC2['PC2'], color='blue', label='Lowest PC2', edgecolor='black', zorder=5)

        # Add labels using the highlight_identity values
        plt.annotate(
            str(highest_PC1['highlight_identity']),
            (highest_PC1['PC1'], highest_PC1['PC2']),
            xytext=(8, 8),
            textcoords='offset points',
            fontsize=9,
            color='red'
        )

        plt.annotate(
            str(highest_PC2['highlight_identity']),
            (highest_PC2['PC1'], highest_PC2['PC2']),
            xytext=(8, -12),
            textcoords='offset points',
            fontsize=9,
            color='blue'
        )

        # Add axis labels with variance explained
        plt.title("PCA")
        plt.xlabel(f"Principal Component 1 ({variance_explained[0]*100:.2f}%)")
        plt.ylabel(f"Principal Component 2 ({variance_explained[1]*100:.2f}%)")

        # Add grid, legend, and theme adjustments
        plt.axvline(0, color='gray', linestyle='--', linewidth=0.8)
        plt.axhline(0, color='gray', linestyle='--', linewidth=0.8)
        plt.grid(True)
        plt.subplots_adjust(right=0.78)
        plt.legend(title= ellipse_identity, loc='upper left', bbox_to_anchor=(1.02, 0.5))
        plt.tight_layout()
        sns.set_style("white")
        
        output_file_name = "PC1_PC2_plot.png"  # Default filename
        output_file_path = os.path.join(self.output_path, output_file_name)
        plt.savefig(output_file_path, dpi=300, bbox_inches='tight')  # Save with high resolution
        plt.show()
 

    