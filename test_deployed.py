import requests
import json

URL = "https://vera-bot-p1vc.onrender.com"

# Push category
print("Pushing Category...")
with open('dataset/categories/dentists.json') as f:
    cat = json.load(f)
requests.post(f"{URL}/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat})

# Push merchant
print("Pushing Merchant...")
with open('dataset/expanded/merchants/m_001_drmeera_dentist_delhi.json') as f:
    merch = json.load(f)
# Add category_slug to merchant payload explicitly!
requests.post(f"{URL}/v1/context", json={"scope": "merchant", "context_id": "m_001_drmeera_dentist_delhi", "version": 1, "payload": merch})

# Push trigger
print("Pushing Trigger...")
with open('dataset/expanded/triggers/trg_022_cde_webinar_dentists.json') as f:
    trg = json.load(f)
requests.post(f"{URL}/v1/context", json={"scope": "trigger", "context_id": "trg_022_cde_webinar_dentists", "version": 1, "payload": trg})

# Call tick
print("Calling Tick...")
resp = requests.post(f"{URL}/v1/tick", json={
    "now": "2026-04-26T10:35:00Z",
    "available_triggers": ["trg_022_cde_webinar_dentists"]
})

print(resp.status_code)
print(json.dumps(resp.json(), indent=2))
