import streamlit as st
import pandas as pd

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

def display_property_card(property_data):
    """
    Display a property card with formatted information
    
    Args:
        property_data (pd.Series): Row of property data from DataFrame
    """
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
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Start the card
        st.markdown('<div class="property-card">', unsafe_allow_html=True)
        
        # Price (large and bold)
        price_display = format_price(property_data['price'])
        st.markdown(f"<h3 style='margin-bottom:0;'>{price_display}</h3>", unsafe_allow_html=True)
        
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
            
            # Add a button to view detailed property information
            property_id = f"property_{hash(str(property_data.values))}"
            if st.button(f"View Details", key=property_id):
                # Store property details in session state for display in a modal
                if 'selected_property' not in st.session_state:
                    st.session_state.selected_property = {
                        'data': property_data,
                        'link': link
                    }
                    # Force a rerun to display the property details
                    st.rerun()
        else:
            st.markdown(f"<p>Source: {source}</p>", unsafe_allow_html=True)
        
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
    
    # Create comparison table with only the selected columns
    comparison = properties[comparison_cols].copy()
    
    # Format price column
    comparison['price'] = comparison['price'].apply(format_price)
    
    # Rename columns for display
    comparison = comparison.rename(columns={
        'address': 'Address',
        'price': 'Price',
        'bedrooms': 'Beds',
        'bathrooms': 'Baths',
        'square_feet': 'Sq Ft',
        'property_type': 'Type',
        'source': 'Source'
    })
    
    return comparison
