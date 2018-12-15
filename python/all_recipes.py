import numpy as np
import pandas as pd
import json
from tqdm import tqdm_notebook

def main():
    c = json.load(open('../generated/clean_cookies.json'))
    k = json.load(open('../generated/clean_kaggle.json'))
    m = json.load(open('../generated/clean_1m.json'))
    all_recipes = c+k+m
    json.dump(all_recipes,open('../generated/all_recipes','w'))
    
    all_ingr = []
    for r in all_recipes:
        for i in r:
            all_ingr.append(i)
            
    df_recipe = pd.Series(all_ingr)
    count_table = df_recipe.value_counts().to_frame().rename({0:'count'}, axis = 1)
    
    without_junk = count_table[count_table['count'] > 15]
    without_junk.to_json("../generated/ingredients_count.json")
    count_table.to_json("../generated/ingredients_count_all.json")
    
if __name__ == "__main__":
    main()