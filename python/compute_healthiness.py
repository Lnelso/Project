import json
import nltk
import inflect
import tqdm
import time
import requests 
import gensim
import pandas as pd
import urllib.request
import numpy as np
import collections
import json
import clean_recipes_datasets as clean
engine = inflect.engine()

# We convert every quantities units to grams, and delete the recipes that contains unconvertable unit or unmappable ingredients
def recipes_to_usda(quantities_recipes, mapping_usda_id, convert_gr, unit_quantities):
    to_remove = []
    for recipe in tqdm.tqdm_notebook(quantities_recipes):
        failure = False
        for ingr in recipe:
            try:
                ingr[1] = convert_gr[ingr[1]]
                try:
                    ingr[2] = mapping_usda_id[clean.clean_ingredient(ingr[2])]
                except KeyError:
                    failure = True
            except KeyError:
                if(ingr[1] == ""):
                    print("came here")
                    try:
                        ingr[1] = unit_quantities[clean.clean_ingredient(ingr[2])]
                        try:
                            ingr[2] = mapping_usda_id[clean.clean_ingredient(ingr[2])]
                        except KeyError:
                            failure = True
                    except KeyError:
                        failure = True
                else:
                    failure = True
        if(failure):
            to_remove.append(recipe)
    quantities_recipes = [list(map(lambda x: (x[0] * x[1], x[2]), recipe)) for recipe in tqdm.tqdm_notebook(quantities_recipes) if recipe not in to_remove]

    with open('../generated/recipes_quantities_mapped_usda.json', 'w') as outfile:
        json.dump(quantities_recipes, outfile)
    return quantities_recipes


def median_weight_ingredient(quantities_recipes, convert_gr, unit_quantities):
    to_remove = []
    for recipe in tqdm.tqdm_notebook(quantities_recipes):
        failure = False
        for ingr in recipe:
            try:
                ingr[1] = convert_gr[ingr[1]]
                ingr[2] = clean.clean_ingredient(ingr[2])
            except KeyError:
                if(ingr[1] == ""):
                    try:
                        ingr[1] = unit_quantities[clean.clean_ingredient(ingr[2])]
                        ingr[2] = clean.clean_ingredient(ingr[2])
                    except KeyError:
                        failure = True
                else:
                    failure = True
        if(failure):
            to_remove.append(recipe)
    quantities_recipes = [list(map(lambda x: (x[0] * x[1], x[2]), recipe)) for recipe in tqdm.tqdm_notebook(quantities_recipes) if recipe not in to_remove]
    
    ingredient_weight = []
    
    for recipe in tqdm.tqdm_notebook(quantities_recipes):
        for ingredient in recipe:
            ingredient_weight.append(ingredient)
        
    ingredient_weight = np.array(ingredient_weight)
    ingredient_weight_df = pd.DataFrame(ingredient_weight, columns=['weight', 'ingredient'])
    ingredient_weight_df = ingredient_weight_df.astype({'weight': float})
    
    median_weight_by_ingredient_df = ingredient_weight_df.groupby('ingredient').median().reset_index()
    median_weight_by_ingredient_df.to_json('../generated/median_weight_ingredient.json')
        
    return median_weight_by_ingredient_df

def map_one_recipe_usda(recipe, mapping_usda_id, convert_gr, unit_quantities):
    recipe_copy = []
    for ingr in recipe:
        recipe_copy.append(ingr.copy())
    
    failure = False
    for ingr in recipe_copy:
        try:
            ingr[1] = convert_gr[ingr[1]]
            try:
                ingr[2] = mapping_usda_id[clean.clean_ingredient(ingr[2])]
            except KeyError:
                failure = True
        except KeyError:
            if(ingr[1] == ""):
                try:
                    ingr[1] = unit_quantities[clean.clean_ingredient(ingr[2])]
                    try:
                        ingr[2] = mapping_usda_id[clean.clean_ingredient(ingr[2])]
                    except KeyError:
                        failure = True
                except KeyError:
                    failure = True
            else:
                failure = True
            
    if(failure):
        print('Mapping of the recipe has failed.')
        
    recipe_copy = list(map(lambda x: (x[0] * x[1], x[2]), recipe_copy))
    return recipe_copy

