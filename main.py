
from projects.SYN.DataCleaning.cleaning import Cleaning
from projects.SYN.Preprocessing.imputation import Imputation
from projects.SYN.PCA.PCA import PCAPrcomp
from projects.SYN.ANOVA.ANOVA import ANOVAtests

def SYN_run():
    # First step of this project: Data Cleaning. 
    Cleaning().preprocess()
    # Second step of this project: Imputation. 
    Imputation().run()
    # Third step of this project: performs Principal Components Analysis (PCA) on the imputed dataset and generates PCA plots.
    PCAPrcomp().run()
    # Parallel Third step of this project: performs ANOVA on the imputed dataset 
    ANOVAtests().run()

if __name__ == "__main__":
    SYN_run()