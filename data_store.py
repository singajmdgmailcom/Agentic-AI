import os
import json
import requests

DATA_BASE_URL = "https://raw.githubusercontent.com/ksolves/agentic_ai_hackthon_2026_sample_data/main"
DATA_FILES = ["customers.json", "orders.json", "products.json", "tickets.json", "knowledge-base.md"]
DATA_DIR = "data"

db = {
    "customers": [],
    "orders": [],
    "products": [],
    "tickets": [],
    "kb": ""
}

def init_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    for file in DATA_FILES:
        filepath = os.path.join(DATA_DIR, file)
        if not os.path.exists(filepath):
            print(f"Downloading {file}...")
            resp = requests.get(f"{DATA_BASE_URL}/{file}")
            resp.raise_for_status()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(resp.text)
                
    with open(os.path.join(DATA_DIR, "customers.json"), "r", encoding="utf-8") as f:
        db["customers"] = json.load(f)
    with open(os.path.join(DATA_DIR, "orders.json"), "r", encoding="utf-8") as f:
        db["orders"] = json.load(f)
    with open(os.path.join(DATA_DIR, "products.json"), "r", encoding="utf-8") as f:
        db["products"] = json.load(f)
    with open(os.path.join(DATA_DIR, "tickets.json"), "r", encoding="utf-8") as f:
        db["tickets"] = json.load(f)
    with open(os.path.join(DATA_DIR, "knowledge-base.md"), "r", encoding="utf-8") as f:
        db["kb"] = f.read()

def get_order_by_id(order_id):
    for o in db["orders"]:
        if o["order_id"] == order_id:
            return o
    return None

def get_customer_by_email(email):
    for c in db["customers"]:
        if c["email"] == email:
            return c
    return None

def get_product_by_id(product_id):
    for p in db["products"]:
        if p["product_id"] == product_id:
            return p
    return None

def get_all_tickets():
    return db["tickets"]

def get_kb_content():
    return db["kb"]