def compute_profile(recipe, nutrients_mapping):
    
    nutrients_mapping = nutrients_mapping.reset_index()
    nutrients_mapping = nutrients_mapping.fillna(0.0)
    fat = 0
    sat_fat = 0
    sugar = 0
    salt = 0
    total_weight = 0
    
    for ingr in recipe:
        total_weight += ingr[0]
        view = nutrients_mapping[nutrients_mapping['food_id'] == ingr[1]]['nutr_per_100g'] * (ingr[0] / 100)
        fat += view['Total lipid (fat)'].values[0]
        sat_fat += view['Fatty acids, total saturated'].values[0]
        sugar += view['Sugars, total'].values[0]
        salt += view['Sodium, Na'].values[0] / 1000
                
    ratio = (100 / total_weight)
    return fat * ratio, sat_fat * ratio, sugar * ratio, salt * ratio

def fetch_profile_ingr(ingr, nutrients_mapping):
    nutrients_mapping = nutrients_mapping.reset_index()
    nutrients_mapping = nutrients_mapping.fillna(0.0)
    
    view = nutrients_mapping[nutrients_mapping['food_id'] == ingr[1]]['nutr_per_100g'] * (ingr[0] / 100)
    fat = view['Total lipid (fat)'].values[0]
    sat_fat = view['Fatty acids, total saturated'].values[0]
    sugar = view['Sugars, total'].values[0]
    salt = view['Sodium, Na'].values[0] / 1000
    
    return fat, sat_fat, sugar, salt
    

def score(fat, sat_fat, sugar, salt):
    score_fat = score_cat(fat, 3.0, 17.5)
    score_sat_fat = score_cat(sat_fat, 1.5, 5.0)
    score_sugar = score_cat(sugar, 5.0, 22.5)
    score_salt = score_cat(salt, 0.3, 1.5)
    score_total = {'fat': score_fat,
                   'sat_fat' : score_sat_fat,
                   'sugar' : score_sugar,
                   'salt' : score_salt,
                   'total' : score_fat + score_sat_fat + score_sugar + score_salt}
    return score_total
    
def score_cat(cat, medium, upper):

    medium_y = 3
    upper_y = 25 

    if (cat < medium):
        return cat * medium_y * 1.0 / medium
    
    else :
        slope = 1.0 * (upper_y - medium_y) / (upper - medium)
        if (cat > medium and cat < upper):
            x = cat - medium
            return x * slope + medium_y
        else:
            x = cat - upper
            return x * slope + upper_y
    
def beautiful_print(recipe, mapping_usda_id, nutrients_mapping, convert_gr, unit_quantities):
    total_weight = 0
    mapped_recipe = map_one_recipe_usda(recipe, mapping_usda_id, convert_gr, unit_quantities)
    table_nut = []
    
    for ingr in mapped_recipe:
        total_weight += ingr[0]
        table_nut.append(fetch_profile_ingr(ingr, nutrients_mapping)) 
        
    for e, ingr in enumerate(table_nut):
        weight = (mapped_recipe[e][0] / total_weight) * 100
        print("{:20s}".format(str(recipe[e][2])) + ': ' + "{:10s}".format("{0:5.2f}".format(weight) + '% =>') + ' content(grams): ' + "(fat={0:7.4f}, sat_fat={1:7.4f}, sugar={2:7.4f}, salt={3:.4f})".format(ingr[0], ingr[1], ingr[2], ingr[3]))
        
        
def compute_healthiness(recipe, mapping_usda_id, nutrients_mapping, convert_gr, unit_quantities):
    mapped_recipe = map_one_recipe_usda(recipe, mapping_usda_id, convert_gr, unit_quantities)
    fat, sat_fat, sugar, salt = compute_profile(mapped_recipe, nutrients_mapping)
    score_total = score(fat, sat_fat, sugar, salt)
    beautiful_print(recipe, mapping_usda_id, nutrients_mapping, convert_gr, unit_quantities)
    return score_total
