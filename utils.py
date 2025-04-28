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
        if 'favorites' in st.session_state and not property_data.empty:
            for fav in st.session_state.favorites:
                if str(fav.values) == str(property_data.values):
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
        
        # Source with link
        source = property_data['source']
        link = property_data['link']
        
        if link and link != "N/A":
            st.markdown(f"<p>Source: <a href='{link}' target='_blank'>{source}</a></p>", unsafe_allow_html=True)
        else:
            st.markdown(f"<p>Source: {source}</p>", unsafe_allow_html=True)
        
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
                        if str(comp.values) == str(property_data.values):
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
                            if str(comp.values) == str(property_data.values):
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
                        st.session_state.compare_properties = [
                            comp for comp in st.session_state.compare_properties 
                            if str(comp.values) != str(property_data.values)
                        ]
        
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
                        st.session_state.favorites = [
                            fav for fav in st.session_state.favorites 
                            if str(fav.values) != str(property_data.values)
                        ]
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
        'square_feet', 'property_type', 'source'
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
    
    # Show the comparison table
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
            
            # Pause briefly to avoid overloading the geocoding service
            time.sleep(0.5)
        
        # Clear progress bar
        progress_bar.empty()
    
    return result_df

def create_property_map(properties_df):
    """
    Create an interactive map showing property locations
    
    Args:
        properties_df (pd.DataFrame): DataFrame containing property listings with coordinates
        
    Returns:
        folium.Map: Interactive map object with property markers
    """
    # Filter properties with valid coordinates
    valid_properties = properties_df.dropna(subset=['latitude', 'longitude'])
    
    if valid_properties.empty:
        return None
    
    # Determine map center (average of all property coordinates)
    center_lat = valid_properties['latitude'].mean()
    center_lng = valid_properties['longitude'].mean()
    
    # Create the map
    property_map = folium.Map(location=[center_lat, center_lng], zoom_start=12)
    
    # Add a marker cluster to handle many properties
    marker_cluster = MarkerCluster().add_to(property_map)
    
    # Add markers for each property
    for idx, property_data in valid_properties.iterrows():
        # Create popup content with property details
        price = format_price(property_data['price'])
        beds = property_data['bedrooms'] if pd.notna(property_data['bedrooms']) else "N/A"
        baths = property_data['bathrooms'] if pd.notna(property_data['bathrooms']) else "N/A"
        sqft = f"{property_data['square_feet']:,.0f}" if pd.notna(property_data['square_feet']) else "N/A"
        prop_type = property_data['property_type'] if pd.notna(property_data['property_type']) else "N/A"
        
        popup_html = f"""
        <div style="width: 200px;">
            <h4 style="margin: 5px 0;">{price}</h4>
            <p style="margin: 2px 0;"><b>{property_data['address']}</b></p>
            <p style="margin: 2px 0;">{beds} beds | {baths} baths | {sqft} sqft</p>
            <p style="margin: 2px 0;">{prop_type} | {property_data['source']}</p>
        </div>
        """
        
        # Create popup
        popup = folium.Popup(popup_html, max_width=300)
        
        # Add marker to cluster
        folium.Marker(
            location=[property_data['latitude'], property_data['longitude']],
            popup=popup,
            icon=folium.Icon(color="blue", icon="home")
        ).add_to(marker_cluster)
    
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
    
    # Create the map
    property_map = create_property_map(geocoded_properties)
    
    if property_map:
        # Display map in Streamlit
        st.subheader(f"Map of {len(valid_coords)} Properties")
        
        # Show stats about mapping success
        total_properties = len(geocoded_properties)
        mapped_properties = len(valid_coords)
        mapping_success_rate = (mapped_properties / total_properties) * 100 if total_properties > 0 else 0
        
        st.caption(f"Successfully mapped {mapped_properties} out of {total_properties} properties ({mapping_success_rate:.1f}%).")
        
        # Display the map
        folium_static(property_map)
    else:
        st.warning("Could not create property map.")

def display_favorites_view(favorites_list):
    """
    Display a list of favorited properties
    
    Args:
        favorites_list (list): List of property Series objects that have been favorited
    """
    if not favorites_list or len(favorites_list) == 0:
        st.info("You haven't added any properties to your favorites yet.")
        return
    
    st.subheader(f"My Favorites ({len(favorites_list)})")
    
    # Convert list to DataFrame
    favorites_df = pd.DataFrame(favorites_list)
    
    # Display favorite properties
    favorites_cols = [st.columns(2) for _ in range((len(favorites_list) + 1) // 2)]
    
    for i, property_data in enumerate(favorites_list):
        row = i // 2
        col = i % 2
        with favorites_cols[row][col]:
            display_property_card(
                property_data, 
                show_compare=True, 
                show_favorite=True
            )
    
    # Add a button to clear all favorites
    if st.button("Clear All Favorites"):
        st.session_state.favorites = []
        st.rerun()
