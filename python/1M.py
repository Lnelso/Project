import json
import nltk
import inflect
import tqdm
import time
import requests 
from bs4 import BeautifulSoup as bs
import gensim
import pandas as pd
import urllib.request
import numpy as np
import collections

engine = inflect.engine()
    
def singularize(word):
    ingr = engine.singular_noun(word)
    return word if (not ingr) else ingr

def clean_ing_word(word) : return singularize(word).lower()

def clean_whole_ing(ing) : return " ".join([clean_ing_word(word) for word in ing.split(" ")])

def string_to_float(x) :
    try :
        x = x.split('/')
        if len(x) > 1 :            
            return (float(x[0])/float(x[1]))
        else :
            return float(x[0])
    except :
        raise ValueError("not possible to cast ", x, "to float")
    
def string_to_frac(x) :
    try :
        if '/' in x:
            return string_to_float(x)
        else :
            return(float(x[0]) / float(x[1:]))
    except :
        raise ValueError("not possible to cast ", x, "to float")
    
def fmt_unit(x) :
    return singularize(x.lower())

units = ["bushel", "cup", "dash", "drop", "fl." "oz", "g", "cc", "gram", "gallon", "glass",
    "kg", "liter", "ml", "ounce", "c.", "pinch", "pint", "pound", "lb", "quart",
    "scoop", "shot", "tablespoon", "teaspoon", "tsp", "tbsp"]

def extract_quantity(tags, recipe_index, ingredient_index) : 
    try :
        ingr  = det_ingr[recipe_index]['ingredients'][ingredient_index]['text']
        ingr_first_word = ingr.split(" ")[0]

        if ((len(tags) >= 2) and (tags[0][1] == 'CD')) :

            #nb (nb+ unit) ing
            if ((tags[1][0] == '(') and (len(tags)>6)):
                idx_par = tags.index((')', ')'))            
                quant_in = tags[2:idx_par-1]
                quant=0

                #nb nb 
                if len(quant_in) == 2 :
                    quant = (string_to_float(quant_in[0][0]) + string_to_frac(quant_in[1][0])) / 2
                elif len(quant_in) == 1:
                    quant = string_to_float(quant_in[0][0])

                else :
                    return None

                unit = fmt_unit(tags[idx_par-1][0])            
                return (quant, unit, ingr)


            #nb+ [unit] ing
            else :
                tag1_nb = tags[1][1] == 'CD'
                tag1_to = tags[1][0] == 'to'
                tag1_unit = fmt_unit(tags[1][0]) in units
                tag1_starts_minus = tags[1][0][0] == '-'

                #nb unit ing
                if (tag1_unit) :
                    return (string_to_float(tags[0][0]), fmt_unit(tags[1][0]), ingr)

                #nb nb ...
                elif tag1_nb : 
                    first_nb = string_to_float(tags[0][0]) + string_to_frac(tags[1][0])

                    #nb nb unit ing
                    if fmt_unit(tags[2][0]) in units :
                        return (first_nb, fmt_unit(tags[2][0]), ingr)

                    #nb nb to nb ...
                    elif tags[2][0] == 'to':

                        #nb nb to nb unit ing
                        if fmt_unit(tags[4][0]) in units :
                            return ((first_nb + string_to_float(tags[3][0])) / 2,  fmt_unit(tags[4][0]), ingr)

                        #nb nb to nb nb ...
                        elif tags[4][1] == 'CD' :

                            second_nb = string_to_float(tags[3][0]) + string_to_frac(tags[4][0])
                            average_qt = (first_nb + second_nb) / 2

                            #nb nb to nb nb unit ing
                            if fmt_unit(tags[5][0]) in units :
                                return (average_qt, fmt_unit(tags[5][0]), ingr)

                            #nb nb to nb nb ing
                            else :
                                return (average_qt, "", ingr)

                        #nb nb to nb ing
                        else :
                            return ((first_nb + string_to_float(tags[4][0])) / 2, "", ingr)

                    #nb nb ing
                    else :
                         return (first_nb, "", ingr)   



                #nb -nb ...
                elif tag1_starts_minus :
                    first_nb = (string_to_float(tags[0][0]) + string_to_float(tags[1][0][1:]))/2

                    #nb -nb unit ing
                    if fmt_unit(tags[2][0]) in units :
                        return (first_nb, fmt_unit(tags[2][0]), ingr)

                    #nb -nb ing
                    else :
                        return (first_nb, "", ingr)

                #nb to nb ...
                elif (tag1_to):
                    first_nb = string_to_float(tags[0][0])

                    #nb to nb nb ...
                    if (tags[3][1] == 'CD') :
                        second_nb = string_to_float(tags[2][0]) + string_to_frac([3][0])
                        avg_qt = (first_nb + second_nb) / 2

                        #nb to nb nb unit ing
                        if fmt_unit(tags[4][0]) in units :
                            return (avg_qt, fmt_unit(tags[4][0]), ingr)

                        #nb to nb nb ing
                        else :
                            return (avg_qt, "", ingr)

                    #nb to nb unit ing
                    elif (fmt_unit(tags[3][0]) in units) :
                        second_nb = string_to_float(tags[2][0])
                        avg_qt = (first_nb + second_nb) / 2
                        return (avg_qt, fmt_unit(tags[3][0]), ingr)

                    #nb to nb ing
                    else :
                        second_nb = string_to_float(tags[2][0])
                        avg_qt = (first_nb + second_nb) / 2
                        return (avg_qt, "", ingr)
                #nb ing 
                else :
                    return (string_to_float(tags[0][0]), "", ingr)
    except :
        return None

