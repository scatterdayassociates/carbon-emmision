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
from geopy.distance import geodesic
from rapidfuzz import process, fuzz
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
    
# Custom CSS for styling
# Updated CSS styles
# Updated CSS styles
st.markdown("""
<style>
    .metric-card {
        border: 2px dashed #999;
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        margin: 5px;
    }
    .metric-card-with-tooltip {
        border: 2px dashed #999;
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        margin: 5px;
        position: relative;
    }
    .metric-title {
        font-size: 14px;
        color: #666;
        margin-bottom: 10px;
        text-align: center;
        position: relative;
    }
    .metric-value {
        font-size: 34px;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-unit {
        font-size: 12px;
        opacity: 0.8;
    }
    .tooltip-container {
        position: relative;
        display: inline-block;
    }
    .tooltip-icon {
        font-size: 12px;
        margin-left: 5px;
        opacity: 0.7;
        cursor: help;
    }
    .tooltip-text {
        visibility: hidden;
        width: 250px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 8px;
        position: absolute;
        z-index: 1000;
        bottom: 125%;
        left: 50%;
        margin-left: -125px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 11px;
        line-height: 1.3;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }
    .tooltip-container:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    .delta-overlay {
        position: absolute;
        top: 50%;
        right: -1px;
        transform: translateY(-50%);
        display: flex;
        flex-direction: column;
        gap: 4px;
        z-index: 10;
        background: rgba(255, 255, 255, 0.9);
        padding: 8px;
        border-radius: 6px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .delta-item {
        display: flex;
        align-items: baseline;
        gap: 3px;
        font-size: 10px;
        white-space: nowrap;
    }
    .delta-label {
        font-size: 10px;
        font-weight: bold;
        color: #555;
    }
    .delta-value {
        font-size: 11px;
        font-weight: 700;
    }
    .delta-unit {
        font-size: 9px;
        color: #777;
        opacity: 0.9;
    }
    .accuracy-card {
        border: 2px dashed #999;
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        margin: 5px;
    }
    .accuracy-value {
        font-size: 34px;
        font-weight: bold;
        margin: 10px 0;
    }
    .accuracy-label {
        font-size: 10px;
        opacity: 0.8;
    }
    .main-header {
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 30px;
        color: #2D3748;
    }
    .pluto-container {
        background: #F7FAFC;
        border: 1px solid #E2E8F0;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .pluto-item {
        font-size: 14px;
        color: #2D3748;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .pluto-label {
        font-weight: bold;
        display: inline;
    }
    .pluto-value {
        font-weight: normal;
        display: inline;
    }
    .pluto-section-header {
        font-size: 18px;
        font-weight: bold;
        color: #2D3748;
        margin: 20px 0 10px 0;
        border-bottom: 2px solid #4A5568;
        padding-bottom: 5px;
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


def fetch_pluto_data(address=None, latitude=None, longitude=None, csv_path="needata.csv"):
    # Load CSV once
    df = pd.read_csv(csv_path)

    if address is not None:
        # Step 1: Fuzzy match on address
        matches = process.extract(address, df['address'], scorer=fuzz.token_sort_ratio, limit=20)
        matched_addresses = [match[0] for match in matches]

        df_filtered = df[df['address'].isin(matched_addresses)]

        if latitude is not None and longitude is not None and not df_filtered.empty:
            # Step 2: Geodesic distance on filtered set
            def compute_distance(row):
                try:
                    return geodesic(
                        (latitude, longitude),
                        (float(row['latitude']), float(row['longitude']))
                    ).meters
                except:
                    return float('inf')

            df_filtered['distance'] = df_filtered.apply(compute_distance, axis=1)
            closest = df_filtered.sort_values(by='distance').iloc[0]
            print(closest)
            return closest.drop(labels='distance', errors='ignore').to_dict()
        
        elif not df_filtered.empty:
            # No lat/lon, just return first fuzzy match
            return df_filtered.iloc[0].to_dict()
    
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
        delta_color = "#ff4444" if absolute_delta > 0 else "#44aa44" if absolute_delta < 0 else "#666"
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
                st.markdown(display_metric_card("Net Emissions", emissions_value, "Metric Tons CO₂"), unsafe_allow_html=True)
            
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
            
            # Model accuracy section
            st.markdown("### Model Accuracy Statistics")
            col5, col6, col7 = st.columns(3)
            
            with col5:
                st.markdown(display_accuracy_card("R-Squared<br>Site Energy Use", "0.8566"), unsafe_allow_html=True)
            
            with col6:
                st.markdown(display_accuracy_card("Mean Absolute Error<br>Site Energy Use", " 5078"), unsafe_allow_html=True)
            
            with col7:
                st.markdown(display_accuracy_card("Root Mean<br>Squared Error<br>Site Energy Use", "26649"), unsafe_allow_html=True)
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
    
    else:        
        # Show empty cards as placeholders
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(display_metric_card("Site Energy Use", 0, "kBtu/ft2"), unsafe_allow_html=True)
        with col2:
            st.markdown(display_metric_card("Energy Star Score", 0), unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(display_metric_card("Net Emissions", 0, "Metric Tons CO₂"), unsafe_allow_html=True)
        with col4:
            st.markdown(display_metric_card("National Median Total GHG Performance", 0, "Metric Tons CO₂"), unsafe_allow_html=True)
        
        # Model accuracy section with placeholder values
        st.markdown("### Model Accuracy Statistics")
        col5, col6, col7 = st.columns(3)
        
   
        with col5:
                st.markdown(display_accuracy_card("R-Squared<br>(Site Energy Use)", "0.8566"), unsafe_allow_html=True)
            
        with col6:
                st.markdown(display_accuracy_card("Mean Absolute Error<br>(Site Energy Use)", " 5078"), unsafe_allow_html=True)
            
        with col7:
                st.markdown(display_accuracy_card("Root Mean Squared Error<br>(Site Energy Use)", "26649"), unsafe_allow_html=True)

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
                st.markdown("###  Map View")
                
            with col2:
                st.markdown("### Street View")
            
            # Display the synced maps
            synced_maps_html = create_synced_map_streetview(latitude, longitude, api_key, address)
            components.html(synced_maps_html, height=400)
    
        with st.spinner('🔍 Fetching building data from NYC PLUTO database...'):
            print(longitude)
            print(latitude)
            pluto_data = fetch_pluto_data(address=address, longitude=longitude, latitude=latitude)
            if pluto_data is not None:
            
                display_pluto_section_alternative(pluto_data)
                    
            else:
                st.warning("⚠️ No PLUTO building data found for this address. Please verify the address is within NYC limits and try again.")
            
if __name__ == "__main__":
    main()



    
