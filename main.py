import streamlit as st
import pickle
import pandas as pd
import numpy as np
import requests
import warnings
import streamlit.components.v1 as components
import folium
import re
import json
import pandas as pd
from rapidfuzz import process, fuzz
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="NYC Building Energy Predictor",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

def create_synced_map_streetview(latitude, longitude, api_key, address=""):
    """
    Create synchronized map and street view that update together
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
            }}
            .container {{
                display: flex;
                gap: 25px;
                height: 400px;
                padding: 0 12.5px;
                box-sizing: border-box;
            }}
            .map-panel {{
                flex: 1;
            }}
            #map, #streetview {{
                height: 100%;
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="map-panel">
                <div id="map"></div>
            </div>
            <div class="map-panel">
                <div id="streetview"></div>
            </div>
        </div>

        <script>
            let map, marker, streetViewPanorama;
            
            function initMap() {{
                const initialPosition = {{ lat: {latitude}, lng: {longitude} }};
                
                // Initialize the map
                map = new google.maps.Map(document.getElementById("map"), {{
                    zoom: 18,
                    center: initialPosition,
                }});
                
                // Initialize Street View
                streetViewPanorama = new google.maps.StreetViewPanorama(
                    document.getElementById("streetview"), 
                    {{
                        position: initialPosition,
                        pov: {{ heading: 210, pitch: 10 }},
                    }}
                );
                
                // Create draggable marker
                marker = new google.maps.Marker({{
                    position: initialPosition,
                    map: map,
                    draggable: true,
                }});
                
                // Update Street View when marker is dragged
                marker.addListener('dragend', function(event) {{
                    const newPosition = event.latLng;
                    streetViewPanorama.setPosition(newPosition);
                }});
            }}
            
            // Initialize when page loads
            window.onload = initMap;
        </script>
        
        <!-- Load Google Maps JavaScript API -->
        <script async defer 
            src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap">
        </script>
    </body>
    </html>
    """
    return html_content

def get_coordinates(address, api_key):
    """
    Get latitude and longitude from address using Google Geocoding API
    """
    geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': address,
        'key': api_key
    }
    
    try:
        response = requests.get(geocoding_url, params=params)
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            return None, None
    except Exception as e:
        st.error(f"Error fetching coordinates: {e}")
        return None, None

# Enhanced CSS with modern UI/UX improvements
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=SF+Pro+Display:wght@400;500;600;700&display=swap');
    
    /* Global Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
        color: #1f2937;
    }
    
    /* Dashboard Container */
    .main .block-container {
        padding: 40px 30px;
        background-color: #fafbfc;
    }
    
    /* Main Dashboard Header */
    .main-header {
        text-align: center;
        font-size: 32px;
        font-weight: 600;
        margin-bottom: 40px;
        color: #1f2937;
        letter-spacing: -0.02em;
    }
    
    /* Enhanced Card Styles */
    .metric-card {
       background: #ffffff;
    border-radius: 10px;
    padding: 32px 24px;
    text-align: center;
    margin: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    transition: all 0.3s ease;
    border: none;
    position: relative;
    min-height: 270px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }
    
    .metric-card-with-tooltip {
        background: #ffffff;
        border-radius: 10px;
        padding: 24px;
        text-align: center;
        margin: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
        border: none;
        position: relative;
    }
    
    .metric-card-with-tooltip:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }
    
  .metric-title {
    font-size: 28px;
    font-weight: 500;
    color: #64748b;
    margin-bottom: 16px;
    text-align: center;
    letter-spacing: -0.01em;
    line-height: 1.4;
}

.metric-value {
    font-size: 38px;
    font-weight: 700;
    margin: 12px 0;
    color: #1f2937;
    letter-spacing: -0.02em;
}
    
    .metric-unit {
        font-size: 14px;
        color: #64748b;
        font-weight: 400;
        letter-spacing: -0.01em;
    }
    
    /* Tooltip Enhancements */
    .tooltip-container {
        position: relative;
        display: inline-block;
    }
    
    .tooltip-icon {
        font-size: 14px;
        margin-left: 6px;
        color: #0891b2;
        cursor: help;
        transition: color 0.2s ease;
    }
    
    .tooltip-icon:hover {
        color: #0c7489;
    }
    
    .tooltip-text {
        visibility: hidden;
        width: 280px;
        background: #1f2937;
        color: #ffffff;
        text-align: center;
        border-radius: 8px;
        padding: 12px;
        position: absolute;
        z-index: 1000;
        bottom: 130%;
        left: 50%;
        margin-left: -140px;
        opacity: 0;
        transition: all 0.3s ease;
        font-size: 12px;
        line-height: 1.4;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        font-weight: 400;
    }
    
    .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -6px;
        border-width: 6px;
        border-style: solid;
        border-color: #1f2937 transparent transparent transparent;
    }
    
    .tooltip-container:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    
    /* Delta Overlay Enhancements */
    .delta-overlay {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    background: #f8fafc;
    padding: 6px 8px;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    width: fit-content;
    margin-left: auto;
    margin-right: auto;
}

