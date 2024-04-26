import jsonlines
import csv
import random
from collections import Counter


cats = dict()
places = dict()
l = []

with jsonlines.open('categories.jsonl') as reader:
    for row in reader:
        cats[row['news_id']]=row['category_list']
        l.append(row)

with jsonlines.open('places.jsonl') as reader:
    for row in reader:
        places[row['news_id']]=row['places_list']

print(len(cats))
print(len(places))

with jsonlines.open('cats_and_places.jsonl', 'w') as writer:
    for news_id in cats:
        writer.write({'news_id': news_id, 'cat': cats[news_id], 'places': places[news_id].split(', ') if news_id in places else []})

c = Counter([r['category_list'] for r in l])
print(c.most_common())


cnp = []
with jsonlines.open('cats_and_places.jsonl') as reader:
    for row in reader:
        cnp.append(row)

random.shuffle(cnp)

train = cnp[:45000]
validation = cnp[45000:50000]
test = cnp[50000:55000]

with open('train.csv', mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=train[0].keys())
    writer.writeheader()
    for row in train:
        writer.writerow(row)

with open('val.csv', mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=validation[0].keys())
    writer.writeheader()
    for row in validation:
        writer.writerow(row)

with open('test.csv', mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=test[0].keys())
    writer.writeheader()
    for row in test:
        writer.writerow(row)