def init_recipes_valid(recipes, det_ingr):
    usda_no_quant_indices = []
    usda_no_quant = 0
    for index in range(len(recipes)) :
        try :
            det_ingr[index]['valid'].index(False)
        except :
            usda_no_quant += 1
            usda_no_quant_indices.append(index)
    recipes = [recipes[index] for index in usda_no_quant_indices] 
    det_ingr = [det_ingr[index] for index in usda_no_quant_indices]
    
    return recipes, det_ingr

def ingredients_count(recipes, det_ingr):
    # Generate ingredients count
    ingredients_counter = collections.Counter()
    
    for e, recipe in tqdm.tqdm_notebook(enumerate(recipes)) :
        ingredients_counter.update([c['text'] for c in det_ingr[e]['ingredients']])
    
    # Filter the ingredients to keep the most important ones (appear more than 50 times)
    common_ing_counts = []
    thresh=50

    for c in ingredients_counter.most_common() :
        if c[1] >= thresh :
            common_ing_counts.append(c)
        else :
            break
    
    rep_with_ing =[]

    # Rewriting recipes with ingredients
    for e, r in tqdm.tqdm_notebook(enumerate(recipes)) :
        ingredients = []
        for ing_index in range(len(r['ingredients'])) :
            ingredients.append(det_ingr[e]['ingredients'][ing_index]['text'])

        rep_with_ing.append(ingredients)

    json.dump(rep_with_ing, open("../generated/1m_recipes.json", 'w'))
    
    
def main():
    # Load data
    recipes = json.load(open("../data/1M/recipe1M_layers/layer1.json"))
    det_ingr = json.load(open("../data/1M/det_ingr.json"))
    unit_quantities_dict = json.load(open("../generated/1m_unit_quantities.json"))
    
    # Filter recipes with only valid ingredients
    recipes, det_ingr = init_recipes_valid(recipes, det_ingr)
    
    # Generate ingredients count and rewrite recipes with ingredients
    ingredients_count(recipes, det_ingr)
    
    #Extracting quantities for recipes
    measurable_indices = []
    all_extracted = []
    unit_ing = collections.Counter()
    measurables = 0
    nb_to_try = len(recipes)
    sizes = ['large', 'medium', 'small']

    for e, r in tqdm.tqdm_notebook(enumerate(recipes[:nb_to_try])) :

        extracted = []
        contains_immeasurable = False

        for i, ingredient in enumerate(r['ingredients']) :

            #remove sizes        
            ingredient['text'] = " ".join([c for c in ingredient['text'].split(" ") if (not c.lower().strip() in sizes)])

            #tag the ingredient definition
            tags = nltk.pos_tag(nltk.word_tokenize(ingredient['text']))

            raw_ing_to_detect = det_ingr[e]['ingredients'][i]['text']
            ing_to_detect = " ".join([singularize(c) for c in raw_ing_to_detect.split(" ")])

            a = extract_quantity(tags, e, i)

            if a is not None and a[1] != "":
                extracted.append(a)

            else :

                #detect units ingredients
                if ((a is not None) \
                    and (a[1] == "") \
                    and (len(ingredient['text'].split(" ")) > 2) \
                    and (len(ing_to_detect.split(" ")) > 0) \
                    and (singularize(ingredient['text'].split(" ")[1]).strip() == ing_to_detect.split(" ")[0].strip())) :
                    unit_ing.update([ing_to_detect])
                    extracted.append(a)

                else :

                    #detect salt (usually nio quantities)
                    ing_is_salt = ((('salt', 'NN') in tags) or (('salt', 'NNP') in tags) or (('Salt', 'NN') in tags) or (('Salt', 'NNP') in tags)) 

                    if not ing_is_salt :
                        contains_immeasurable = True
                        break
                    elif ing_is_salt :                    
                        extracted.append((2.5, 'g', 'kosher salt'))            
    
    # Recipes with both quantities and usda id for all ingredients
    usda_and_quant_recipes = []

    for r in tqdm.tqdm_notebook(all_extracted) :
        ingredients_entries = []
        all_actually_measurable = True

        for ing in r :
            if ing[1] == "" :
                cleaned_eq = clean_whole_ing(ing[2])

                if cleaned_eq in unit_quantities_dict.keys() :
                    unit_quant = unit_quantities_dict[cleaned_eq]
                    ingredients_entries.append((unit_quant[0], unit_quant[1], ing[2]))

                else :
                    all_actually_measurable = False
                    break
            else :
                ingredients_entries.append(ing)

        if all_actually_measurable :
            usda_and_quant_recipes.append(ingredients_entries)

    json.dump(usda_and_quant_recipes, open("../generated/1m_quant_recipes.json", 'w'))
        
    

if __name__ == "__main__":
    main()