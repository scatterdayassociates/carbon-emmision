import requests
import pandas as pd

def fetch_pluto_data(address):
    """Fetch PLUTO metadata for a given NYC address"""
    base_url = "https://data.cityofnewyork.us/resource/64uk-42ks.json"
    query = f"?address={address.replace(' ', '%20')}"
    
    try:
        response = requests.get(base_url + query)
        response.raise_for_status()
        data = response.json()

        if not data:
            print("⚠️ No data found for this address.")
            return

        df = pd.DataFrame(data)

        # Extract and display only relevant fields (from the image)
        fields = {
            "lotarea": "Lot Area",
            "bldgarea": "Bldg Area",
            "comarea": "Commercial Area",
            "resarea": "Residential Area",
            "numfloors": "Number of Floors",
            "unitstotal": "Units Total",
            "yearbuilt": "Years Built",
            "bldgclass": "Building Class",
            "landuse": "Land Use",
            "builtfar": "Built Floor Area Ratio",
            "assessland": "Assessed Land Value",
            "assesstot": "Assessed Total Value"
        }

        row = df.iloc[0]

        print("✅ PLUTO Building Information:\n")
        for key, label in fields.items():
            value = row.get(key)
            if pd.isna(value):
                value = "N/A"
            elif isinstance(value, float) and "Value" not in label:
                value = f"{value:.2f}"
            elif "Value" in label or "Area" in label:
                try:
                    value = f"{int(float(value)):,} sq ft" if "Area" in label else f"${int(float(value)):,}"
                except:
                    pass
            print(f"{label}: {value}")

    except Exception as e:
        print(f"❌ Error fetching PLUTO data: {e}")

if __name__ == "__main__":
    print("🔍 NYC PLUTO Building Info Lookup")
    address = input("Enter NYC building address (e.g., 1 Centre Street): ").strip()
    fetch_pluto_data(address)
