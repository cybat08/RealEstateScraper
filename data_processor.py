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

def calculate_roi_metrics(property_data, rental_yield_percent=None, appreciation_rate=None, 
                down_payment_pct=20, interest_rate=4.5, loan_term_years=30, 
                vacancy_rate=5.0, property_tax_rate=1.2, insurance_rate=0.5, 
                maintenance_rate=1.0, property_mgmt_rate=8.0, monthly_utilities=0, 
                monthly_hoa=0, investment_horizon_years=5):
    """
    Calculate ROI metrics for a real estate property
    
    Args:
        property_data (pd.Series): Series containing property data
        rental_yield_percent (float, optional): Estimated annual rental yield as percentage
        appreciation_rate (float, optional): Estimated annual appreciation rate as percentage
        down_payment_pct (float): Down payment percentage
        interest_rate (float): Annual interest rate percentage
        loan_term_years (int): Loan term in years
        vacancy_rate (float): Vacancy rate percentage
        property_tax_rate (float): Annual property tax rate percentage
        insurance_rate (float): Annual insurance rate percentage
        maintenance_rate (float): Annual maintenance rate percentage
        property_mgmt_rate (float): Monthly property management fee percentage
        monthly_utilities (float): Monthly utilities cost in dollars
        monthly_hoa (float): Monthly HOA fees in dollars
        investment_horizon_years (int): Investment horizon in years
        
    Returns:
        dict: Dictionary containing ROI metrics
    """
    # Default values if not provided
    rental_yield = rental_yield_percent if rental_yield_percent is not None else estimate_rental_yield(property_data)
    appreciation = appreciation_rate if appreciation_rate is not None else estimate_appreciation_rate(property_data)
    
    # Get property price
    price = property_data['price'] if pd.notna(property_data['price']) else 0
    
    # Skip calculation if price is zero
    if price == 0:
        return {
            'rental_yield': None,
            'annual_rental_income': None,
            'cash_flow': None,
            'appreciation_rate': None,
            'five_year_value': None,
            'roi_5yr': None,
            'investment_recommendation': "Insufficient data for analysis"
        }
    
    # Calculate rental income
    annual_rental_income = (price * rental_yield) / 100
    monthly_rental_income = annual_rental_income / 12
    
    # Calculate expenses based on parameters
    # Vacancy loss
    vacancy_loss = monthly_rental_income * (vacancy_rate / 100)
    
    # Property tax (annual, converted to monthly)
    monthly_property_tax = (price * (property_tax_rate / 100)) / 12
    
    # Insurance (annual, converted to monthly)
    monthly_insurance = (price * (insurance_rate / 100)) / 12
    
    # Maintenance
    monthly_maintenance = (price * (maintenance_rate / 100)) / 12
    
    # Property management fee
    monthly_management = monthly_rental_income * (property_mgmt_rate / 100)
    
    # Total monthly expenses
    monthly_expenses = (
        vacancy_loss + 
        monthly_property_tax + 
        monthly_insurance + 
        monthly_maintenance + 
        monthly_management + 
        monthly_utilities + 
        monthly_hoa
    )
    
    # Calculate monthly mortgage payment using provided parameters
    down_payment = price * (down_payment_pct / 100)
    loan_amount = price - down_payment
    monthly_interest_rate = interest_rate / 100 / 12
    loan_term_months = loan_term_years * 12
    
    # Calculate mortgage payment using formula: P = L[i(1+i)^n]/[(1+i)^n-1]
    # Where P = payment, L = loan amount, i = monthly interest rate, n = number of payments
    if loan_amount > 0:
        mortgage_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** loan_term_months) / ((1 + monthly_interest_rate) ** loan_term_months - 1)
    else:
        mortgage_payment = 0
    
    # Calculate cash flow
    monthly_cash_flow = monthly_rental_income - monthly_expenses - mortgage_payment
    annual_cash_flow = monthly_cash_flow * 12
    
    # Calculate metrics for the investment horizon
    future_value = price * ((1 + appreciation / 100) ** investment_horizon_years)
    total_appreciation = future_value - price
    total_cash_flow = annual_cash_flow * investment_horizon_years
    
    # Calculate total ROI over the investment horizon
    total_investment = down_payment + (monthly_expenses * 12)  # Down payment + first year expenses
    total_roi = (total_appreciation + total_cash_flow) / total_investment * 100
    
    # Determine investment recommendation
    recommendation = ""
    if total_roi > 50:
        recommendation = "Excellent investment opportunity with strong returns"
    elif total_roi > 30:
        recommendation = "Good investment with solid potential returns"
    elif total_roi > 15:
        recommendation = "Average investment opportunity"
    elif total_roi > 0:
        recommendation = "Below average returns, consider negotiating price"
    else:
        recommendation = "Not recommended as an investment property"
    
    # Calculate additional metrics for display
    # Mortgage payment is calculated above
    monthly_expenses_for_display = monthly_expenses
    
    # Cap rate (annual net income / property value)
    cap_rate = (annual_rental_income - (monthly_expenses * 12)) / price * 100
    
    # Cash on cash return (annual cash flow / total cash invested)
    cash_on_cash_return = (annual_cash_flow / down_payment) * 100
    
    # Equity in 5 years (assuming linear equity growth from mortgage payments)
    # This is a simplification - actual equity growth depends on amortization schedule
    if loan_amount > 0:
        # Estimate principal portion of mortgage payment (increases over time, but simplified here)
        avg_principal_payment = loan_amount / (loan_term_months)
        equity_5yr = down_payment + (avg_principal_payment * min(60, loan_term_months)) + total_appreciation
    else:
        equity_5yr = price + total_appreciation
    
    # Calculate annualized ROI
    annualized_roi = ((1 + (total_roi / 100)) ** (1 / investment_horizon_years) - 1) * 100
    
    # Return metrics dictionary
    return {
        'rental_yield': rental_yield,
        'annual_rental_income': annual_rental_income,
        'monthly_cash_flow': monthly_cash_flow,
        'appreciation_rate': appreciation,
        'future_value': future_value,
        'roi': total_roi,
        'total_roi_pct': total_roi,  # For compatibility with existing code
        'investment_horizon': investment_horizon_years,
        'investment_recommendation': recommendation,
        'mortgage_payment': mortgage_payment,
        'monthly_expenses': monthly_expenses_for_display,
        'cap_rate': cap_rate,
        'cash_on_cash_return': cash_on_cash_return,
        'equity_5yr': equity_5yr,
        'annualized_roi': annualized_roi
    }

