# Imports
import re
import csv
import json
import numpy as np
import pandas as pd
import inflect
from tqdm import tqdm

engine = inflect.engine()
    
# File containing keywords to be remove from the ingredients datasets
with open('../data/to_remove.csv', 'r') as f:
    reader = csv.reader(f)
    to_remove = [item.lower() for sublist in list(reader) for item in sublist]

# Remove content of every parenthesis
def remove_par(ingredient):
    return re.sub(r"\([^)]*\)","", ingredient)

# Remove special character
def remove_special_char(ingredient):
    return re.sub(r'/|\n|%|:|\*|\.|#|\"|;| - ' , '', ingredient)

# Remove dangling letters
def remove_letter(ingredient):
    ingredient = re.sub(r'(\A| )s( |\Z)' , ' ', ingredient)
    ingredient = re.sub(r'(\A| )(t|T)( |\Z)' , ' ', ingredient)
    ingredient = re.sub(r'(\A| )c( |\Z)' , ' ', ingredient)
    ingredient = re.sub(r'(\A| )a ' , ' ', ingredient)
    ingredient = re.sub(r'(\A| )g ' , ' ', ingredient)
    return ingredient

# Remove every digit
def remove_number(ingredient):
    return re.sub(r"\d+", '', ingredient)

# Remove the leading whitespaces and the content that follow a comma
def remove_whitespace_comma(ingredient):
    return ingredient.lstrip().split(',')[0]

# Remove every keywords that appear in the to_remove file (essentially quantities, adjectives, ...)
def remove_useless_words(ingredient):
    ingredient_list = ingredient.split(' ')
    ingredient_list = [word for word in ingredient_list if (word not in to_remove)]
    ingredient = ' '.join(ingredient_list)
    return ingredient

# Remove every words ending by -ed
def remove_adjective(ingredient):
    return re.sub(r'\w+ed\s','',ingredient)

# Remove everything that come after a 'or'
def remove_alternative(ingredient):
    return ingredient.split(' or ')[0]

# Remove - sign if it appears at the beginning of the string
def remove_minus(ingredient):
    return re.sub(r'\A-', '', ingredient)

# Remove 'of', 'and' and 'to' when they appear at the beginning of the string
def remove_conjonction(ingredient):
    return re.sub(r'\Aof |\Aand |\Ato ', '', ingredient)

# Convert multi-whitespaces to a single whitespaces, and remove the one that appear at the beginning of a string
def remove_space(ingredient):
    ingredient = re.sub(r'( )+', ' ', ingredient)
    return re.sub(r'\A ', '', ingredient)

# Break strings having multiple ingredients into a list of ingredient
def break_ingredient(ingredient):
    split = ingredient.split(" and ")
    return split

# Apply every cleaning method on a given ingredient, takes the singular form of the noun
def clean_ingredient(ingredient):
    ingredient = remove_par(ingredient)
    ingredient = remove_special_char(ingredient)
    ingredient = remove_number(ingredient)
    ingredient = remove_whitespace_comma(ingredient)
    
    ingredient = ingredient.lower()
    ingredient = remove_useless_words(ingredient)
    ingredient = remove_adjective(ingredient)
    ingredient = remove_alternative(ingredient)
    ingredient = remove_letter(ingredient)
    ingredient = remove_conjonction(ingredient)
    ingredient = remove_minus(ingredient)
    ingredient = remove_space(ingredient)
    if len(ingredient) == 0:
        return ""
    if engine.singular_noun(ingredient):
        return engine.singular_noun(ingredient)
    else:
        return ingredient
    
# Apply the cleaning_ingredient function on a whole dataset (list of ingredients)
def clean_ingredients(ingredients):
    clean_recipe = []
    for ingr in ingredients:
        clean_ingr = clean_ingredient(ingr)
        if clean_ingr:
            clean_recipe.append(clean_ingr)
    
    # Add ingredients that were separated by 'and' in the same string
    new_ingredients = []
    for ingredient in clean_recipe:
        to_add = break_ingredient(ingredient)
        for ingr in to_add:
            new_ingredients.append(ingr)
    clean_recipe = new_ingredients
    
    return clean_recipe

