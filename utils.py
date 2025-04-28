import streamlit as st
import pandas as pd
import numpy as np
import re
import time
import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import plotly.express as px
from streamlit_folium import folium_static

def get_unique_values(df, column):
    """
    Get unique values from a DataFrame column
    
    Args:
        df (pd.DataFrame): DataFrame to extract values from
        column (str): Column name to get unique values from
        
    Returns:
        list: List of unique values (sorted)
    """
    if df.empty or column not in df.columns:
        return []
    
    # Get unique values, excluding NaN
    unique_values = df[column].dropna().unique().tolist()
    
    # Sort values
    unique_values.sort()
    
    return unique_values

def format_price(price):
    """
    Format price value to a nice string
    
    Args:
        price (float or int): Price value to format
        
    Returns:
        str: Formatted price string
    """
    if pd.isna(price):
        return "N/A"
    
    # Format as currency with commas
    if price >= 1000000:
        return f"${price/1000000:.2f}M"
    if price >= 1000:
        return f"${price/1000:.0f}K"
    return f"${price:.0f}"

def display_property_card(property_data, show_compare=True, show_favorite=True):
    """
    Display a property card with formatted information
    
    Args:
        property_data (pd.Series): Row of property data from DataFrame
        show_compare (bool): Whether to show the compare checkbox
        show_favorite (bool): Whether to show the favorite button
    """
    # Create a unique ID for this property
    property_id = f"property_{hash(str(property_data.values))}"
    
    # Create a card-like display for a property
    with st.container():
        # Add a border and padding
        st.markdown("""
        <style>
        .property-card {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            position: relative;
        }
        .favorite-badge {
            position: absolute;
            top: 5px;
            right: 5px;
            color: gold;
            font-size: 24px;
        }
        .quality-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        .quality-high {
            background-color: #d4edda;
            color: #155724;
        }
        .quality-medium {
            background-color: #fff3cd;
            color: #856404;
        }
        .quality-low {
            background-color: #f8d7da;
            color: #721c24;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Check if property is in favorites
        is_favorite = False
        if 'favorites' in st.session_state:
            # Check if property_data is a DataFrame/Series or a dict
            if hasattr(property_data, 'empty'):
                # Handle pandas Series/DataFrame
                if not property_data.empty:
                    for fav in st.session_state.favorites:
                        if hasattr(fav, 'values') and hasattr(property_data, 'values'):
                            if str(fav.values) == str(property_data.values):
                                is_favorite = True
                                break
            elif isinstance(property_data, dict):
                # Handle dictionary type property data
                for fav in st.session_state.favorites:
                    if isinstance(fav, dict) and str(fav) == str(property_data):
                        is_favorite = True
                        break
                    elif hasattr(fav, 'to_dict') and str(fav.to_dict()) == str(property_data):
                        is_favorite = True
                        break
        
        # Start the card
        favorite_badge = '<span class="favorite-badge">★</span>' if is_favorite else ''
        st.markdown(f'<div class="property-card">{favorite_badge}', unsafe_allow_html=True)
        
        # Price (large and bold)
        price_display = format_price(property_data['price'])
        
        # Add data quality badge if available
        quality_badge = ""
        if 'data_quality_score' in property_data:
            quality = property_data['data_quality_score']
            if quality >= 80:
                quality_badge = f'<span class="quality-badge quality-high">{quality:.0f}% Quality</span>'
            elif quality >= 50:
                quality_badge = f'<span class="quality-badge quality-medium">{quality:.0f}% Quality</span>'
            else:
                quality_badge = f'<span class="quality-badge quality-low">{quality:.0f}% Quality</span>'
        
        st.markdown(f"<h3 style='margin-bottom:0;'>{price_display} {quality_badge}</h3>", unsafe_allow_html=True)
        
        # Address
        st.markdown(f"<p style='margin-top:0;'>{property_data['address']}</p>", unsafe_allow_html=True)
        
        # Property details in a single line
        beds = property_data['bedrooms'] if not pd.isna(property_data['bedrooms']) else "N/A"
        baths = property_data['bathrooms'] if not pd.isna(property_data['bathrooms']) else "N/A"
        sqft = f"{property_data['square_feet']:,.0f}" if not pd.isna(property_data['square_feet']) else "N/A"
        
        details = f"{beds} beds • {baths} baths • {sqft} sqft • {property_data['property_type']}"
        st.markdown(f"<p>{details}</p>", unsafe_allow_html=True)
        
        # Source with link - enhanced to be more prominent
        source = property_data['source']
        link = property_data['link']
        
        if link and link != "N/A":
            st.markdown(f"""
            <div style="margin-top: 10px; margin-bottom: 10px;">
                <span style="font-weight: bold;">Found on:</span> 
                <a href='{link}' target='_blank' style="color: #0366d6; text-decoration: underline; font-weight: bold;">
                    {source} <span style="font-size: 14px;">↗</span>
                </a>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="margin-top: 10px; margin-bottom: 10px;">
                <span style="font-weight: bold;">Found on:</span> {source}
            </div>
            """, unsafe_allow_html=True)
        
        # Action buttons in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Add a button to view detailed property information
            if st.button(f"View Details", key=f"view_{property_id}"):
                # Store property details in session state for display in a modal
                st.session_state.selected_property = {
                    'data': property_data,
                    'link': link
                }
                # Force a rerun to display the property details
                st.rerun()
        
        with col2:
            # Add checkbox to compare properties
            if show_compare:
                is_in_compare = False
                if 'compare_properties' in st.session_state:
                    for comp in st.session_state.compare_properties:
                        # Check if both are Series/DataFrame with values attribute
                        if hasattr(comp, 'values') and hasattr(property_data, 'values'):
                            if str(comp.values) == str(property_data.values):
                                is_in_compare = True
                                break
                        # Check if they're dictionaries
                        elif isinstance(comp, dict) and isinstance(property_data, dict):
                            if str(comp) == str(property_data):
                                is_in_compare = True
                                break
                
                if st.checkbox("Compare", value=is_in_compare, key=f"compare_{property_id}"):
                    # Add to comparison list if not already there
                    if 'compare_properties' not in st.session_state:
                        st.session_state.compare_properties = [property_data]
                    else:
                        # Check if already in list to avoid duplicates
                        already_in_list = False
                        for comp in st.session_state.compare_properties:
                            # Check if both are Series/DataFrame with values attribute
                            if hasattr(comp, 'values') and hasattr(property_data, 'values'):
                                if str(comp.values) == str(property_data.values):
                                    already_in_list = True
                                    break
                            # Check if they're dictionaries
                            elif isinstance(comp, dict) and isinstance(property_data, dict):
                                if str(comp) == str(property_data):
                                    already_in_list = True
                                    break
                        
                        if not already_in_list:
                            # Limit to 5 properties for comparison
                            if len(st.session_state.compare_properties) < 5:
                                st.session_state.compare_properties.append(property_data)
                            else:
                                st.warning("You can compare up to 5 properties at a time.")
                else:
                    # Remove from comparison list
                    if 'compare_properties' in st.session_state:
                        new_compare_list = []
                        for comp in st.session_state.compare_properties:
                            should_keep = True
                            # Check if both are Series/DataFrame with values attribute
                            if hasattr(comp, 'values') and hasattr(property_data, 'values'):
                                if str(comp.values) == str(property_data.values):
                                    should_keep = False
                            # Check if they're dictionaries
                            elif isinstance(comp, dict) and isinstance(property_data, dict):
                                if str(comp) == str(property_data):
                                    should_keep = False
                            
                            if should_keep:
                                new_compare_list.append(comp)
                        
                        st.session_state.compare_properties = new_compare_list
        
        with col3:
            # Add favorite button
            if show_favorite:
                if st.button("★ Favorite" if not is_favorite else "☆ Unfavorite", key=f"fav_{property_id}"):
                    # Initialize favorites list if it doesn't exist
                    if 'favorites' not in st.session_state:
                        st.session_state.favorites = []
                    
                    if not is_favorite:
                        # Add to favorites
                        st.session_state.favorites.append(property_data)
                    else:
                        # Remove from favorites
                        new_favorites_list = []
                        for fav in st.session_state.favorites:
                            should_keep = True
                            # Check if both are Series/DataFrame with values attribute
                            if hasattr(fav, 'values') and hasattr(property_data, 'values'):
                                if str(fav.values) == str(property_data.values):
                                    should_keep = False
                            # Check if they're dictionaries
                            elif isinstance(fav, dict) and isinstance(property_data, dict):
                                if str(fav) == str(property_data):
                                    should_keep = False
                            
                            if should_keep:
                                new_favorites_list.append(fav)
                        
                        st.session_state.favorites = new_favorites_list
                    st.rerun()  # Refresh to update the display
        
        # End the card
        st.markdown('</div>', unsafe_allow_html=True)

def create_comparison_table(properties):
    """
    Create a comparison table for selected properties
    
    Args:
        properties (pd.DataFrame): DataFrame containing selected properties
        
    Returns:
        pd.DataFrame: Formatted comparison table
    """
    if properties.empty:
        return pd.DataFrame()
    
    # Select columns for comparison
    comparison_cols = [
        'address', 'price', 'bedrooms', 'bathrooms', 
        'square_feet', 'property_type', 'source', 'link'
    ]
    
    # Add optional data quality columns if available
    optional_cols = ['data_quality_score', 'price_per_sqft']
    for col in optional_cols:
        if col in properties.columns:
            comparison_cols.append(col)
    
    # Create comparison table with only the selected columns
    comparison = properties[comparison_cols].copy()
    
    # Format price column
    comparison['price'] = comparison['price'].apply(format_price)
    
    # Add calculated fields
    if 'square_feet' in comparison.columns and 'price' in comparison.columns:
        # Calculate price per square foot if not already present
        if 'price_per_sqft' not in comparison.columns:
            comparison['price_per_sqft'] = properties.apply(
                lambda x: x['price'] / x['square_feet'] if pd.notna(x['price']) and pd.notna(x['square_feet']) and x['square_feet'] > 0 else pd.NA, 
                axis=1
            )
    
    # Format price_per_sqft if present
    if 'price_per_sqft' in comparison.columns:
        comparison['price_per_sqft'] = comparison['price_per_sqft'].apply(
            lambda x: f"${x:.2f}/sqft" if pd.notna(x) else "N/A"
        )
    
    # Format data quality score if present
    if 'data_quality_score' in comparison.columns:
        comparison['data_quality_score'] = comparison['data_quality_score'].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
        )
    
    # Rename columns for display
    column_renames = {
        'address': 'Address',
        'price': 'Price',
        'bedrooms': 'Beds',
        'bathrooms': 'Baths',
        'square_feet': 'Sq Ft',
        'property_type': 'Type',
        'source': 'Source',
        'data_quality_score': 'Data Quality',
        'price_per_sqft': 'Price/SqFt'
    }
    comparison = comparison.rename(columns=column_renames)
    
    return comparison

def display_interactive_comparison(properties_list):
    """
    Display an interactive comparison view of properties
    
    Args:
        properties_list (list): List of property Series objects to compare
    """
    if not properties_list or len(properties_list) == 0:
        st.info("Select properties to compare using the checkboxes")
        return
    
    # Convert list to DataFrame
    properties_df = pd.DataFrame(properties_list)
    
    # Create formatted comparison table
    comparison_df = create_comparison_table(properties_df)
    
    # Display comparison table
    st.subheader(f"Comparing {len(properties_list)} Properties")
    
    # Calculate metrics for comparison
    metrics_cols = st.columns(len(properties_list))
    
    for i, (_, prop) in enumerate(properties_df.iterrows()):
        with metrics_cols[i]:
            # Show metrics for this property
            st.metric(
                label=f"Property {i+1}",
                value=format_price(prop['price']),
                delta=f"{prop['bedrooms']} beds, {prop['bathrooms']} baths"
            )
    
    # Format source column to include links if available
    if 'link' in comparison_df.columns:
        # Create clickable links for each property
        st.markdown("### Properties with Links to Original Listings")
        for i, row in comparison_df.iterrows():
            source = row.get('Source', 'Unknown Source')
            link = row.get('link')
            address = row.get('Address', f'Property {i+1}')
            
            if pd.notna(link) and link != "N/A" and link != "#":
                st.markdown(f"""
                <div style="margin-bottom: 8px;">
                    <strong>Property {i+1}:</strong> {address} - 
                    <a href="{link}" target="_blank" style="color: #0366d6; text-decoration: underline;">
                        View on {source} <span style="font-size: 14px;">↗</span>
                    </a>
                </div>
                """, unsafe_allow_html=True)
        
        # Remove the link column from the display table
        if 'link' in comparison_df.columns:
            comparison_df = comparison_df.drop(columns=['link'])
    
    # Show the comparison table
    st.markdown("### Comparison Table")
    st.dataframe(comparison_df, use_container_width=True)
    
    # Display a visual comparison of key metrics
    st.subheader("Visual Comparison")
    
    # Price comparison bar chart
    price_data = {f"Property {i+1}": prop['price'] for i, prop in enumerate(properties_list)}
    price_df = pd.DataFrame([price_data])
    price_df = price_df.T.reset_index()
    price_df.columns = ['Property', 'Price']
    
    import plotly.express as px
    fig = px.bar(
        price_df, 
        x='Property', 
        y='Price',
        title="Price Comparison",
        labels={"Price": "Price ($)"},
        color='Property'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Price per square foot comparison (if data available)
    if all('square_feet' in prop and pd.notna(prop['square_feet']) and prop['square_feet'] > 0 for prop in properties_list):
        price_per_sqft_data = {
            f"Property {i+1}": prop['price'] / prop['square_feet'] 
            for i, prop in enumerate(properties_list)
        }
        price_per_sqft_df = pd.DataFrame([price_per_sqft_data])
        price_per_sqft_df = price_per_sqft_df.T.reset_index()
        price_per_sqft_df.columns = ['Property', 'Price per SqFt']
        
        fig = px.bar(
            price_per_sqft_df, 
            x='Property', 
            y='Price per SqFt',
            title="Price per Square Foot Comparison",
            labels={"Price per SqFt": "Price per SqFt ($)"},
            color='Property'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Add a button to clear comparison
    if st.button("Clear Comparison"):
        st.session_state.compare_properties = []
        st.rerun()

def geocode_address(address):
    """
    Convert an address to latitude and longitude coordinates.
    
    Args:
        address (str): Property address to geocode
        
    Returns:
        tuple: (latitude, longitude) coordinates or (None, None) if geocoding fails
    """
    # Check if we've already geocoded this address (using session state as cache)
    if 'geocode_cache' not in st.session_state:
        st.session_state.geocode_cache = {}
        
    # Return cached result if available
    if address in st.session_state.geocode_cache:
        return st.session_state.geocode_cache[address]
    
    # Initialize the geocoder with a custom user agent
    geolocator = Nominatim(user_agent="real_estate_scraper")
    
    try:
        # Attempt to geocode the address with a shorter timeout
        location = geolocator.geocode(address, timeout=5)
        
        # If successful, cache and return the coordinates
        if location:
            coords = (location.latitude, location.longitude)
            st.session_state.geocode_cache[address] = coords
            return coords
        else:
            st.session_state.geocode_cache[address] = (None, None)
            return (None, None)
    
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        # Handle geocoding errors gracefully
        print(f"Geocoding error for address '{address}': {str(e)}")
        st.session_state.geocode_cache[address] = (None, None)
        return (None, None)
    except Exception as e:
        # Handle any other errors
        print(f"Unexpected error geocoding address '{address}': {str(e)}")
        st.session_state.geocode_cache[address] = (None, None)
        return (None, None)

def geocode_properties(properties_df):
    """
    Add latitude and longitude coordinates to a DataFrame of properties
    
    Args:
        properties_df (pd.DataFrame): DataFrame containing property listings with addresses
        
    Returns:
        pd.DataFrame: DataFrame with added latitude and longitude columns
    """
    if properties_df.empty:
        return properties_df
    
    # Check if geocoding has already been done
    if 'latitude' in properties_df.columns and 'longitude' in properties_df.columns:
        # Only geocode rows with missing coordinates
        mask = properties_df['latitude'].isna() | properties_df['longitude'].isna()
        if not mask.any():
            return properties_df  # No geocoding needed
    else:
        # Add latitude and longitude columns
        properties_df['latitude'] = None
        properties_df['longitude'] = None
        mask = pd.Series([True] * len(properties_df))  # Geocode all rows
    
    # Create a copy of the dataframe to avoid modifying the original during iteration
    result_df = properties_df.copy()
    
    # Limit the number of properties to geocode to improve performance
    max_to_geocode = min(15, mask.sum())
    if mask.sum() > max_to_geocode:
        st.info(f"To improve performance, only geocoding {max_to_geocode} out of {mask.sum()} properties for the map.")
        # Sort by price descending to prioritize higher-priced properties
        if 'price' in properties_df.columns:
            prioritized = properties_df[mask].sort_values(by='price', ascending=False)
            to_geocode = prioritized.index[:max_to_geocode]
            mask = mask & properties_df.index.isin(to_geocode)
    
    # Show a progress bar for geocoding
    with st.spinner("Geocoding property addresses..."):
        progress_bar = st.progress(0)
        
        # Process each property that needs geocoding
        rows_to_process = mask.sum()
        processed = 0
        
        for idx, row in properties_df[mask].iterrows():
            # Combine address and city for better geocoding results
            full_address = row['address']
            if pd.notna(row.get('city')):
                if row['city'] not in full_address:
                    full_address += f", {row['city']}"
                    
            # Geocode the address
            lat, lng = geocode_address(full_address)
            
            # Update the result dataframe
            result_df.at[idx, 'latitude'] = lat
            result_df.at[idx, 'longitude'] = lng
            
            # Update progress
            processed += 1
            progress_bar.progress(processed / rows_to_process)
            
            # Use a smaller delay for geocoding service
            time.sleep(0.2)
        
        # Clear progress bar
        progress_bar.empty()
    
    return result_df

def create_property_map(properties_df, view_type="markers"):
    """
    Create an interactive map showing property locations
    
    Args:
        properties_df (pd.DataFrame): DataFrame containing property listings with coordinates
        view_type (str): Type of map visualization - 'markers', 'heatmap', or 'both'
        
    Returns:
        folium.Map: Interactive map object with property markers or heatmap
    """
    # Filter properties with valid coordinates
    valid_properties = properties_df.dropna(subset=['latitude', 'longitude'])
    
    if valid_properties.empty:
        return None
    
    # Determine map center (average of all property coordinates)
    center_lat = valid_properties['latitude'].mean()
    center_lng = valid_properties['longitude'].mean()
    
    # Create the map with simplified tiles for faster loading
    property_map = folium.Map(
        location=[center_lat, center_lng], 
        zoom_start=12,
        tiles='CartoDB positron',  # Use a lighter tile set for faster loading
        prefer_canvas=True         # Use canvas rendering for better performance
    )
    
    # Define price color ranges
    def get_price_color(price):
        if pd.isna(price):
            return "gray"
        elif price < 300000:
            return "green"
        elif price < 600000:
            return "blue"
        elif price < 1000000:
            return "orange"
        else:
            return "red"
    
    # Add markers for each property - limit to 50 for performance
    properties_to_display = valid_properties
    if len(valid_properties) > 50:
        # Only show top 50 properties by price for better performance
        properties_to_display = valid_properties.nlargest(50, 'price')
    
    # Add marker clusters if selected
    if view_type in ["markers", "both"]:
        # Add a marker cluster to handle many properties
        marker_cluster = MarkerCluster().add_to(property_map)
        
        for idx, property_data in properties_to_display.iterrows():
            # Create simplified popup content with property details
            price = format_price(property_data['price'])
            beds_baths = f"{property_data['bedrooms']:.0f}bd, {property_data['bathrooms']:.1f}ba" if pd.notna(property_data['bedrooms']) and pd.notna(property_data['bathrooms']) else "N/A"
            
            popup_html = f"""
            <div style="width: 180px;">
                <h4 style="margin: 3px 0;">{price}</h4>
                <p style="margin: 2px 0;"><b>{property_data['address']}</b></p>
                <p style="margin: 2px 0;">{beds_baths}</p>
            </div>
            """
            
            # Create popup
            popup = folium.Popup(popup_html, max_width=200)
            
            # Add marker to cluster with color based on price
            color = get_price_color(property_data['price'])
            folium.Marker(
                location=[property_data['latitude'], property_data['longitude']],
                popup=popup,
                icon=folium.Icon(color=color, icon="home", prefix='fa')
            ).add_to(marker_cluster)
    
    # Add heatmap if selected
    if view_type in ["heatmap", "both"]:
        # Prepare data for heatmap
        heat_data = [[row['latitude'], row['longitude'], row['price']/50000] 
                     for _, row in valid_properties.iterrows() if pd.notna(row['latitude']) and pd.notna(row['longitude'])]
        
        # Add heatmap layer
        from folium.plugins import HeatMap
        HeatMap(heat_data, 
                radius=15, 
                blur=10, 
                gradient={0.4: 'blue', 0.65: 'lime', 0.8: 'yellow', 1: 'red'},
                max_zoom=13).add_to(property_map)
    
    # Add a layer control if both view types are used
    if view_type == "both":
        folium.LayerControl().add_to(property_map)
    
    return property_map

def display_property_map(properties_df):
    """
    Display an interactive map of property locations in Streamlit
    
    Args:
        properties_df (pd.DataFrame): DataFrame containing property listings
    """
    if properties_df.empty:
        st.info("No properties available for mapping.")
        return
    
    # Ensure properties have coordinates
    geocoded_properties = geocode_properties(properties_df)
    
    # Check if we have valid coordinates
    valid_coords = geocoded_properties.dropna(subset=['latitude', 'longitude'])
    
    if valid_coords.empty:
        st.warning("Could not geocode any property addresses. Map cannot be displayed.")
        return
    
    # Create columns for layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Add view type selector
        view_type = st.radio(
            "Map View Type", 
            ["Markers", "Heatmap", "Both"],
            key="map_view_type",
            horizontal=True
        )
    
    with col2:
        # Show price range legend
        st.markdown("**Price Legend:**")
        
        st.markdown('<div style="display:flex;align-items:center;margin-bottom:5px;"><div style="width:12px;height:12px;background-color:green;margin-right:5px;"></div> &lt; $300k</div>', unsafe_allow_html=True)
        st.markdown('<div style="display:flex;align-items:center;margin-bottom:5px;"><div style="width:12px;height:12px;background-color:blue;margin-right:5px;"></div> $300k - $600k</div>', unsafe_allow_html=True)
        st.markdown('<div style="display:flex;align-items:center;margin-bottom:5px;"><div style="width:12px;height:12px;background-color:orange;margin-right:5px;"></div> $600k - $1M</div>', unsafe_allow_html=True)
        st.markdown('<div style="display:flex;align-items:center;margin-bottom:5px;"><div style="width:12px;height:12px;background-color:red;margin-right:5px;"></div> &gt; $1M</div>', unsafe_allow_html=True)
    
    # Map the radio button selection to the parameter values for create_property_map
    view_type_map = {
        "Markers": "markers",
        "Heatmap": "heatmap",
        "Both": "both"
    }
    selected_view_type = view_type_map[view_type]
    
    # Create the map
    property_map = create_property_map(geocoded_properties, view_type=selected_view_type)
    
    if property_map:
        # Display map in Streamlit
        st.subheader(f"Map of {len(valid_coords)} Properties")
        
        # Show stats about mapping success
        total_properties = len(geocoded_properties)
        mapped_properties = len(valid_coords)
        mapping_success_rate = (mapped_properties / total_properties) * 100 if total_properties > 0 else 0
        
        st.caption(f"Successfully mapped {mapped_properties} out of {total_properties} properties ({mapping_success_rate:.1f}%).")
        
        # Add map description based on view type
        if view_type == "Markers":
            st.caption("Showing clustered property markers. Click on clusters to zoom in and see individual properties.")
        elif view_type == "Heatmap":
            st.caption("Showing property price heatmap. Red areas indicate higher-priced properties.")
        else:
            st.caption("Showing both markers and heatmap. Use the layer control in the top right to toggle between views.")
        
        # Display the map
        folium_static(property_map)
        
        # Map optimization note
        st.info("Note: For better performance, the map displays up to 50 properties. If you have more properties, consider using the filters to focus on specific areas or price ranges.")
    else:
        st.warning("Could not create property map.")

def display_favorites_view(favorites_list):
    """
    Display a list of favorited properties
    
    Args:
        favorites_list (list): List of property Series objects or dictionaries that have been favorited
    """
    if not favorites_list or len(favorites_list) == 0:
        st.info("You haven't added any properties to your favorites yet.")
        return
    
    st.subheader(f"My Favorites ({len(favorites_list)})")
    
    # Handle different data types in favorites_list
    try:
        # Try to convert list to DataFrame - this works if all items are Series
        favorites_df = pd.DataFrame(favorites_list)
    except Exception as e:
        # If conversion failed, we might have a mix of types or all dictionaries
        st.warning("Some favorites may not display correctly. Try refreshing or clearing favorites if you encounter issues.")
    
    # Display favorite properties
    favorites_cols = [st.columns(2) for _ in range((len(favorites_list) + 1) // 2)]
    
    for i, property_data in enumerate(favorites_list):
        try:
            row = i // 2
            col = i % 2
            with favorites_cols[row][col]:
                # Make sure property_data is properly structured
                if isinstance(property_data, dict):
                    # If it's a dictionary, we need to ensure required fields exist
                    required_fields = ['price', 'address', 'bedrooms', 'bathrooms', 'square_feet', 'property_type', 'source', 'link']
                    for field in required_fields:
                        if field not in property_data:
                            if field in ['price', 'bedrooms', 'bathrooms', 'square_feet']:
                                property_data[field] = 0
                            else:
                                property_data[field] = "N/A"
                
                # Display the property card
                display_property_card(
                    property_data, 
                    show_compare=True, 
                    show_favorite=True
                )
        except Exception as e:
            with favorites_cols[row][col]:
                st.error(f"Error displaying this favorite property. It may use an incompatible format.")
                st.caption(f"Error details: {str(e)}")
    
    # Add a button to clear all favorites
    if st.button("Clear All Favorites"):
        st.session_state.favorites = []
        st.rerun()