def estimate_rental_yield(property_data):
    """
    Estimate rental yield based on property characteristics
    
    Args:
        property_data (pd.Series): Series containing property data
        
    Returns:
        float: Estimated annual rental yield as percentage
    """
    # Base rental yield by property type
    base_yields = {
        'House': 5.0,
        'Condo': 5.5,
        'Townhouse': 5.2,
        'Multi-Family': 7.0,
        'Apartment': 6.0,
        'Land': 2.0,
        'Commercial': 8.0
    }
    
    # Get property type and set default yield
    property_type = property_data['property_type'] if pd.notna(property_data['property_type']) else 'House'
    rental_yield = base_yields.get(property_type, 5.0)
    
    # Adjust based on location (city)
    if 'city' in property_data and pd.notna(property_data['city']):
        city = property_data['city'].lower()
        # Higher yields in certain areas
        high_yield_cities = ['detroit', 'cleveland', 'memphis', 'birmingham', 'toledo']
        medium_yield_cities = ['atlanta', 'houston', 'dallas', 'phoenix', 'las vegas']
        low_yield_cities = ['san francisco', 'los angeles', 'new york', 'seattle', 'boston', 'miami']
        
        if any(city in c for c in high_yield_cities):
            rental_yield += 2.0
        elif any(city in c for c in medium_yield_cities):
            rental_yield += 0.5
        elif any(city in c for c in low_yield_cities):
            rental_yield -= 1.0
    
    # Adjust based on beds and baths
    if 'bedrooms' in property_data and pd.notna(property_data['bedrooms']):
        # 3-4 bedroom properties often have the best rental yields
        if 2 <= property_data['bedrooms'] <= 4:
            rental_yield += 0.3
        elif property_data['bedrooms'] > 4:
            rental_yield -= 0.2  # Luxury homes typically have lower yields
    
    # Cap the yield within reasonable range
    rental_yield = max(2.0, min(rental_yield, 12.0))
    
    return rental_yield

