import pandas as pd
import numpy as np
import re
import tqdm
import itertools
import json
import inflect

#take a description-like syntax and return the list of words, filtering  no negation
def split_des_in_list(des) :
    
    cats = re.sub("[()]", "", des).strip().lower().split(',')    
    final_list = []
    
    for c in cats :        
        words_list = c.strip().split(" ")
        
        if (("no" not in words_list) and ("without" not in words_list)) :
            final_list.extend([c.strip().lower() for c in words_list if c != "with"])
    
    return final_list
    
    
#return [w.strip() for c in des.split(",") for w in c.strip().lower().split(' ')]

#singularize a word if plural
def singularize_word(x, engine) :
    if engine.singular_noun(x) :
        return engine.singular_noun(x)
    else :
        return x
        
#clean the description(lowercases, strips, singularization)
def format_long_des(x, engine) :
        
    if str(x) == "nan" :
        return ""    
    
    split = split_des_in_list(x)
    
    #decompose description
    words = [c for c in split]
    
    #singularize words
    sing_words = [singularize_word(x, engine) for x in words]
    
    #rebuild description
    return str(" ".join(sing_words))

def concat_common_and_des(common, des) :
    if common != "" :
        return common.split(" ") + des.split(" ")
    else :
        return des.split(" ")
    
def search_ingredient(ingredient, food_des, engine) :
    
    #do not penalize the presence of those words, 'table' is for the salt
    non_complexificators = set(["fresh", "raw", "skin", "peel", "whole"])
    
    def search_score(categories, ing_words, engine) :
        
        # singularize search words
        ing_words = set([singularize_word(x, engine) for x in ing_words])
        
        #prioritize matching query terms
        nb_matching = len(ing_words.intersection(set(categories)))
        
        #non_complexificators should not be penalized,ignore them AFTER computing number of matching words
        categories = [c for c in categories if (c not in non_complexificators)]
        
        
        #matching keywords one by one 
        matching = [len(set([x]).intersection(ing_words)) != 0 for x in categories]
            
        
        #first keywords are more important
        weights = np.linspace(2, 1, num=len(matching))
        weights = weights / sum(weights)
        
        #the query should have as many ingredients words as possible
        score = (10 * nb_matching) + sum([c[0] * c[1] for c in zip(matching, weights)])
        
        return score
    
    
    ing_words = set(ingredient.split(" "))       
    
    #compute search score for each entry and sort them by score (descending order)
    food_des["search_score"] = food_des["search_words"].apply(lambda x : search_score(x, ing_words, engine))  
    food_des_sorted = food_des.sort_values(by=['search_score'], ascending=False)

    #best score
    result = food_des_sorted[["food_id", "search_words", "search_score"]].head(1)        

    #check if we found a positive score
    if result["search_score"].values[0] != 0 :
        return result, result["search_score"].values[0]
    else :
        return None, 0
    
def change_value(unit, value) :
    
    if unit == 'mg' or unit == 'IU' :
        return value

    elif unit == 'g' :
        return (float(value) / 1000)
    
    else :
        return (float(value) * 1000)

