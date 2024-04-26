import jsonlines

top_places = dict()
with jsonlines.open('top_places.jsonl') as reader:
    for place in reader:
        top_places[place['name']] = place['category']
with jsonlines.open('connected_places.jsonl', 'w') as writer, jsonlines.open('place_trees.jsonl') as reader:
    for place in reader:
        top_name = place['recursive_name'].split('/')[0]
        place['category'] = top_places[top_name]
        writer.write(place)