# Apply the cleaning process to the FromCookieToCook dataset
def clean_recipes_cookies(recipes):
    
    def clean_recipe_cookies(recipe):
        ingredients = recipe.split('|')
        return clean_ingredients(ingredients)

    clean_recipes = []
    for recipe in tqdm(recipes):
        clean_recipe = clean_recipe_cookies(recipe)
        if clean_recipe:
            clean_recipe = [x for x in clean_recipe if x != '' or x != '\'' or x != '\\n' or x != ['']]
            if clean_recipe:
                clean_recipes.append(clean_recipe)
    return clean_recipes

# Apply the cleaning process to the Kaggle dataset

def clean_recipes_kaggle(recipes):
    
    def clean_recipe_kaggle(recipe):
        return clean_ingredients(recipe)

    clean_recipes = []
    for recipe in tqdm(recipes):
        clean_recipe = clean_recipe_kaggle(recipe['ingredients'])
        if clean_recipe:
            clean_recipe = [x for x in clean_recipe if x != '' or x != '\'' or x != '\\n' or x != ['']]
            if clean_recipe:
                clean_recipes.append(clean_recipe)
    return clean_recipes


def main():    
    # Fetch the ingredients contained in the ingredients.txt file
    ingredients = open("../data/recipeClean/ingredients.txt", mode='r', buffering=-1, encoding="ISO-8859-1", errors=None, newline=None, closefd=True, opener=None)
    content = ingredients.readlines()

    ids = np.zeros(len(content), dtype=object)
    titles = np.zeros(len(content), dtype=object)
    ingredients = np.zeros(len(content), dtype=object)
    for i in range(len(content)):
        line = content[i].split('\t')
        if len(line) > 4:
            id_recipe, title, ingredient = line[0], line[3], line[4]
            ids[i] = id_recipe
            titles[i] = title
            ingredients[i] = ingredient
        else:
            ids[i] = line[0]
            titles[i] = line[2]
            ingredients[i] = ""
            
    cookies_recipes = ingredients
    cleaned_cookies = clean_recipes_cookies(cookies_recipes)
    
    # Load our dataset into a DataFrame
    ids_titles_recipes_cookies = list(zip(ids, titles, cleaned_cookies))
    ids_titles_recipes_cookies = [x for x in ids_titles_recipes_cookies if (x[2] != [''])]
    ids_clean_cookies = np.array([x[0] for x in ids_titles_recipes_cookies])
    titles_clean_cookies = np.array([x[1] for x in ids_titles_recipes_cookies])
    recipes_clean_cookies = np.array([x[2] for x in ids_titles_recipes_cookies])
    df_cookies = pd.DataFrame({'id': ids_clean_cookies, 'title': titles_clean_cookies, 'recipe': recipes_clean_cookies})
    df_cookies.to_json("../generated/clean_cookies.json")
    
    with open('../data/kaggle/train.json') as f:
        data_train = json.load(f)
    
    with open('../data/kaggle/test.json') as f:
        data_test = json.load(f)
        
    kaggle_recipes = data_train+data_test
    cleaned_kaggle = clean_recipes_kaggle(kaggle_recipes)
    
    # Load our dataset into a DataFrame
    df_kaggle = pd.DataFrame({'recipe':np.array(cleaned_kaggle)})
    df_kaggle = df_kaggle.reset_index().rename({'index' : 'id'}, axis = 1)
    df_kaggle.to_json("../generated/clean_kaggle.json")
    
    with open('../generated/1m_recipes.json') as f:
    data_1m = json.load(f)
    
    cleaned_1m_recipes = []
    for r in tqdm(data_1m):
        clean_recipe = clean_ingredients(r)
        if clean_recipe:
                clean_recipe = [x for x in clean_recipe if x != '' or x != '\'' or x != '\\n' or x != ['']]
                if clean_recipe:
                    cleaned_1m_recipes.append(clean_recipe)
                    
    json.dump(cleaned_1m_recipes,open("../generated/clean_1m.json", 'w'))
    
if __name__ == "__main__":
    main()