import json
from tqdm import tqdm_notebook
import matplotlib.pyplot as plt
import numpy as np
import inflect
import time
import gensim

engine = inflect.engine()

def singularize(word):
    ingr = engine.singular_noun(word)
    return word if (not ingr) else ingr

def clean_ing_word(word) : return singularize(word).lower()

def clean_whole_ing(ing) : return " ".join([clean_ing_word(word) for word in ing.split(" ")])

def train_model(recipes):
    start_time = time.time()
    model = gensim.models.Word2Vec(recipes, min_count=2)
    time_after_creation = time.time()
    model.train(recipes, total_examples=len(recipes), epochs=25)
    time_after_training = time.time()
    model.save('../generated/food_embeddings.bin')
    time_after_saving = time.time()

def main():
    recipes = json.load(open('../generated/all_recipes_repr.json'))
    train_model(recipes)

if __name__ == "__main__":
    main()