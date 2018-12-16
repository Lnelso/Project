import numpy as np
import pandas as pd
import json
import tqdm
import collections

def load_data():
    #read usda mapping
    ing_mapping = json.load(open("../generated/ing_id_mapping.json"))

    #read usda id description
    item_describe = json.load(open("./../generated/usda_id_describe.json"))

    #read cleaned recipes
    cleaned_kaggle_recipes = json.load(open("../generated/clean_kaggle.json"))
    cleaned_cookies_recipes = json.load(open("../generated/clean_cookies.json"))
    cleaned_1m_recipes = json.load(open("../generated/clean_1m.json"))
    cleaned_all_recipes = cleaned_kaggle_recipes+cleaned_cookies_recipes+cleaned_1m_recipes

    #read ingredients count
    ingredients_count = json.load(open("./../generated/ingredients_count.json"))['count']
    
    return ing_mapping, item_describe, cleaned_kaggle_recipes, cleaned_cookies_recipes, cleaned_1m_recipes, cleaned_all_recipes, ingredients_count

def main():
    
    ing_mapping, item_describe, cleaned_kaggle_recipes, cleaned_cookies_recipes, cleaned_1m_recipes, cleaned_all_recipes, ingredients_count = load_data()
    
    #spot collisions
    mapped_ids = [ing_mapping[k] for k in ing_mapping]

    #build dict to store collisions
    collisions = {}

    for m in tqdm.tqdm(ing_mapping) :
        if ing_mapping[m] not in collisions.keys() :
            collisions[ing_mapping[m]] = [m]

        else :
            collisions[ing_mapping[m]].append(m)
            
    #Find representative name for each group
    item_number = 43
    proportion = 0.5

    representative_keys = dict()

    for i, c in tqdm.tqdm(enumerate(collisions)) :

        all_items = " ".join(collisions[c]).split(" ")
        counter = collections.Counter()
        counter.update(all_items)

        #find common names
        common_names = [x[0] for x in counter.most_common() if x[1] > len(collisions[c])*proportion]

        #choose database description
        if len(common_names) == 0 :
            representative_keys[c] = collisions[c][0]

        elif len(common_names) == 1 :
            representative_keys[c] = common_names[0]

        else :
            #determine order

            #case 1, there exist an entry with only wanted words
            exact_match = [x.split(" ") for x in collisions[c] if (len(set(common_names).difference(set(x.split(" "))))== 0)]
            if len(exact_match) != 0 :
                representative_keys[c] = " ".join(exact_match[0])

            #case 2, no exact match
            else :

                all_words_collisions = [x.split(" ") for x in collisions[c] if set(common_names).issubset(set(x.split(" ")))]

                index_tuples = [ (word, index) for collision in all_words_collisions for index, word in enumerate(collision) if (word in common_names)]

                index_counts = np.array([0]*len(common_names))

                #average the relative indices
                for it in index_tuples :
                    word_index = common_names.index(it[0])
                    index_counts[word_index] += it[1]

                index_counts = index_counts

                common_names_ordered = " ".join([common_names[i] for i in np.argsort(index_counts)])
                representative_keys[c] = common_names_ordered
                
    collisions_repr = dict()

    for repr_id in representative_keys :
        repr_name = representative_keys[repr_id]

        if repr_name in collisions_repr.keys() :
            collisions_repr[repr_name] += [repr_id]
        else :
            collisions_repr[repr_name] = [repr_id]
 
    json.dump(collisions_repr, open("../generated/repr_ids.json", 'w'))
    json.dump(representative_keys, open("../generated/id_repr.json" , 'w'))
    
    usda_all_mapped_recipes = []
    usda_any_mapped_recipes = []
    for r in cleaned_all_recipes:
        all_ids_found = True
        founds = list(filter(lambda i: i in ing_mapping.keys(), r))
        found_ids = list(map(lambda i: ing_mapping[i],founds))
        if len(found_ids) == len(r):
            usda_all_mapped_recipes.append(found_ids)
        if len(found_ids) != 0:
            usda_any_mapped_recipes.append(found_ids)

    json.dump(usda_all_mapped_recipes, open("../generated/all_recipes_all_ids.json", 'w'))
    json.dump(usda_any_mapped_recipes, open("../generated/all_recipes_any_ids.json", 'w'))
    

if __name__ == "__main__":
    main()