.delta-item {
    display: flex;
    align-items: baseline;
    gap: 4px;
    font-size: 11px;
    white-space: nowrap;
    justify-content: center;
}

.delta-label {
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
}

.delta-value {
    font-size: 12px;
    font-weight: 700;
}

.delta-unit {
    font-size: 10px;
    color: #64748b;
    font-weight: 400;
}
        
    /* Enhanced Expander Styles */
    .streamlit-expanderHeader {
        background: #f8f9fa !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 20px 24px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #1f2937 !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: #f1f5f9 !important;
    }
    
    .streamlit-expanderContent {
        background: #ffffff !important;
        border-radius: 0 0 10px 10px !important;
        padding: 24px !important;
        border: none !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
        margin-bottom: 24px !important;
    }
    
    .streamlit-expander {
        border: none !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
        border-radius: 10px !important;
        margin: 24px 0 !important;
        background: #ffffff !important;
    }
    
    /* Accuracy Card Enhancements */
    .accuracy-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin: 8px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
        border: none;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .accuracy-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    }
    
    .accuracy-value {
        font-size: 22px;
        font-weight: 700;
        margin: 8px 0;
       
        letter-spacing: -0.02em;
    }
    
    .accuracy-label {
        font-size: 12px;
        color: #64748b;
        font-weight: 500;
        line-height: 1.3;
        letter-spacing: -0.01em;
    }
    
    /* PLUTO Section Enhancements */
    .pluto-container {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 28px;
        border-radius: 12px;
        margin: 20px 0;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
    }
    
    .pluto-item {
        font-size: 15px;
        color: #1f2937;
        margin-bottom: 12px;
        line-height: 1.5;
    }
    
    .pluto-label {
        font-weight: 600;
        display: inline;
        color: #374151;
    }
    
    .pluto-value {
        font-weight: 400;
        display: inline;
        color: #1f2937;
    }
    
    .pluto-section-header {
        font-size: 20px;
        font-weight: 600;
        color: #1f2937;
        margin: 28px 0 16px 0;
        border-bottom: 2px solid #0891b2;
        padding-bottom: 8px;
        letter-spacing: -0.01em;
    }
    
    /* Sidebar Enhancements */
    .css-1d391kg {
        background-color: #ffffff;
        padding: 24px 20px;
    }
    
    /* Button Enhancements */
    .stButton > button {
        background: #0891b2;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(8, 145, 178, 0.2);
    }
    
    .stButton > button:hover {
        background: #0c7489;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
    }
    
    /* Spacing improvements */
    .element-container {
        margin-bottom: 20px;
    }
    
    /* Grid layout improvements */
    .row-widget {
        gap: 20px;
    }