def estimate_appreciation_rate(property_data):
    """
    Estimate annual appreciation rate based on property characteristics
    
    Args:
        property_data (pd.Series): Series containing property data
        
    Returns:
        float: Estimated annual appreciation rate as percentage
    """
    # Base appreciation rate (national average)
    base_rate = 3.5
    
    # Adjust based on location
    if 'city' in property_data and pd.notna(property_data['city']):
        city = property_data['city'].lower()
        # Higher appreciation cities
        high_growth_cities = ['austin', 'nashville', 'raleigh', 'tampa', 'boise', 'phoenix', 'salt lake']
        medium_growth_cities = ['dallas', 'denver', 'atlanta', 'charlotte', 'houston', 'miami']
        low_growth_cities = ['buffalo', 'cleveland', 'detroit', 'baltimore', 'chicago', 'milwaukee']
        
        if any(city in c for c in high_growth_cities):
            base_rate += 2.0
        elif any(city in c for c in medium_growth_cities):
            base_rate += 1.0
        elif any(city in c for c in low_growth_cities):
            base_rate -= 0.5
    
    # Adjust based on property price vs area average
    if 'price_vs_median' in property_data and pd.notna(property_data['price_vs_median']):
        # Properties priced below market tend to appreciate faster
        if property_data['price_vs_median'] > 120:  # Priced 20% below market
            base_rate += 1.0
        elif property_data['price_vs_median'] > 110:  # Priced 10% below market
            base_rate += 0.5
        elif property_data['price_vs_median'] < 80:  # Priced 20% above market
            base_rate -= 0.5
    
    # Adjust based on property type
    if 'property_type' in property_data and pd.notna(property_data['property_type']):
        property_type = property_data['property_type']
        if property_type == 'Land':
            base_rate += 1.0  # Land can appreciate faster in growing areas
        elif property_type == 'Condo':
            base_rate -= 0.5  # Condos typically appreciate slower than single-family homes
    
    # Cap the appreciation rate within reasonable range
    appreciation_rate = max(1.0, min(base_rate, 7.0))
    
    return appreciation_rate

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
    
    # Add bedroom-to-bathroom ratio
    if 'bedrooms' in df.columns and 'bathrooms' in df.columns:
        condition = (~df['bedrooms'].isna() & ~df['bathrooms'].isna() & (df['bathrooms'] > 0))
        
        if condition.any():
            df.loc[condition, 'bed_bath_ratio'] = df.loc[condition, 'bedrooms'] / df.loc[condition, 'bathrooms']
            # Round to 2 decimal places
            df['bed_bath_ratio'] = df['bed_bath_ratio'].round(2)
    
    # Add value score (a composite metric combining multiple factors)
    value_columns = ['price_per_sqft', 'bedrooms', 'bathrooms', 'square_feet']
    value_columns = [col for col in value_columns if col in df.columns]
    
    if len(value_columns) >= 3:  # Need at least 3 factors to create a meaningful score
        # Create normalized versions of each column (0-100 scale)
        for col in value_columns:
            if col == 'price_per_sqft':
                # For price_per_sqft, lower is better, so invert the normalization
                if df[col].notna().any():
                    min_val = df[col].min()
                    max_val = df[col].max()
                    if max_val > min_val:
                        df[f'norm_{col}'] = 100 - (((df[col] - min_val) / (max_val - min_val)) * 100)
                    else:
                        df[f'norm_{col}'] = 50  # Default if all values are the same
            else:
                # For other metrics, higher is better
                if df[col].notna().any():
                    min_val = df[col].min()
                    max_val = df[col].max()
                    if max_val > min_val:
                        df[f'norm_{col}'] = ((df[col] - min_val) / (max_val - min_val)) * 100
                    else:
                        df[f'norm_{col}'] = 50  # Default if all values are the same
        
        # Calculate weighted average of normalized values
        norm_cols = [f'norm_{col}' for col in value_columns if f'norm_{col}' in df.columns]
        weights = {
            'norm_price_per_sqft': 0.4,  # Price per sqft is most important
            'norm_square_feet': 0.3,     # Square footage is second most important
            'norm_bedrooms': 0.15,       # Bedrooms
            'norm_bathrooms': 0.15       # Bathrooms
        }
        
        # Apply weights only to columns that exist
        valid_weights = {k: v for k, v in weights.items() if k in norm_cols}
        sum_weights = sum(valid_weights.values())
        
        if sum_weights > 0:
            df['value_score'] = 0
            for col, weight in valid_weights.items():
                df['value_score'] += df[col] * (weight / sum_weights)
            
            # Round to integer
            df['value_score'] = df['value_score'].round().astype('Int64')
            
            # Drop temporary normalization columns
            df = df.drop(columns=norm_cols, errors='ignore')
    
    # Add investment potential score
    if 'price' in df.columns and 'square_feet' in df.columns and 'city' in df.columns:
        # Group by city to get average price per sqft per city
        city_avg_price_sqft = df.groupby('city')['price_per_sqft'].median().reset_index()
        city_avg_price_sqft.columns = ['city', 'median_price_per_sqft']
        
        # Merge back to original dataframe
        df = df.merge(city_avg_price_sqft, on='city', how='left')
        
        # Calculate investment score based on how good the price is compared to city median
        condition = (~df['price_per_sqft'].isna() & ~df['median_price_per_sqft'].isna() & (df['median_price_per_sqft'] > 0))
        
        if condition.any():
            # If property price_per_sqft is less than city median, it's a better investment
            df.loc[condition, 'price_vs_median'] = (df.loc[condition, 'median_price_per_sqft'] / df.loc[condition, 'price_per_sqft']) * 100
            df['price_vs_median'] = df['price_vs_median'].round().astype('Int64')
            
            # Create investment score - higher means better value
            conditions = [
                df['price_vs_median'] > 120,  # Over 20% better than median
                (df['price_vs_median'] > 105) & (df['price_vs_median'] <= 120),  # 5-20% better than median
                (df['price_vs_median'] >= 95) & (df['price_vs_median'] <= 105),  # Within 5% of median
                (df['price_vs_median'] >= 80) & (df['price_vs_median'] < 95),  # 5-20% worse than median
                df['price_vs_median'] < 80  # Over 20% worse than median
            ]
            
            choices = ['Excellent', 'Good', 'Average', 'Below Average', 'Poor']
            df['investment_rating'] = np.select(conditions, choices, default='Unknown')
    
    # Add data quality score (enhanced version with weights for different fields)
    quality_columns = {
        'price': 0.20,
        'bedrooms': 0.15,
        'bathrooms': 0.15,
        'square_feet': 0.15,
        'address': 0.10,
        'city': 0.10,
        'property_type': 0.10,
        'state': 0.05
    }
    
    available_quality_columns = {col: weight for col, weight in quality_columns.items() if col in df.columns}
    
    if available_quality_columns:
        # Calculate weighted quality score
        df['data_quality_score'] = 0
        total_weight = sum(available_quality_columns.values())
        
        for col, weight in available_quality_columns.items():
            # Calculate percent non-null for this column
            non_null_pct = df[col].notnull().astype(int) * 100
            # Apply weight
            df['data_quality_score'] += non_null_pct * (weight / total_weight)
        
        # Round to integer
        df['data_quality_score'] = df['data_quality_score'].round().astype(int)
        
        # Add data quality category
        conditions = [
            df['data_quality_score'] >= 90,
            (df['data_quality_score'] >= 70) & (df['data_quality_score'] < 90),
            (df['data_quality_score'] >= 50) & (df['data_quality_score'] < 70),
            df['data_quality_score'] < 50
        ]
        
        choices = ['Excellent', 'Good', 'Fair', 'Poor']
        df['data_quality_category'] = np.select(conditions, choices, default='Unknown')
    
    # Add scrape date if it doesn't exist
    if 'scrape_date' not in df.columns:
        df['scrape_date'] = datetime.now().strftime('%Y-%m-%d')
    
    return df
