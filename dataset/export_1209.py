import pandas as pd
from collections import Counter
from datasets import load_dataset

# Adathalmaz betöltése
dataset = load_dataset('K-Monitor/kmdb_base')

# Csak a 2024-es adatok szűrése
data_2024 = [item for item in dataset['train'] if item['pub_time'].startswith('2024')]

# Gyakoriságok számítása
def count_entities(data, key):
    counter = Counter()
    for item in data:
        counter.update(item[key])
    return counter

# Leggyakoribb entitások kinyerése (15 mindegyik kategóriából)
top_persons = [f'persons::{entity}' for entity, _ in count_entities(data_2024, 'persons').most_common(15)]
top_institutions = [f'institutions::{entity}' for entity, _ in count_entities(data_2024, 'institutions').most_common(15)]
top_others = [f'others::{entity}' for entity, _ in count_entities(data_2024, 'others').most_common(15)]
top_files = [f'files::{entity}' for entity, _ in count_entities(data_2024, 'files').most_common(15)]

# Hónapok és entitások alapján összesítés
result = {}
all_columns = set(top_persons + top_institutions + top_others + top_files)

for item in data_2024:
    month = item['pub_time'][:7]  # 'YYYY-MM' formátum
    if month not in result:
        result[month] = Counter()
    
    for entity in item['persons']:
        col_name = f'persons::{entity}'
        if col_name in all_columns:
            result[month][col_name] += 1
    
    for entity in item['institutions']:
        col_name = f'institutions::{entity}'
        if col_name in all_columns:
            result[month][col_name] += 1
    
    for entity in item['others']:
        col_name = f'others::{entity}'
        if col_name in all_columns:
            result[month][col_name] += 1
    
    for entity in item['files']:
        col_name = f'files::{entity}'
        if col_name in all_columns:
            result[month][col_name] += 1

# Adatok DataFrame-be rendezése
df = pd.DataFrame.from_dict(result, orient='index').fillna(0).astype(int)
df.index.name = 'Month'

# Üres oszlopok hozzáadása a teljes lista biztosításához
for col in all_columns:
    if col not in df.columns:
        df[col] = 0

# Oszlopok rendezése entitástípus szerint
sorted_columns = (
    sorted([col for col in df.columns if col.startswith('persons::')]) +
    sorted([col for col in df.columns if col.startswith('institutions::')]) +
    sorted([col for col in df.columns if col.startswith('others::')]) +
    sorted([col for col in df.columns if col.startswith('files::')])
)
df = df[sorted_columns]

# CSV exportálása
df.to_csv('export.csv')
print("A fájl exportálása sikeresen megtörtént: export.csv")
