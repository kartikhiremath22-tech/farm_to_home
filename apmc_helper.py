# apmc_helper.py — save this in your farm_to_home folder (same level as app.py)
import urllib.request
import json
import os

APMC_API_KEY = os.environ.get("APMC_API_KEY", "579b464db66ec23bdd000001986ad256e70648785241fdffc0477a8e")
RESOURCE_ID  = "9ef84268-d588-465a-a308-a864a43d0070"

# Map common product names to Agmarknet commodity names
COMMODITY_MAP = {
    "tomato": "Tomato", "tomatoes": "Tomato",
    "potato": "Potato", "potatoes": "Potato",
    "onion": "Onion", "onions": "Onion",
    "broccoli": "Broccoli",
    "mango": "Mango", "mangoes": "Mango",
    "carrot": "Carrot", "carrots": "Carrot",
    "cabbage": "Cabbage",
    "cauliflower": "Cauliflower",
    "spinach": "Spinach",
    "banana": "Banana", "bananas": "Banana",
    "apple": "Apple", "apples": "Apple",
    "lemon": "Lemon", "lemons": "Lemon",
    "orange": "Orange", "oranges": "Orange",
    "garlic": "Garlic",
    "chilli": "Chilli", "chili": "Chilli",
    "cucumber": "Cucumber",
    "corn": "Maize",
    "wheat": "Wheat",
    "rice": "Rice",
    "grape": "Grapes", "grapes": "Grapes",
}

# Map Indian states to Agmarknet state names
STATE_MAP = {
    "karnataka": "Karnataka",
    "tamil nadu": "Tamil Nadu",
    "maharashtra": "Maharashtra",
    "gujarat": "Gujarat",
    "rajasthan": "Rajasthan",
    "uttar pradesh": "Uttar Pradesh",
    "madhya pradesh": "Madhya Pradesh",
    "andhra pradesh": "Andhra Pradesh",
    "telangana": "Telangana",
    "kerala": "Kerala",
    "punjab": "Punjab",
    "haryana": "Haryana",
    "west bengal": "West Bengal",
    "bihar": "Bihar",
    "odisha": "Odisha",
}

def get_apmc_price(product_name, location):
    """
    Fetch today's APMC modal price for a product in a given location.
    Returns dict with min_price, max_price, modal_price, market, state or None.
    """
    # Find commodity name
    commodity = None
    product_lower = product_name.lower().strip()
    for key, val in COMMODITY_MAP.items():
        if key in product_lower:
            commodity = val
            break
    if not commodity:
        return None

    # Find state from location string
    state = None
    location_lower = location.lower()
    for key, val in STATE_MAP.items():
        if key in location_lower:
            state = val
            break

    # Build API URL
    url = (
        f"https://api.data.gov.in/resource/{RESOURCE_ID}"
        f"?api-key={APMC_API_KEY}"
        f"&format=json"
        f"&limit=5"
        f"&filters[commodity]={commodity}"
    )
    if state:
        url += f"&filters[state]={state}"

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'FarmToHome/1.0',
            'Accept': 'application/json'
        })
        resp = urllib.request.urlopen(req, timeout=8)
        data = json.loads(resp.read().decode())

        records = data.get("records", [])
        if not records:
            return None

        # Get the first record
        r = records[0]
        return {
            "commodity": r.get("commodity", commodity),
            "market":    r.get("market", ""),
            "state":     r.get("state", state or ""),
            "min_price": r.get("min_price", "N/A"),
            "max_price": r.get("max_price", "N/A"),
            "modal_price": r.get("modal_price", "N/A"),
            "arrival_date": r.get("arrival_date", ""),
        }
    except Exception as e:
        print(f"APMC API error: {e}")
        return None