</style>
""", unsafe_allow_html=True)

def display_pluto_section_alternative(pluto_data):
    """Alternative approach for displaying PLUTO data"""
    
    left_column_fields = [
        ("lotarea", "Lot Area", "area"),
        ("bldgarea", "Bldg Area", "area"),
        ("comarea", "Commercial Area", "area"),
        ("resarea", "Residential Area", "area"),
        ("numfloors", "Number of Floors", "number"),
        ("unitstotal", "Units Total", "number")
    ]
    
    right_column_fields = [
        ("yearbuilt", "Years Built", "text"),
        ("bldgclass", "Building Class", "text"),
        ("landuse", "Land Use", "text"),
        ("builtfar", "Built Floor Area Ratio", "decimal"),
        ("assessland", "Assessed Land Value", "currency"),
        ("assesstot", "Assessed Total Value", "currency")
    ]
    
    col1, col2 = st.columns(2)
    
    # Left column
    with col1:
        for field_key, field_label, field_type in left_column_fields:
            value = pluto_data.get(field_key)
            formatted_value = format_pluto_value(value, field_type)
            st.write(f"**{field_label}:** {formatted_value}")
    
    # Right column
    with col2:
        for field_key, field_label, field_type in right_column_fields:
            value = pluto_data.get(field_key)
            formatted_value = format_pluto_value(value, field_type)
            st.write(f"**{field_label}:** {formatted_value}")

def format_pluto_value(value, field_type):
    """Format PLUTO values based on field type"""
    if pd.isna(value) or value == "":
        return "N/A"
    
    try:
        if field_type == "area":
            return f"{int(float(value)):,} sq ft"
        elif field_type == "currency":
            return f"${int(float(value)):,}"
        elif field_type == "number":
            return f"{int(float(value)):,}"
        elif field_type == "decimal":
            return f"{float(value):.2f}"
        else:
            return str(value)
    except:
        return str(value)

# Mapping common street suffixes
STREET_SUFFIXES = {
    "st": "STREET",
    "ave": "AVENUE",
    "blvd": "BOULEVARD",
    "rd": "ROAD",
    "dr": "DRIVE",
    "ln": "LANE",
    "ct": "COURT",
    "pl": "PLACE",
    "ter": "TERRACE",
    "e": "EAST",
    "w": "WEST",
    "n": "NORTH",
    "s": "SOUTH"
}

import re

def normalize_street_address(address):
    # Step 1: Get the part before the first comma (e.g., "214 W 15th St")
    street_part = address.split(',')[0].strip().lower()

    # Step 2: Convert "15th", "1st", "2nd", "3rd", etc. to "15", "1", etc.
    street_part = re.sub(r'\b(\d+)(st|nd|rd|th)\b', r'\1', street_part)

    # Step 3: Tokenize and expand suffixes
    tokens = street_part.split()
    normalized_tokens = [STREET_SUFFIXES.get(token, token).upper() for token in tokens]

    return " ".join(normalized_tokens)


def fetch_pluto_data(address=None, csv_path="Primary_Land_Use_Tax_Lot_Output__PLUTO__20250723.csv"):
    if address is None:
        return None

    normalized_input = normalize_street_address(address)
    print(f"Normalized Input: {normalized_input}")
    chunk_size = 10000  # adjust based on memory
    for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
        # Ensure address column exists
        if 'address' not in chunk.columns:
            raise KeyError("'address' column not found in the CSV")

        # Normalize chunk addresses
        chunk['address'] = chunk['address'].astype(str).str.strip().str.upper()

        # Compare
        match = chunk[chunk['address'] == normalized_input]
        if not match.empty:
            print(f"✅ Match found for '{normalized_input}'")
            return match.iloc[0].to_dict()

    print(f"❌ No match found for: '{normalized_input}'")
    return None

def engineer_features(df):
    """Create the same engineered features used during training"""
    df = df.copy()
    
    # Building age and age categories
    current_year = 2024
    df['building_age'] = current_year - df['year_built']
    df['age_category'] = pd.cut(df['building_age'], 
                              bins=[0, 20, 40, 60, 100], 
                              labels=['New', 'Modern', 'Mature', 'Old'])
    
    # Energy efficiency ratios
    df['total_energy_use'] = df['electricity_use_kbtu'] + df['natural_gas_use_kbtu']
    df['energy_per_sqft'] = df['total_energy_use'] / df['building_gross_floor_area_ft2']
    
    # Handle division by zero for energy ratios
    df['electricity_ratio'] = np.where(df['total_energy_use'] > 0, 
                                     df['electricity_use_kbtu'] / df['total_energy_use'], 0)
    df['gas_ratio'] = np.where(df['total_energy_use'] > 0,
                             df['natural_gas_use_kbtu'] / df['total_energy_use'], 0)
    
    # Building size categories
    df['size_category'] = pd.cut(df['building_gross_floor_area_ft2'],
                               bins=[0, 10000, 50000, 100000, float('inf')],
                               labels=['Small', 'Medium', 'Large', 'XLarge'])
    
    # Occupancy efficiency
    df['occupancy_efficiency'] = df['occupancy_percent'] / 100 * df['energy_per_sqft']
    
    # Climate zone proxy (borough-based)
    borough_climate = {
        'MANHATTAN': 'Dense_Urban',
        'BROOKLYN': 'Urban',
        'QUEENS': 'Suburban',
        'BRONX': 'Urban',
        'STATEN ISLAND': 'Suburban'
    }
    df['climate_zone'] = df['borough'].map(borough_climate)
    
    # Property type efficiency proxy
    efficient_types = ['Office', 'Medical Office', 'Bank Branch']
    df['is_efficient_type'] = df['primary_property_type'].isin(efficient_types).astype(int)
    
    # Multi-building complexity
    df['is_multi_building'] = (df['number_of_buildings'] > 1).astype(int)
    df['complexity_score'] = df['number_of_buildings'] * df['building_gross_floor_area_ft2'] / 10000
    
    return df

@st.cache_data
def load_model(model_file='nyc_building_predictor.pkl'):
    """Load the pre-trained model"""
    try:
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
        return model_data
    except FileNotFoundError:
        st.error(f"❌ Model file '{model_file}' not found! Make sure you've trained and saved a model first.")
        return None
    except Exception as e:
        st.error(f"❌ Error loading model: {e}")
        return None

def make_prediction(model_data, input_data):
    """Make prediction using the loaded model"""
    try:
        # Convert input to DataFrame
        if isinstance(input_data, dict):
            df = pd.DataFrame([input_data])
        else:
            df = pd.DataFrame(input_data)
        
        # Engineer features
        df = engineer_features(df)
        
        # Get all feature columns that the model expects
        input_features = model_data['input_features']
        additional_numerical = [
            'building_age', 'total_energy_use', 'energy_per_sqft',
            'electricity_ratio', 'gas_ratio', 'occupancy_efficiency',
            'complexity_score'
        ]
        
        additional_categorical = [
            'age_category', 'size_category', 'climate_zone', 'is_efficient_type', 'is_multi_building'
        ]
        
        # Select all features that the model expects
        feature_columns = input_features + additional_numerical + additional_categorical
        X_pred = df[feature_columns]
        
        # Make prediction
        model = model_data['model']
        prediction = model.predict(X_pred)
        
        # Format results
        results = {}
        target_variables = model_data['target_variables']
        for i, target in enumerate(target_variables):
            results[target] = float(prediction[0][i])
        
        return results
        
    except Exception as e:
        st.error(f"❌ Error during prediction: {e}")
        return None

def display_metric_card(title, value, unit="", col_width=1):
    """Display a metric card"""
    return f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value:,.0f}</div>
        <div class="metric-unit">{unit}</div>
    </div>
    """

