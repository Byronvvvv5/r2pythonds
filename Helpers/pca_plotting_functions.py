import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Ellipse

def pca_plot_pc1_pc2(pca, scores, df, output_path, ellipse_identity: str = 'Group', highlight_identity: str = 'SampleID'):
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
    output_file_path = os.path.join(output_path, output_file_name)
    plt.savefig(output_file_path, dpi=300, bbox_inches='tight')  # Save with high resolution
    plt.show()


