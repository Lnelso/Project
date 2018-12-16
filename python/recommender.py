import tables
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import h5py
from gensim import models
import compute_healthiness as ch
import clean_recipes_datasets as clean
import one_m


# Trained model that is used to compute the similirity between two ingredients
food_embeddings = models.Word2Vec.load('../generated/food_embeddings.bin')

# Dictionary to convert unit (e.g. cup) to an approximate value in gram
conver_gr = json.load(open('../generated/convert_gr.json'))
    
# Nutrients table
nutrients_mapping = pd.read_hdf("../generated/nut_data.h5", 'table')

# Map the id to its representative
id_repr = json.load(open("../generated/id_repr.json"))

# Map a representative to all its id
repr_ids = json.load(open("../generated/repr_ids.json"))

# Dictionary to convert unitary (e.g. 1 lemon) to an approximate value in gram
unit_quantities = json.load(open("../generated/1m_unit_quantities.json"))

mapping_usda_id = json.load(open('../generated/ing_id_mapping.json'))

# Dictionary to convert unit (e.g. cup) to an approximate value in gram
convert_gr = json.load(open('../generated/convert_gr.json'))


#the bigger the better
def health_similarity_score(similarity, health) :
    if health <= 7 :
        return similarity
    else :
        return (similarity**2 / health) 
        

def find_swaps(ing_id, threshold=0.45, nb=1) : 
    
    try :        
        ing_ref = id_repr[str(ing_id)] 
        
    except KeyError:
        print("The ingredient with id", ing_id, "has never been seen before")  
        return None
    
    closest_refs = food_embeddings.wv.most_similar(ing_ref, topn=50)
    
    to_consider = []
    
    closest_refs_and_contains = list(filter(lambda x : (ing_ref     in x[0]) and (x[1] >= threshold), closest_refs))
    closest_refs_not_contains = list(filter(lambda x : (ing_ref not in x[0]) and (x[1] >= threshold), closest_refs))
    
    if len(closest_refs_not_contains) == 0 :
        to_consider = closest_refs_and_contains
    else :
        to_consider = closest_refs_not_contains
        
    if len(to_consider) == 0 :
        return None
    
    else :
        entries = []
        fat, sat_fat, sugar, salt, energy = ch.compute_profile([(100.0, ing_id)], nutrients_mapping)
        base_score = ch.score(fat, sat_fat, sugar, salt, energy)['total']
        for ref in to_consider :
            
            best_id = -1
            best_score = np.inf
            
            for collided_id in repr_ids[ref[0]] :
                fat, sat_fat, sugar, salt, energy = ch.compute_profile([(100.0, collided_id)], nutrients_mapping)

                score = ch.score(fat, sat_fat, sugar, salt, energy)['total']

                if score < best_score :
                    best_id = collided_id
                    best_score = score
            
            
            if (score < base_score) :
                entries.append((ref[0], ref[1], score))
        if len(entries) == 0 :
            return None
        else:
            return sorted(entries, key=lambda x : health_similarity_score(x[1], x[2]), reverse=True)[:nb]
        
        
def find_swapping(recipe) :
    swappings = []
    
    recipe_info = ch.map_one_recipe_usda(recipe, mapping_usda_id, convert_gr, unit_quantities)
    if recipe_info is None :
        print("No swapping found")
    fat, sat_fat, sugar, salt, energy = ch.compute_profile(recipe_info, nutrients_mapping)
    old_score = ch.score(fat, sat_fat, sugar, salt, energy)['total']
    best_score = -1
    best_h_score = 99999
    best_swap = (None, None) 
    
    for e, (quant, ingr) in enumerate(recipe_info) :
        swap = find_swaps(ingr)

        if swap is not None :
            swap = swap[0]
            recipe_copy = [i for i in recipe_info]
            recipe_copy[e] = (recipe_copy[e][0],mapping_usda_id[swap[0]])
            fat, sat_fat, sugar, salt, energy = ch.compute_profile(recipe_copy, nutrients_mapping)
            h_score = ch.score(fat, sat_fat, sugar, salt, energy)['total']
            score = health_similarity_score(swap[1], h_score)
            
            if score > best_score :
                best_h_score = h_score
                best_score = score
                best_swap = (recipe[e][2], swap[0])
                
    new_score = best_h_score
    print('your recipe is',"{:.2f}".format((1-new_score/old_score)*100),'% healthier if you replace',best_swap[0],'with',best_swap[1])
    return best_swap


def find_consecutive_swappings(recipe, nb_swaps=3) :
    recipe_copy = [ing.copy() for ing in recipe]
    swaps = []
    
    for swap_iter in range(nb_swaps) :
        current_swap = find_swapping(recipe)
        swaps.append(current_swap)
        
        #replace ingredient in recipe
        for e, ing in enumerate(recipe) :
            if ing[2] == current_swap[0] :
                recipe[e][2] = current_swap[1]
                
    return swaps, recipe
        