def display_metric_card_net(title, value, unit="", col_width=1):
    """Display a metric card"""
    return f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value:,.0f}</div>
        <div class="metric-unit">{unit}</div>
    </div>
    """
def display_metric_card_national(title, value, unit="", property_type="", absolute_delta=0, percent_delta=0, col_width=1):
    """Display a metric card with tooltip and delta values"""
    tooltip_text = f"National median Site EUI for {property_type} buildings – Portfolio Manager (CBECS 2018)."
    
    # Format the value properly
    if isinstance(value, (int, float)) and value != "N/A":
        formatted_value = f"{value:,.0f}"
        show_delta = True
    else:
        formatted_value = str(value)
        show_delta = False
    
    # Format delta values only if we have a numeric value
    if show_delta:
        delta_sign = "+" if absolute_delta >= 0 else ""
        delta_color = "#ef4444" if absolute_delta > 0 else "#10b981" if absolute_delta < 0 else "#64748b"
        delta_html = f'''<div class="delta-overlay">
            <div class="delta-item">
                <span class="delta-label">Δ</span>
                <span class="delta-value" style="color: {delta_color};">{delta_sign}{absolute_delta:.1f}</span>
                <span class="delta-unit">{unit}</span>
            </div>
            <div class="delta-item">
                <span class="delta-label">Δ%</span>
                <span class="delta-value" style="color: {delta_color};">{delta_sign}{percent_delta:.1f}%</span>
            </div>
        </div>'''
    else:
        delta_html = ""
    
    return f"""
    <div class="metric-card-with-tooltip">
        <div class="metric-title">
            {title} 
            <span class="tooltip-container">
                <span class="tooltip-icon">ℹ️</span>
                <span class="tooltip-text">{tooltip_text}</span>
            </span>
        </div>
        <div class="metric-content">
            <div class="metric-value">{formatted_value}</div>
            <div class="metric-unit">{unit}</div>
            {delta_html}
        </div>
    </div>
    """

def display_accuracy_card(title, value, unit=""):
    """Display an accuracy metric card"""
    return f"""
    <div class="accuracy-card">
        <div class="accuracy-value">{value}</div>
        <div class="accuracy-label">{title}</div>
    </div>
    """

def display_accuracy_metrics():
    """Display accuracy metrics using Streamlit columns"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(display_accuracy_card("R-Squared<br>Site Energy Use", "0.8566"), unsafe_allow_html=True)
    
    with col2:
        st.markdown(display_accuracy_card("Mean Absolute Error<br>Site Energy Use", "5,078"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(display_accuracy_card("Root Mean Squared Error<br>Site Energy Use", "26,649"), unsafe_allow_html=True)

# Function to load median data
def load_median_data(median_file_path='median.json'):
    """Load median reference data from JSON file"""
    try:
        import json
        with open(median_file_path, 'r') as f:
            median_data = json.load(f)
        return median_data
    except Exception as e:
        st.error(f"Error loading median data: {e}")
        return None

# Function to map property type to portfolio manager function
def map_property_type_to_portfolio_function(property_type):
    """Map primary property type to portfolio manager primary function"""
    # Create mapping dictionary (you may need to adjust these mappings based on your data)
    property_mapping = {
        "Bank Branch": "bank branch",
        "Distribution Center": "distribution center",
        "Enclosed Mall": "enclosed mall",
        "Hospital (General Medical & Surgical)": "hospital",
        "Hotel": "hotel",
        "K-12 School": "k-12 school",
        "Laboratory": "laboratory",
        "Manufacturing/Industrial Plant": "manufacturing/industrial plant",
        "Medical Office": "medical office",
        "Mixed Use Property": "mixed use property",
        "Multifamily Housing": "multifamily housing",
        "Non-Refrigerated Warehouse": "non-refrigerated warehouse",
        "Office": "office",
        "Other - Lodging/Residential": "other - lodging/residential",
        "Outpatient Rehabilitation/Physical Therapy": "outpatient rehabilitation/physical therapy",
        "Parking": "parking",
        "Performing Arts": "performing arts",
        "Refrigerated Warehouse": "refrigerated warehouse",
        "Repair Services (Vehicle, Shoe, Locksmith, etc.)": "repair services",
        "Residence Hall/Dormitory": "residence hall/dormitory",
        "Residential Care Facility": "residential care facility",
        "Retail Store": "retail store",
        "Self-Storage Facility": "self-storage facility",
        "Supermarket/Grocery Store": "supermarket/grocery store",
        "Transportation Terminal/Station": "transportation terminal/station",
        "Worship Facility": "worship facility"
    }
    
    return property_mapping.get(property_type, property_type.lower())

def get_median_value_for_property_type(median_data, property_type):
    """Get median site EUI value for a specific property type"""
    if not median_data:
        return None
    
    # Map the property type to portfolio function
    portfolio_function = map_property_type_to_portfolio_function(property_type)
    
    # Search through median_data (assuming it's a list of dictionaries or a single dictionary)
    if isinstance(median_data, list):
        for entry in median_data:
            if entry.get('portfolio_manager_primary_function', '').lower() == portfolio_function.lower():
                return entry.get('site_eui_kbtu_ft2')
    elif isinstance(median_data, dict):
        if median_data.get('portfolio_manager_primary_function', '').lower() == portfolio_function.lower():
            return median_data.get('site_eui_kbtu_ft2')
    
    # If no match found, return None or a default value
    return None

# Main app
def main():
    st.markdown('<h1 class="main-header">Property Carbon Emission Profile</h1>', unsafe_allow_html=True)
    
    # Property type options
    property_types = [
        "Bank Branch", "Distribution Center", "Enclosed Mall", 
        "Hospital (General Medical & Surgical)", "Hotel", "K-12 School", 
        "Laboratory", "Manufacturing/Industrial Plant", "Medical Office", 
        "Mixed Use Property", "Multifamily Housing", "Non-Refrigerated Warehouse", 
        "Office", "Other - Lodging/Residential", 
        "Outpatient Rehabilitation/Physical Therapy", "Parking", 
        "Performing Arts", "Refrigerated Warehouse", 
        "Repair Services (Vehicle, Shoe, Locksmith, etc.)", 
        "Residence Hall/Dormitory", "Residential Care Facility", 
        "Retail Store", "Self-Storage Facility", "Supermarket/Grocery Store", 
        "Transportation Terminal/Station", "Worship Facility"
    ]
    
    # Borough options with emojis
    borough_options = {
        "Bronx": "Bronx",
        "Brooklyn": "Brooklyn", 
        "Manhattan": "Manhattan",
        "Queens": "Queens",
        "Staten Island": "Staten Island"
    }
    
    # Sidebar inputs
    st.sidebar.title("Building Parameters")

    st.sidebar.subheader("Address")
    address = st.sidebar.text_input(
    "Enter Building Address",
    placeholder="123 Main Street, City, Country"
    )
    
    # Building section
    st.sidebar.subheader("Building")
    building_area = st.sidebar.number_input(
        "Building Gross Floor Area (ft²)", 
        min_value=1, 
        max_value=1000000, 
        value=50000,
        step=1000
    )
    
    primary_property_type = st.sidebar.selectbox(
    "Primary Property Type", 
    property_types, 
    index=property_types.index("Office")
)
    
    year_built = st.sidebar.slider(
        "Year Built", 
        min_value=1880, 
        max_value=2025, 
        value=1990,
        step=1
    )
    
    # Operations section
    st.sidebar.subheader("Operations")
    occupancy_percent = st.sidebar.slider(
        "Occupancy (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=75.0,
        step=0.1
    )
    
    number_of_buildings = st.sidebar.number_input(
        "Number of Buildings", 
        min_value=1, 
        max_value=25, 
        value=1,
        step=1
    )
    
    # Loads section
    st.sidebar.subheader("Loads")
    electricity_use = st.sidebar.number_input(
        "Electricity Use (kBtu)", 
        min_value=0, 
        max_value=50000000, 
        value=1000000,
        step=1000,
        format="%d"
    )
    
    natural_gas_use = st.sidebar.number_input(
        "Natural Gas Use (kBtu)", 
        min_value=0, 
        max_value=50000000, 
        value=500000,
        step=1000,
        format="%d"
    )
    
    # Environment section
    st.sidebar.subheader("Environment")
    weather_normalized_eui = st.sidebar.number_input(
        "Weather-Normalized Site EUI (kBtu/ft²)", 
        min_value=1.0, 
        max_value=1000.0, 
        value=100.0,
        step=0.1,
        help="Energy Use Intensity normalized for weather conditions"
    )
    
    # Context section
    st.sidebar.subheader("Context")
    selected_borough = st.sidebar.selectbox(
        "Borough", 
        list(borough_options.keys()),
        index=list(borough_options.keys()).index("Manhattan"),
        format_func=lambda x: borough_options[x]
    )
    
    construction_status = st.sidebar.radio(
        "Construction Status", 
        ["Existing", "Major Renovation", "Proposed"],
        index=0
    )
    
    # Predict button
    st.sidebar.markdown("---")
    predict_button = st.sidebar.button(
        "Predict Property Emission", 
        type="primary",
        use_container_width=True
    )
    
    # Create building data dictionary
    building_data = {
        'building_gross_floor_area_ft2': building_area,
        'primary_property_type': primary_property_type,
        'year_built': year_built,
        'occupancy_percent': occupancy_percent,
        'number_of_buildings': number_of_buildings,
        'electricity_use_kbtu': electricity_use,
        'natural_gas_use_kbtu': natural_gas_use,
        'weather_normalized_site_eui_kbtu_ft2': weather_normalized_eui,
        'borough': selected_borough.upper(),
        'construction_status': construction_status
    }
    
    # Only make prediction when button is clicked
    if predict_button:
        with st.spinner('Analyzing building data and predicting emissions...'):
            # Load model and make prediction
            model_data = load_model('nyc_building_predictor.pkl')
            median_data = load_median_data('median.json')
            if model_data is not None:
                prediction = make_prediction(model_data, building_data)
            else:
                prediction = None
        
        if prediction:
            # Display main prediction cards using actual model predictions
            median_site_eui = get_median_value_for_property_type(median_data, primary_property_type)
            col1, col2 = st.columns(2)
            
            with col1:
                # Site Energy Use - try to get from prediction first
                site_energy_key = next((k for k in prediction.keys() if 'site' in k.lower() and 'energy' in k.lower()), None)
                if site_energy_key:
                    site_energy_value = prediction[site_energy_key]/building_area
                else:
                    # Fallback to calculated value if not in prediction
                    site_energy_value = (building_data['electricity_use_kbtu'] + building_data['natural_gas_use_kbtu']) / 1000
                st.markdown(display_metric_card("Site Energy Use", site_energy_value, "kBtu/ft²"), unsafe_allow_html=True)
            
            with col2:
                # Energy Star Score - get from prediction
                energy_star_key = next((k for k in prediction.keys() if 'energy_star' in k.lower() or 'star' in k.lower() or 'score' in k.lower()), None)
                if energy_star_key:
                    energy_star_score = prediction[energy_star_key]
                else:
                    # If not in prediction, look for any score-related prediction
                    score_key = next((k for k in prediction.keys() if 'score' in k.lower()), None)
                    energy_star_score = prediction[score_key] if score_key else 0
                st.markdown(display_metric_card("Energy Star Score", energy_star_score), unsafe_allow_html=True)
            
            col3, col4 = st.columns(2)
            
            with col3:
                # Net Emissions - get from prediction
                emissions_key = next((k for k in prediction.keys() if 'emission' in k.lower() or 'ghg' in k.lower() or 'co2' in k.lower()), None)
                if emissions_key:
                    emissions_value = prediction[emissions_key]
                else:
                    emissions_value = 0
                st.markdown(display_metric_card_net("Net Emissions", emissions_value, "Metric Tons CO₂"), unsafe_allow_html=True)
            
            with col4:
                # National Median - use median data from JSON
                if median_site_eui is not None:
                    national_median = median_site_eui
                    unit_text = "kBtu/ft²"
                    
                    # Calculate delta values
                    # Get predicted site EUI (assuming it's normalized by floor area)
                    predicted_site_eui = site_energy_value / building_data.get('gross_floor_area', 1) if building_data.get('gross_floor_area', 0) > 0 else site_energy_value
                    
                    # Calculate absolute and percentage delta
                    absolute_delta = predicted_site_eui - national_median
                    percent_delta = (absolute_delta / national_median) * 100 if national_median != 0 else 0
                    
                else:
                    # Fallback if no median data found for this property type
                    national_median = "N/A"
                    unit_text = ""
                    absolute_delta = 0
                    percent_delta = 0
                    st.warning(f"No median data found for property type: {primary_property_type}")
                
                st.markdown(display_metric_card_national("National Median Site EUI", national_median, unit_text, 
                                                    primary_property_type, absolute_delta, percent_delta), 
                        unsafe_allow_html=True)
            
        else:
            st.error("⚠️ Model not available. Please ensure the model file is in the correct location.")
            st.info("📝 Using calculated values based on input parameters.")
            
            # Show calculated values even without model
            col1, col2 = st.columns(2)
            with col1:
                site_energy = building_data['electricity_use_kbtu'] + building_data['natural_gas_use_kbtu']
                st.markdown(display_metric_card("Site Energy Use", site_energy/1000, "kBtu"), unsafe_allow_html=True)
            
            with col2:
                # Calculate Energy Star Score based on EUI
                energy_star_score = max(1, min(100, 125 - (weather_normalized_eui * 0.5)))
                st.markdown(display_metric_card("Energy Star Score", energy_star_score), unsafe_allow_html=True)
            
            col3, col4 = st.columns(2)
            with col3:
                # Calculate emissions
                elec_emissions = (building_data['electricity_use_kbtu'] * 0.293 * 0.4) / 1000
                gas_emissions = (building_data['natural_gas_use_kbtu'] * 0.293 * 0.18) / 1000
                emissions_value = elec_emissions + gas_emissions
                st.markdown(display_metric_card("Net Emissions", emissions_value, "Metric Tons CO₂"), unsafe_allow_html=True)
            
            with col4:
                # Calculate national median
                type_factors = {
                    'Office': 0.8,
                    'Multifamily Housing': 0.6,
                    'Retail Store': 1.0,
                    'Hospital (General Medical & Surgical)': 1.5,
                    'K-12 School': 0.7,
                    'Hotel': 1.2
                }
                base_factor = type_factors.get(primary_property_type, 1.0)
                size_factor = max(0.5, 1.2 - (building_area / 100000))
                national_median = (building_area / 1000) * base_factor * size_factor * 0.05
                st.markdown(display_metric_card("National Median Total GHG Performance", national_median, "Metric Tons CO₂"), unsafe_allow_html=True)
        
        # Model accuracy section with Streamlit expander
        with st.expander("Model Accuracy Statistics", expanded=False):
            display_accuracy_metrics()
    
    else:        
        # Show empty cards as placeholders
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(display_metric_card("Site Energy Use", 0, "kBtu/ft²"), unsafe_allow_html=True)
        with col2:
            st.markdown(display_metric_card("Energy Star Score", 0), unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(display_metric_card("Net Emissions", 0, "Metric Tons CO₂"), unsafe_allow_html=True)
        with col4:
            st.markdown(display_metric_card("National Median Total GHG Performance", 0, "Metric Tons CO₂"), unsafe_allow_html=True)
        
        # Model accuracy section with Streamlit expander (collapsed by default)
        with st.expander("Model Accuracy Statistics", expanded=False):
            display_accuracy_metrics()

    # Prediction Feature & Segment Analysis Section
    st.markdown("---")
    st.markdown('<h1 class="main-header">Prediction Feature & Segment Analysis</h1>', unsafe_allow_html=True)
    
    # Load and prepare data for analysis
    @st.cache_data
    def load_analysis_data():
        df = pd.read_csv('nyc_data_extracted.csv')
        # Clean data - remove rows with missing Site EUI
        df = df.dropna(subset=['weather_normalized_site_eui_kbtu_ft2'])
        return df
    
    df = load_analysis_data()
    
    # Feature Importance Analysis
    st.markdown("### Feature Importance Analysis")
    st.markdown("Understanding which factors most significantly influence building energy efficiency predictions.")
    
    # Prepare data for feature importance
    feature_cols = ['building_gross_floor_area_ft2', 'year_built', 'occupancy_percent', 
                   'number_of_buildings', 'electricity_use_kbtu', 'natural_gas_use_kbtu']
    
    # Create encoded features
    le_property = LabelEncoder()
    le_borough = LabelEncoder()
    
    X = df[feature_cols].copy()
    X['primary_property_type_encoded'] = le_property.fit_transform(df['primary_property_type'].fillna('Unknown'))
    X['borough_encoded'] = le_borough.fit_transform(df['borough'].fillna('Unknown'))
    
    y = df['weather_normalized_site_eui_kbtu_ft2']
    
    # Train Random Forest for feature importance
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    # Create feature importance chart
    feature_names = feature_cols + ['Primary Property Type', 'Borough']
    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': rf.feature_importances_
    }).sort_values('Importance', ascending=True)
    
    fig_importance = go.Figure()
    fig_importance.add_trace(go.Bar(
        y=importance_df['Feature'],
        x=importance_df['Importance'],
        orientation='h',
        marker_color='#0891b2',
        text=[f'{val:.3f}' for val in importance_df['Importance']],
        textposition='auto'
    ))
    
    fig_importance.update_layout(
        title='Feature Importance in Site EUI Prediction',
        xaxis_title='Importance Score',
        yaxis_title='Features',
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig_importance, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown("---")
    
    # Predictor Distributions Analysis
    st.markdown("### Predictor Distributions Analysis")
    st.markdown("Exploring how different building characteristics relate to Site EUI across various dimensions using violin plots to show distribution patterns.")
    
    # Create subplots for different predictors
    fig_dist = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Building Type vs Site EUI', 'Year Built vs Site EUI', 'Borough vs Site EUI', 'Occupancy vs Site EUI'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Building Type vs Site EUI - Violin plot
    # Get top building types by count to avoid overcrowding
    building_type_counts = df['primary_property_type'].value_counts()
    top_building_types = building_type_counts.head(8).index
    building_type_df = df[df['primary_property_type'].isin(top_building_types)]
    
    fig_dist.add_trace(
        go.Violin(
            x=building_type_df['primary_property_type'],
            y=building_type_df['weather_normalized_site_eui_kbtu_ft2'],
            name='Building Type',
            box_visible=True,
            meanline_visible=True,
            line_color='#10b981',
            fillcolor='rgba(16, 185, 129, 0.3)'
        ),
        row=1, col=1
    )
    
    # Year Built vs Site EUI - Violin plot
    # Group years into decades for better visualization
    df['decade'] = (df['year_built'] // 10) * 10
    decade_df = df[df['decade'] >= 1900]  # Filter out very old buildings
    
    fig_dist.add_trace(
        go.Violin(
            x=decade_df['decade'],
            y=decade_df['weather_normalized_site_eui_kbtu_ft2'],
            name='Year Built',
            box_visible=True,
            meanline_visible=True,
            line_color='#f59e0b',
            fillcolor='rgba(245, 158, 11, 0.3)'
        ),
        row=1, col=2
    )
    
    # Borough vs Site EUI - Violin plot
    fig_dist.add_trace(
        go.Violin(
            x=df['borough'],
            y=df['weather_normalized_site_eui_kbtu_ft2'],
            name='Borough',
            box_visible=True,
            meanline_visible=True,
            line_color='#8b5cf6',
            fillcolor='rgba(139, 92, 246, 0.3)'
        ),
        row=2, col=1
    )
    
    # Occupancy vs Site EUI - Violin plot
    # Group occupancy into ranges for better visualization
    df['occupancy_range'] = pd.cut(df['occupancy_percent'], bins=[0, 25, 50, 75, 100], labels=['0-25%', '25-50%', '50-75%', '75-100%'])
    occupancy_df = df.dropna(subset=['occupancy_range'])
    
    fig_dist.add_trace(
        go.Violin(
            x=occupancy_df['occupancy_range'],
            y=occupancy_df['weather_normalized_site_eui_kbtu_ft2'],
            name='Occupancy',
            box_visible=True,
            meanline_visible=True,
            line_color='#ef4444',
            fillcolor='rgba(239, 68, 68, 0.3)'
        ),
        row=2, col=2
    )
    
    fig_dist.update_layout(
        title='Predictor Distributions and Site EUI Relationships',
        height=600,
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Update axis labels
    fig_dist.update_xaxes(title_text="Building Type", row=1, col=1)
    fig_dist.update_xaxes(title_text="Decade Built", row=1, col=2)
    fig_dist.update_xaxes(title_text="Borough", row=2, col=1)
    fig_dist.update_xaxes(title_text="Occupancy Range", row=2, col=2)
    
    fig_dist.update_yaxes(title_text="Site EUI (kBtu/ft²)", row=1, col=1)
    fig_dist.update_yaxes(title_text="Site EUI (kBtu/ft²)", row=1, col=2)
    fig_dist.update_yaxes(title_text="Site EUI (kBtu/ft²)", row=2, col=1)
    fig_dist.update_yaxes(title_text="Site EUI (kBtu/ft²)", row=2, col=2)
    
    st.plotly_chart(fig_dist, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown("---")
    
    # Feature Correlations Analysis
    st.markdown("### Feature Correlations Analysis")
    st.markdown("Understanding the relationships between different building features and their correlation with Site EUI.")
    
    # Prepare correlation data
    correlation_cols = ['building_gross_floor_area_ft2', 'year_built', 'occupancy_percent', 
                       'number_of_buildings', 'electricity_use_kbtu', 'natural_gas_use_kbtu',
                       'weather_normalized_site_eui_kbtu_ft2']
    
    corr_df = df[correlation_cols].corr()
    
    # Create correlation heatmap
    fig_corr = go.Figure(data=go.Heatmap(
        z=corr_df.values,
        x=corr_df.columns,
        y=corr_df.columns,
        colorscale='RdBu',
        zmid=0,
        text=corr_df.round(2).values,
        texttemplate="%{text}",
        textfont={"size": 12},
        hoverongaps=False
    ))
    
    fig_corr.update_layout(
        title='Feature Correlation Matrix',
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(side="bottom"),
        yaxis=dict(autorange="reversed")
    )
    
    st.plotly_chart(fig_corr, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")
    st.markdown('<h1 class="main-header">Property Intelligence</h1>', unsafe_allow_html=True)

    if address:
        query_address = address.replace(" ", "+")
        api_key = "AIzaSyD0zJjgiT8qd395langIROnIVMBOfkhUW0"
        
        # Get coordinates
        latitude, longitude = get_coordinates(address, api_key)
        
        if latitude and longitude:
            # Create two columns
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("### Map View")
                
            with col2:
                st.markdown("### Street View")
            
            # Display the synced maps
            synced_maps_html = create_synced_map_streetview(latitude, longitude, api_key, address)
            components.html(synced_maps_html, height=400)
    
        with st.spinner('🔍 Fetching building data from NYC PLUTO database...'):
            print(address)
            pluto_data = fetch_pluto_data(address=address)
            if pluto_data is not None:
                display_pluto_section_alternative(pluto_data)
            else:
                st.warning("⚠️ No PLUTO building data found for this address. Please verify the address is within NYC limits and try again.")
            
if __name__ == "__main__":
    main()
