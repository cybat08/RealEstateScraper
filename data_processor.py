import pandas as pd
import numpy as np

def filter_properties(df, price_range, min_beds, min_baths, sources, cities, property_types):
    """
    Filter the properties dataframe based on user criteria
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        price_range (tuple): Min and max price tuple (min_price, max_price)
        min_beds (int): Minimum number of bedrooms
        min_baths (int): Minimum number of bathrooms
        sources (list): List of website sources to include
        cities (list): List of cities to include
        property_types (list): List of property types to include
        
    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    # Create a copy to avoid modifying the original
    filtered_df = df.copy()
    
    # Apply filters one by one
    if not filtered_df.empty:
        # Filter by price range
        filtered_df = filtered_df[
            (filtered_df['price'] >= price_range[0]) & 
            (filtered_df['price'] <= price_range[1])
        ]
        
        # Filter by minimum bedrooms
        if min_beds > 0:
            filtered_df = filtered_df[filtered_df['bedrooms'] >= min_beds]
        
        # Filter by minimum bathrooms
        if min_baths > 0:
            filtered_df = filtered_df[filtered_df['bathrooms'] >= min_baths]
        
        # Filter by sources
        if sources:
            filtered_df = filtered_df[filtered_df['source'].isin(sources)]
        
        # Filter by cities
        if cities:
            filtered_df = filtered_df[filtered_df['city'].isin(cities)]
        
        # Filter by property types
        if property_types:
            filtered_df = filtered_df[filtered_df['property_type'].isin(property_types)]
    
    return filtered_df

def get_statistics(df):
    """
    Calculate statistics for the property listings
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame containing statistics
    """
    # Handle empty dataframe
    if df.empty:
        return pd.DataFrame()
    
    # Calculate statistics
    stats = {
        'Metric': [
            'Average Price', 
            'Median Price', 
            'Min Price', 
            'Max Price',
            'Average Bedrooms',
            'Average Bathrooms',
            'Average Square Feet',
            'Price per Square Foot (Avg)',
            'Most Common Property Type'
        ],
        'Value': [
            f"${df['price'].mean():,.2f}",
            f"${df['price'].median():,.2f}",
            f"${df['price'].min():,.2f}",
            f"${df['price'].max():,.2f}",
            f"{df['bedrooms'].mean():.1f}",
            f"{df['bathrooms'].mean():.1f}",
            f"{df['square_feet'].mean():,.0f}" if 'square_feet' in df.columns and not df['square_feet'].isnull().all() else 'N/A',
            f"${(df['price'] / df['square_feet']).mean():,.2f}" if 'square_feet' in df.columns and not df['square_feet'].isnull().all() else 'N/A',
            df['property_type'].mode()[0] if not df['property_type'].isnull().all() else 'N/A'
        ]
    }
    
    # Create statistics DataFrame
    stats_df = pd.DataFrame(stats)
    
    return stats_df

def calculate_price_per_sqft(df):
    """
    Calculate price per square foot for each property
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.Series: Series containing price per square foot values
    """
    # Create a copy to avoid warnings
    df_copy = df.copy()
    
    # Calculate price per square foot
    price_per_sqft = pd.Series(index=df_copy.index)
    
    # Only calculate for rows where both price and square_feet are available
    valid_rows = ~(df_copy['price'].isna() | df_copy['square_feet'].isna() | (df_copy['square_feet'] == 0))
    
    if valid_rows.any():
        price_per_sqft[valid_rows] = df_copy.loc[valid_rows, 'price'] / df_copy.loc[valid_rows, 'square_feet']
    
    return price_per_sqft

def group_properties_by_city(df):
    """
    Group properties by city and calculate statistics
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame grouped by city with statistics
    """
    if df.empty or 'city' not in df.columns:
        return pd.DataFrame()
    
    # Group by city and calculate statistics
    city_stats = df.groupby('city').agg({
        'price': ['mean', 'median', 'min', 'max', 'count'],
        'bedrooms': ['mean', 'median'],
        'bathrooms': ['mean', 'median'],
        'square_feet': ['mean', 'median']
    })
    
    # Flatten the MultiIndex columns
    city_stats.columns = ['_'.join(col).strip() for col in city_stats.columns.values]
    
    # Rename columns for clarity
    city_stats = city_stats.rename(columns={
        'price_mean': 'avg_price',
        'price_median': 'median_price',
        'price_min': 'min_price',
        'price_max': 'max_price',
        'price_count': 'num_listings',
        'bedrooms_mean': 'avg_bedrooms',
        'bedrooms_median': 'median_bedrooms',
        'bathrooms_mean': 'avg_bathrooms',
        'bathrooms_median': 'median_bathrooms',
        'square_feet_mean': 'avg_sqft',
        'square_feet_median': 'median_sqft'
    })
    
    return city_stats
