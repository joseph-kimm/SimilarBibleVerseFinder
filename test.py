import pandas as pd
import random

def create_sample():
    bible_data = pd.read_csv('bible_data_set.csv')
    size = len(bible_data)

    print(sample_data.head())

    random_indices = random.sample(range(size), 100)

    sample_data = bible_data.iloc[random_indices]
    #sample_data.to_csv('sample_bible_data.csv', index=False)

def view_sample():
    sample_data = pd.read_csv('sample_bible_data.csv')
    print(sample_data.head())

if __name__ == "__main__":
    sample_data
   


    

