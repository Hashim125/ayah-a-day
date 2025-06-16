import json
import random
import re

# Load your JSON
with open('ayah-a-day/data/indopak.json', encoding='utf-8-sig') as f:
    data = json.load(f)

print (data)
ayahs = list(data.values())
print (ayahs[1])