def main():
    food_des_path = "./../data/usda/FOOD_DES.txt"
    food_groups_path = "./../data/usda/FD_GROUP.txt"
    nut_data_path = "./../data/usda/NUT_DATA.txt"
    nut_def_path = "./../data/usda/NUTR_DEF.txt"

    all_paths = [food_des_path, food_groups_path, nut_data_path, nut_def_path]
    
    columns = ["food_group_id", "food_group_name"]
    food_groups = pd.read_csv(food_groups_path, sep="^", encoding="ISO-8859-1", names=columns, header=None)
    food_groups.set_index("food_group_id", inplace=True)
    
    #generate singularization engine
    engine = inflect.engine()

    #columns we want to retrieve from the database files
    columns = ["food_id", "food_group_id", "long_description", "common_names"]
    use_cols = [0, 1, 2, 4]

    #get the info from file
    food_des = pd.read_csv(food_des_path, sep="^", encoding="ISO-8859-1", names=columns, usecols=use_cols, header=None)

    # generate search_words
    food_des['search_words'] = food_des.apply(lambda row : concat_common_and_des(format_long_des(row['common_names'], engine),
                                                                                 format_long_des(row['long_description'], engine)),
                                                                                 axis=1)
    #drop common_names column
    food_des = food_des.drop("common_names", axis=1)
    

    " ".join(search_ingredient("asparagus", food_des, engine)[0]['search_words'].values[0])
    
    
    all_ingredients_ids = {}
    total_ing_count = 0
    mapped_at_least_one_ing_count = 0
    mapped_all_ing_count = 0
    ingredients = json.load(open("../generated/ingredients_count.json"))['count']

    for k, v in tqdm.tqdm(ingredients.items()) :
        #print(k, v)
        cats, score = search_ingredient(k, food_des, engine)
        total_ing_count += v

        if score >= 10 * len(k.split(" ")) :
            mapped_all_ing_count += v
            all_ingredients_ids[k] = int(cats['food_id'].values[0])
                         
        
    #save mapping
    json.dump(all_ingredients_ids, open("../generated/ing_id_mapping.json", 'w'))
    
    
    id_describe = dict()
    high_mapping = all_ingredients_ids
    all_ids = list(set([high_mapping[c] for c in high_mapping]))
    for index in tqdm.tqdm(all_ids) :
        id_describe[index] = food_des[food_des['food_id'] == index]['long_description'].values[0]
    json.dump(id_describe, open("../generated/id_description.json", 'w'))
    
    
    rdi = pd.read_excel("../data/RDI.xlsx")
    rdi_nutrients = rdi['nutrient'].values
    
    use_cols = [0, 1, 2, 3]
    columns = ["nutrient_id", "units", "tagname", "description"]
    nut_def = pd.read_csv(nut_def_path, sep="^", encoding="ISO-8859-1", names=columns, usecols=use_cols, header=None)
    
    
    #try to map rdi elements with database elements automatically
    mapping = {}
    still_unmapped = list(rdi_nutrients)

    for r in rdi_nutrients :

        mapped_count = 0
        sev_des = []

        for des in nut_def['description'].values :
            if ((r in des) or (des in r)) :

                sev_des.append(des)
                mapped_count += 1


        if mapped_count == 1 :
            mapping[r] = sev_des[0]
            still_unmapped.remove(r)
            
    nut_def = nut_def[~(nut_def['tagname'] == 'ENERC_KJ')]
    
    
    # solve conficlts manually
    mapping['Folate'] = "Folate, total"
    mapping['Vitamin A'] = "Vitamin A, RAE"
    mapping['Vitamin D'] = "Vitamin D (D2 + D3)"
    mapping["Vitamin E"] = "Vitamin E (alpha-tocopherol)"
    mapping['Calories'] = "Energy"
    mapping["Monounsaturated fat"] = "Fatty acids, total monounsaturated"
    mapping["Polyunsaturated fat"] = "Fatty acids, total polyunsaturated"
    mapping["Saturated fat"] = "Fatty acids, total saturated"
    mapping['alpha-linoleic acid'] = "Alanine"
    mapping["Vitamin B6"] = "Vitamin B-6"
    mapping["Vitamin B12"] = "Vitamin B-12"
    mapping['Fat'] = "Total lipid (fat)"

    #we do not want to keep the USDA name, change it in the database
    mapping['Linoleic acid'] = "Linoleic acid"
    nut_def["description"] = nut_def["description"].replace("18:2 undifferentiated", "Linoleic acid")



    conflicts_solved = ["Folate", "Vitamin A", "Vitamin D", "Vitamin E", "Saturated fat",
                       "Monounsaturated fat", "Polyunsaturated fat", "alpha-linoleic acid",
                       "Vitamin B6", "Vitamin B12", "Fat", "Linoleic acid"]

    still_unmapped = [su for su in still_unmapped if (su not in conflicts_solved)]
    
    
    # change rdi elements names
    rdi['nutrient'] = rdi['nutrient'].apply(lambda x : mapping[x] if x in mapping.keys() else x)
    rdi = rdi[~(rdi['nutrient'].apply(lambda x : x in still_unmapped))]
    rdi.set_index("nutrient", inplace=True)

    #filter nut_def to keep only mapped elements
    nut_def = nut_def[nut_def['description'].apply(lambda x : x in rdi.index.values)]
    
    new_male_rdis = []
    new_female_rdis = []

    for n in rdi.index.values :
        unit = nut_def[nut_def['description'] == n]['units'].values[0]
        male_rdi = rdi.loc[n]['Male_RDI(19-30)']
        female_rdi = rdi.loc[n]['Female_RDI(19-30)']
        new_male_rdis.append(change_value(unit, male_rdi))
        new_female_rdis.append(change_value(unit, female_rdi))


    #change values
    rdi['Male_RDI(19-30)'] = pd.Series(new_male_rdis).values
    rdi['Female_RDI(19-30)'] = pd.Series(new_female_rdis).values

    #save new RDI file as csv
    rdi.to_csv("./../generated/matching_rdi.csv")
    
    
    use_cols = [0, 1, 2]
    columns = ["food_id", "nutrient_id", "nutr_per_100g"]
    nut_data = pd.read_csv(nut_data_path, sep="^", encoding="ISO-8859-1", names=columns, usecols=use_cols, header=None)

    #drop non-exploitable lines
    nut_data = nut_data[nut_data['nutrient_id'].apply(lambda x : x in nut_def['nutrient_id'].values)]

    #replace id by name to have more convenient reading
    nut_data['nutrient'] = nut_data['nutrient_id'].apply(lambda x : nut_def[nut_def['nutrient_id'] == x]['description'].values[0])
    nut_data = nut_data.drop("nutrient_id", axis=1)
    
    m = json.load(open("./../generated/ing_id_mapping.json"))
    matching_ids = [str(m[k]) for k in m]

    print_bold("length before filtering : " + str(len(nut_data)))

    #apply filtering
    nut_data = nut_data[nut_data['food_id'].apply( lambda x : str(x) in matching_ids)]
    
    nut_data["percentage_male_rdi"] = nut_data.apply(lambda row : 100*row['nutr_per_100g'] / rdi.loc[row['nutrient']]['Male_RDI(19-30)'], axis=1)
    nut_data["percentage_female_rdi"] = nut_data.apply(lambda row : 100*row['nutr_per_100g'] / rdi.loc[row['nutrient']]['Female_RDI(19-30)'], axis=1)
    
    #pivot table
    nut_data = nut_data.pivot(index='food_id', columns='nutrient', values=['nutr_per_100g', 'percentage_male_rdi', 'percentage_female_rdi'])

    #save table using h5 (easier for multi-index table storage)
    nut_data.to_hdf('./../generated/nut_data.h5','table', append=True)
    
if __name__ == "__main__":
    main()