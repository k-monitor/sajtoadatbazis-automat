import jsonlines
from sklearn.metrics import accuracy_score

l=[]

with jsonlines.open('cats_and_places.jsonl') as reader:
    for place in reader:
        l.append(place)

#l = [f for f in l if len(f['places']) > 0]

top_places = dict()
with jsonlines.open('top_places.jsonl') as reader:
    for place in reader:
        top_places[place['name']] = place['category']

def to_label(pl):
    if pl == 'magyar-hirek':
        return 0
    if pl == 'eu-hirek':
        return 1
    if pl == 'vilag-hirek':
        return 2
    return 3

predictions = []
labels = [to_label(p['cat']) for p in l]
for p in l:
    is_eu = False
    is_vilag = False
    is_hu = False
    for pl in p['places']:
        if pl in top_places and top_places[pl] == 'v':
            is_vilag = True
        if pl in top_places and top_places[pl] == 'e':
            is_eu = True
        if pl in top_places and top_places[pl] == 'm':
            is_hu = True
    if is_vilag:
        predictions.append(2)
    elif is_eu:
        predictions.append(1)
    elif is_hu:
        predictions.append(0)
    else:
        predictions.append(0)

print(len([f for f in l if f['cat']=='vilag-hirek']))
print(len([f for f in l if f['cat']=='vilag-hirek' and len(f['places'])==0]))

print(len([f for f in l if f['cat']=='eu-hirek']))
print(len([f for f in l if f['cat']=='eu-hirek' and len(f['places'])==0]))

print(len([f for f in l if f['cat']=='magyar-hirek']))
print(len([f for f in l if f['cat']=='magyar-hirek' and len(f['places'])==0]))

print(len(l))
print(len([f for f in l if len(f['places'])==0]))

print(accuracy_score(labels, predictions))
