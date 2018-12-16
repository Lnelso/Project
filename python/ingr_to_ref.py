import json

def main():
    ids = json.load(open('../generated/all_recipes_any_ids.json'))
    id2repr = json.load(open('../generated/id_repr.json'))
    
    all_repr = []
    for r in ids:
        ref = list(map(lambda x: id2repr[str(x)],r))
        all_repr.append(ref)
        
    json.dump(all_repr,open('../generated/all_recipes_repr.json', 'w'))

if __name__ == "__main__":
    main()