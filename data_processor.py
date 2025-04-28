import pandas as pd
import numpy as np
import re
from datetime import datetime

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

def validate_and_clean_data(df):
    """
    Validate and clean property data to ensure consistency and accuracy
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: Cleaned and validated DataFrame
    """
    if df.empty:
        return df
    
    # Create a copy to avoid modifying the original
    clean_df = df.copy()
    
    # Track validation results
    validation_log = []
    
    # Clean and standardize data
    clean_df = standardize_property_types(clean_df)
    clean_df = validate_and_clean_numeric_fields(clean_df)
    clean_df = clean_address_data(clean_df)
    clean_df = validate_and_clean_price(clean_df)
    clean_df = standardize_string_fields(clean_df)
    clean_df = handle_outliers(clean_df)
    clean_df = add_derived_fields(clean_df)
    
    # Add timestamp for when the validation was performed
    clean_df['validated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return clean_df

def standardize_property_types(df):
    """
    Standardize property type names to ensure consistency
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame with standardized property types
    """
    if 'property_type' not in df.columns:
        return df
    
    # Create a mapping of common variations to standard property types
    property_type_map = {
        # House variations
        'single family home': 'House',
        'single family': 'House',
        'single-family': 'House',
        'house': 'House',
        'home': 'House',
        'residential': 'House',
        
        # Condo variations
        'condo': 'Condo',
        'condominium': 'Condo',
        'apartment': 'Condo',
        'flat': 'Condo',
        
        # Townhouse variations
        'townhouse': 'Townhouse',
        'townhome': 'Townhouse',
        'town house': 'Townhouse',
        'town home': 'Townhouse',
        
        # Multi-family variations
        'multi family': 'Multi-Family',
        'multi-family': 'Multi-Family',
        'duplex': 'Multi-Family',
        'triplex': 'Multi-Family',
        'fourplex': 'Multi-Family',
        
        # Land variations
        'land': 'Land',
        'lot': 'Land',
        'vacant land': 'Land',
        'vacant lot': 'Land',
        
        # Commercial variations
        'commercial': 'Commercial',
        'office': 'Commercial',
        'retail': 'Commercial',
        'industrial': 'Commercial',
        'business': 'Commercial'
    }
    
    # Convert to lowercase for matching
    df['property_type_lower'] = df['property_type'].str.lower().fillna('')
    
    # Map to standardized types
    for key, value in property_type_map.items():
        mask = df['property_type_lower'].str.contains(key, na=False)
        df.loc[mask, 'property_type'] = value
    
    # Handle missing property types
    df.loc[df['property_type'].isna(), 'property_type'] = 'Unknown'
    
    # Drop the temporary lowercase column
    df = df.drop('property_type_lower', axis=1)
    
    return df

def validate_and_clean_numeric_fields(df):
    """
    Validate and clean numeric fields (bedrooms, bathrooms, square feet)
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame with cleaned numeric fields
    """
    # Handle bedrooms
    if 'bedrooms' in df.columns:
        # Convert to numeric, errors coerced to NaN
        df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce')
        
        # Set reasonable limits (0-20 bedrooms)
        df.loc[df['bedrooms'] < 0, 'bedrooms'] = np.nan
        df.loc[df['bedrooms'] > 20, 'bedrooms'] = np.nan
        
        # Convert to integer where possible
        df['bedrooms'] = df['bedrooms'].apply(lambda x: int(x) if pd.notnull(x) and x.is_integer() else x)
    
    # Handle bathrooms
    if 'bathrooms' in df.columns:
        # Convert to numeric, errors coerced to NaN
        df['bathrooms'] = pd.to_numeric(df['bathrooms'], errors='coerce')
        
        # Set reasonable limits (0-15 bathrooms)
        df.loc[df['bathrooms'] < 0, 'bathrooms'] = np.nan
        df.loc[df['bathrooms'] > 15, 'bathrooms'] = np.nan
    
    # Handle square feet
    if 'square_feet' in df.columns:
        # Extract numeric values if the field contains text
        if df['square_feet'].dtype == 'object':
            df['square_feet'] = df['square_feet'].apply(
                lambda x: re.sub(r'[^\d.]', '', str(x)) if pd.notnull(x) else x
            )
        
        # Convert to numeric, errors coerced to NaN
        df['square_feet'] = pd.to_numeric(df['square_feet'], errors='coerce')
        
        # Set reasonable limits (100-50,000 sqft for residential properties)
        df.loc[df['square_feet'] < 100, 'square_feet'] = np.nan
        df.loc[df['square_feet'] > 50000, 'square_feet'] = np.nan
    
    return df

def clean_address_data(df):
    """
    Clean and standardize address data
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame with cleaned address data
    """
    # Handle city names
    if 'city' in df.columns:
        # Capitalize city names
        df['city'] = df['city'].str.title()
        
        # Remove any numeric characters from city names
        df['city'] = df['city'].apply(
            lambda x: re.sub(r'[0-9]', '', str(x)) if pd.notnull(x) else x
        )
        
        # Trim whitespace
        df['city'] = df['city'].str.strip()
    
    # Handle state/province
    if 'state' in df.columns:
        # Uppercase state abbreviations
        df['state'] = df['state'].str.upper()
        
        # Trim whitespace
        df['state'] = df['state'].str.strip()
        
        # Ensure valid US states (optional, depending on your data)
        valid_states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
            'DC', 'PR'
        ]
        df.loc[~df['state'].isin(valid_states), 'state'] = np.nan
    
    # Handle zip codes
    if 'zip_code' in df.columns:
        # Extract numeric values
        df['zip_code'] = df['zip_code'].apply(
            lambda x: re.sub(r'[^0-9]', '', str(x))[:5] if pd.notnull(x) else x
        )
    
    return df

