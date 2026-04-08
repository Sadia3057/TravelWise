import pandas as pd
import numpy as np
import random
import os

random.seed(42)
np.random.seed(42)

# ── Load destinations from Excel ──────────────────────────────────────────────
BASE       = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE, "destinations.xlsx")

if not os.path.exists(EXCEL_PATH):
    raise FileNotFoundError(
        f"destinations.xlsx not found at {EXCEL_PATH}\n"
        "Please place the destinations.xlsx file in the data/ folder."
    )

df_dest = pd.read_excel(EXCEL_PATH, sheet_name="Destinations")
df_dest = df_dest.dropna(subset=["Name"])

destinations = []
for _, row in df_dest.iterrows():
    destinations.append({
        "name":          str(row["Name"]).strip(),
        "type":          str(row["Type"]).strip(),
        "state":         str(row.get("State", "")).strip(),
        "region":        str(row.get("Region", "North")).strip(),
        "accommodation": int(row.get("Accommodation (₹/night)", 1500) or 1500),
        "food":          int(row.get("Food (₹/day)", 500) or 500),
        "entry_fee":     int(row.get("Entry Fee (₹)", 0) or 0),
        "travel_time":   float(row.get("Travel Time (hrs)", 5) or 5),
        "rating":        float(row.get("Rating (out of 5)", 4.0) or 4.0),
    })

print(f"Loaded {len(destinations)} destinations from destinations.xlsx")

# ── Configuration ─────────────────────────────────────────────────────────────
TRIP_TYPES  = ["Solo", "Couple", "Family", "Friends", "Senior"]
TRANSPORTS  = ["Flight", "Train", "Bus", "Car", "Bike"]
SEASONS     = ["Summer", "Winter", "Monsoon", "Spring", "Autumn"]
FROM_CITIES = ["Delhi", "Mumbai", "Kolkata", "Chennai", "Bangalore",
               "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow"]

MULTIPLIERS = {
    "Solo": 1.0, "Couple": 1.7, "Family": 2.5,
    "Friends": 2.0, "Senior": 1.3
}

# ── Generate records ──────────────────────────────────────────────────────────
RECORDS_PER_DEST = 51    # 51 x 99 destinations = ~5049 total records

records = []
for dest in destinations:
    for _ in range(RECORDS_PER_DEST):
        trip_type = random.choice(TRIP_TYPES)
        transport = random.choice(TRANSPORTS)
        season    = random.choice(SEASONS)
        from_city = random.choice(FROM_CITIES)
        num_days  = random.randint(2, 10)

        m          = MULTIPLIERS[trip_type]
        total_cost = (dest["accommodation"] * num_days * m +
                      dest["food"] * num_days * m +
                      dest["entry_fee"])

        if random.random() < 0.6:
            budget   = total_cost * random.uniform(1.05, 2.2)
            feasible = 1
        else:
            budget   = total_cost * random.uniform(0.35, 0.95)
            feasible = 0

        rating = dest["rating"]
        if season == "Monsoon" and dest["type"] == "Beach":
            rating = max(1.0, rating - 0.3)
        if season == "Summer" and dest["type"] == "Hill Station":
            rating = min(5.0, rating + 0.1)

        records.append({
            "destination":        dest["name"],
            "destination_type":   dest["type"],
            "from_location":      from_city,
            "state":              dest["state"],
            "region":             dest["region"],
            "trip_type":          trip_type,
            "transport":          transport,
            "season":             season,
            "num_days":           num_days,
            "budget":             round(budget),
            "accommodation_cost": round(dest["accommodation"] * m),
            "food_cost":          round(dest["food"] * m),
            "entry_fee":          dest["entry_fee"],
            "travel_time":        dest["travel_time"],
            "rating":             round(rating, 1),
            "total_cost":         round(total_cost),
            "feasible":           feasible,
        })

df = pd.DataFrame(records)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

OUTPUT_PATH = os.path.join(BASE, "travel_data.csv")
df.to_csv(OUTPUT_PATH, index=False)

print(f"\nDataset generated : {len(df)} records → travel_data.csv")
print(f"Feasible trips    : {df['feasible'].sum()} ({df['feasible'].mean()*100:.1f}%)")
print(f"Not feasible      : {(df['feasible']==0).sum()} ({(df['feasible']==0).mean()*100:.1f}%)")
print(f"Unique destinations: {df['destination'].nunique()}")
print(f"Columns           : {list(df.columns)}")
print("\nNext step: run train_model.py to retrain the ML model.")