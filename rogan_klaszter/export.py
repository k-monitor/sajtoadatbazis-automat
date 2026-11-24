import pandas as pd
from datasets import load_dataset

# Betöltjük az adathalmazt
dataset = load_dataset('K-Monitor/kmdb_base')
data = dataset['train']

# Szűrjük azokat a cikkeket, amelyekben "Rogán Antal" szerepel
filtered_data = [
    row for row in data
    if "Rogán Antal" in row['persons']
]

# Helper függvény az időbélyeg kezelésére
def extract_month(pub_time):
    return pd.to_datetime(pub_time).strftime('%Y-%m')

# Havi bontáshoz előkészítjük az adatokat
monthly_data = {}
entities = set()

for row in filtered_data:
    month = extract_month(row['pub_time'])

    # Entitások előállítása prefixelve
    persons = [f"person:{person}" for person in row['persons']]
    institutions = [f"institution:{inst}" for inst in row['institutions']]
    places = [f"place:{place}" for place in row['places']]
    others = [f"other:{other}" for other in row['others']]
    files = [f"file:{file}" for file in row['files']]

    # Összes entitás listába gyűjtése
    all_entities = persons + institutions + others + files
    entities.update(all_entities)

    # Hozzáadjuk az entitások előfordulását a hónaphoz
    if month not in monthly_data:
        monthly_data[month] = {}
    for entity in all_entities:
        monthly_data[month][entity] = monthly_data[month].get(entity, 0) + 1

# Minden hónap és entitás biztosítása (üres cellák kezelése)
all_months = pd.date_range(start=min(monthly_data.keys()), end=max(monthly_data.keys()), freq='MS').strftime('%Y-%m')
entities = sorted(entities)

rows = []
for month in all_months:
    row = {'month': month}
    for entity in entities:
        row[entity] = monthly_data.get(month, {}).get(entity, 0)
    rows.append(row)

# Adatok DataFrame-be
output_df = pd.DataFrame(rows)

# CSV exportálása
output_df.to_csv('export.csv', index=False)

print("Az export.csv fájl sikeresen elkészült!")