def validate_and_clean_price(df):
    """
    Validate and clean price data
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame with cleaned price data
    """
    if 'price' not in df.columns:
        return df
    
    # Extract numeric values if the field contains text
    if df['price'].dtype == 'object':
        df['price'] = df['price'].apply(
            lambda x: re.sub(r'[^\d.]', '', str(x)) if pd.notnull(x) else x
        )
    
    # Convert to numeric, errors coerced to NaN
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Handle unrealistic values
    # Minimum reasonable price (avoid free/error listings)
    df.loc[df['price'] < 10000, 'price'] = np.nan
    
    # Maximum reasonable price for typical residential property ($100M)
    df.loc[df['price'] > 100000000, 'price'] = np.nan
    
    return df

def standardize_string_fields(df):
    """
    Standardize string fields (title, description)
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame with standardized string fields
    """
    # Standardize title
    if 'title' in df.columns:
        # Ensure title is string type
        df['title'] = df['title'].astype(str)
        
        # Capitalize first letter of sentences
        df['title'] = df['title'].apply(
            lambda x: '. '.join(s.capitalize() for s in x.split('. ')) if pd.notnull(x) else x
        )
        
        # Trim whitespace
        df['title'] = df['title'].str.strip()
    
    # Standardize description
    if 'description' in df.columns:
        # Ensure description is string type
        df['description'] = df['description'].astype(str)
        
        # Replace multiple spaces with single space
        df['description'] = df['description'].apply(
            lambda x: re.sub(r'\s+', ' ', x) if pd.notnull(x) else x
        )
        
        # Trim whitespace
        df['description'] = df['description'].str.strip()
    
    # Standardize source
    if 'source' in df.columns:
        # Capitalize source names
        df['source'] = df['source'].str.capitalize()
        
        # Trim whitespace
        df['source'] = df['source'].str.strip()
    
    return df

def handle_outliers(df):
    """
    Identify and handle outliers in numeric data
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame with outliers handled
    """
    # Handle price outliers using IQR method
    if 'price' in df.columns and len(df) > 10:
        Q1 = df['price'].quantile(0.05)
        Q3 = df['price'].quantile(0.95)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - (1.5 * IQR)
        upper_bound = Q3 + (1.5 * IQR)
        
        # Flag outliers rather than removing them
        df['price_outlier'] = ((df['price'] < lower_bound) | (df['price'] > upper_bound))
    
    # Handle square_feet outliers
    if 'square_feet' in df.columns and len(df) > 10 and not df['square_feet'].isna().all():
        Q1 = df['square_feet'].quantile(0.05)
        Q3 = df['square_feet'].quantile(0.95)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - (1.5 * IQR)
        upper_bound = Q3 + (1.5 * IQR)
        
        # Flag outliers rather than removing them
        df['sqft_outlier'] = ((df['square_feet'] < lower_bound) | (df['square_feet'] > upper_bound))
    
    return df

def add_derived_fields(df):
    """
    Add useful derived fields based on existing data
    
    Args:
        df (pd.DataFrame): DataFrame containing property listings
        
    Returns:
        pd.DataFrame: DataFrame with additional derived fields
    """
    # Add price per square foot
    if 'price' in df.columns and 'square_feet' in df.columns:
        # Only calculate for valid data
        condition = (~df['price'].isna() & ~df['square_feet'].isna() & (df['square_feet'] > 0))
        
        if condition.any():
            df.loc[condition, 'price_per_sqft'] = df.loc[condition, 'price'] / df.loc[condition, 'square_feet']
    
    # Add price category
    if 'price' in df.columns:
        conditions = [
            df['price'] < 200000,
            (df['price'] >= 200000) & (df['price'] < 500000),
            (df['price'] >= 500000) & (df['price'] < 1000000),
            df['price'] >= 1000000
        ]
        
        choices = ['Budget', 'Mid-Range', 'High-End', 'Luxury']
        
        df['price_category'] = np.select(conditions, choices, default='Unknown')
    
    # Add property size category
    if 'square_feet' in df.columns:
        conditions = [
            df['square_feet'] < 1000,
            (df['square_feet'] >= 1000) & (df['square_feet'] < 2000),
            (df['square_feet'] >= 2000) & (df['square_feet'] < 3000),
            df['square_feet'] >= 3000
        ]
        
        choices = ['Small', 'Medium', 'Large', 'Very Large']
        
        df['size_category'] = np.select(conditions, choices, default='Unknown')
    
    # Add data quality score (simple version based on missing data)
    quality_columns = ['price', 'bedrooms', 'bathrooms', 'square_feet', 'address', 'city', 'state']
    quality_columns = [col for col in quality_columns if col in df.columns]
    
    if quality_columns:
        # Calculate percentage of non-null values for key fields
        df['data_quality_score'] = df[quality_columns].notnull().mean(axis=1) * 100
        # Round to integer
        df['data_quality_score'] = df['data_quality_score'].round().astype(int)
    
    # Add scrape date if it doesn't exist
    if 'scrape_date' not in df.columns:
        df['scrape_date'] = datetime.now().strftime('%Y-%m-%d')
    
    return df
