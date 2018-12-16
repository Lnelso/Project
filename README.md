# Healthier tasty recipes recommender system

# Abstract
The goal of the analysis is to determine what ingredients people like to eat and to discover their underlying combination/association rules (avoid combining mustard and chocolate together) to create new healthy recipes. Those rules would be discovered by using a word embedding algorithm (Word2Vec) on recipes.
Once the rules are discovered, we study the nutritional facts of the ingredients and come up with healthiness profiles, by looking at fat, saturated fat, sugar, salt and energy. The food nutritional facts would be retrieved from the [USDA](https://ndb.nal.usda.gov/ndb/search/list?home=tr) dataset. We then come up with a recommender system that will try to optimize the healthiness of a recipe by swapping unhealthy ingredients fir healthier ones, while preserving tastiness.
Regarding social Impact, the nutrition balance would be an answer to junk food and malnutrition issues across the world, including diabetes and other potentially food-related diseases. Moreover, tastiness would ensure the adoption of the recipes and the actual impact of their creation.

# Dataset
This section enumerates the datasets we are using to do the analysis.

## Determine the rules for tastiness (recipes datasets)
- [Kaggle “whats cooking”](https://www.kaggle.com/c/whats-cooking/data?fbclid=IwAR2RkMMWvBHJUirhgx-f5uB5ZVZ0XmlscS7OWJmuVZHUhDB9r2C8dLv4Bj4) (2Mb) 
- [“From cookies to cook”](infolab.stanford.edu/~west1/from-cookies-to-cooks/) (2.5Gb zipped) 
- [“1M”](http://im2recipe.csail.mit.edu/im2recipe-journal.pdf) (1.4Gb zipped)
The first two datasets contain approximativerly 100,000 recipes and the last one alone has more than a million. These datasets are used to determine ingredient associations. Additionally, we can use the last dataset to parse quantity along with the ingredients, to be used to create healthiness profiles for recipes.

## Determine the healthiness of ingredients (nutritional facts datasets)
- [USDA](https://ndb.nal.usda.gov/ndb/search/list?home=tr) (1.6Gb)
This dataset contains nutritional values for all sorts of ingredients

# Ingredient merging
We first cleaned the ingredients from the datasets and mapped them to existing ids in the USDA nutrition table. Once we did that, we grouped the ids of similar ingredients together by defining a representative ingredient string for the group, that matched the words used in majority in that group. 

# Word Embedding
We used a word embedding algorithm (Word2Vec) to compute similarities between ingredients. Each ingredient is represented as a word and each recipe is a sentence. The algorithm computes similarities as swappability between words. Using that, we can then use the ingredients with high similarity as replacement in the recipe.

# Recommender system
We use the word embedding defined in the previous section to build a recommender system that can optimize the healthiness of a recipe by swapping unhealthy ingredients with healthier ones with high similarity.

# Repository structure
The project report and results notebook acn be found in the milestone 3 folder. The data folder contains raw dataset data (that were small enough, bigger datasts need to be downloaded manually). The generated folder contains intermediate results that were stored for better performance. We included only the files that were small enough. All the other files can be generated with the provided code. The scripts folder contains the python scripts of the project. The notebooks folder contains all the notebooks created for the project. The python scripts are exported notebooks so all the functions are there.
