import json
import os

DB_FILE = "taskrit_db.json"

def Init():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def Load():
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def Save(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
