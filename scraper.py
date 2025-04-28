import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import random
import time
import re
import datetime
from urllib.parse import quote_plus

# User agents to rotate for avoiding detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15"
]

def get_random_user_agent():
    """Return a random user agent from the list"""
    return random.choice(USER_AGENTS)

def handle_request(url):
    """Make a request with error handling and random delays"""
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }
    
    # Add a random delay to avoid rate limiting
    time.sleep(random.uniform(1, 3))
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {str(e)}")

def clean_price(price_str):
    """Extract and clean price from various formats"""
    if not price_str:
        return None
    
    # Remove non-numeric characters except for decimal points
    price_str = re.sub(r'[^\d.]', '', price_str)
    
    try:
        return float(price_str)
    except ValueError:
        return None

def extract_number(text, pattern=r'\d+'):
    """Extract numbers from text using regex pattern"""
    if not text:
        return None
    
    match = re.search(pattern, text)
    if match:
        return float(match.group())
    return None

def scrape_zillow(location, max_listings=20):
    """
    Scrape real estate listings from Zillow
    
    Args:
        location (str): City, state or zip code
        max_listings (int): Maximum number of listings to scrape
        
    Returns:
        pandas.DataFrame: DataFrame containing the scraped listings
    """
    # Format the location for the URL
    formatted_location = quote_plus(location)
    url = f"https://www.zillow.com/homes/for_sale/{formatted_location}_rb/"
    
    try:
        response = handle_request(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all property listing cards
        listing_cards = soup.select('div[data-test="property-card"]')
        
        # Initialize lists to store property details
        addresses = []
        prices = []
        bedrooms = []
        bathrooms = []
        square_feet = []
        property_types = []
        links = []
        cities = []
        
        # Extract data from each listing card (up to max_listings)
        for card in listing_cards[:max_listings]:
            try:
                # Extract address
                address_elem = card.select_one('address')
                address = address_elem.text.strip() if address_elem else "N/A"
                addresses.append(address)
                
                # Extract city from address (usually after the comma)
                city = "N/A"
                if ',' in address:
                    city = address.split(',')[0].strip()
                cities.append(city)
                
                # Extract price
                price_elem = card.select_one('[data-test="property-card-price"]')
                price_text = price_elem.text.strip() if price_elem else "N/A"
                prices.append(clean_price(price_text))
                
                # Extract bedrooms, bathrooms, and square feet
                details_elem = card.select_one('[data-test="property-card-details"]')
                details_text = details_elem.text.strip() if details_elem else ""
                
                # Extract bedrooms
                bed_match = re.search(r'(\d+)\s*bd', details_text)
                bedrooms.append(float(bed_match.group(1)) if bed_match else None)
                
                # Extract bathrooms
                bath_match = re.search(r'(\d+(?:\.\d+)?)\s*ba', details_text)
                bathrooms.append(float(bath_match.group(1)) if bath_match else None)
                
                # Extract square feet
                sqft_match = re.search(r'([\d,]+)\s*sqft', details_text)
                sqft = sqft_match.group(1).replace(',', '') if sqft_match else None
                square_feet.append(float(sqft) if sqft else None)
                
                # Extract property type
                property_type_elem = card.select_one('[data-test="property-card-home-type"]')
                property_type = property_type_elem.text.strip() if property_type_elem else "House"
                property_types.append(property_type)
                
                # Extract link
                link_elem = card.select_one('a[data-test="property-card-link"]')
                link = "https://www.zillow.com" + link_elem['href'] if link_elem and 'href' in link_elem.attrs else "N/A"
                links.append(link)
                
            except Exception as e:
                # Skip this listing if there's an error processing it
                print(f"Error processing Zillow listing: {str(e)}")
                continue
        
        # Create DataFrame
        data = {
            'address': addresses,
            'city': cities,
            'price': prices,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'square_feet': square_feet,
            'property_type': property_types,
            'link': links
        }
        
        df = pd.DataFrame(data)
        return df
    
    except Exception as e:
        raise Exception(f"Failed to scrape Zillow: {str(e)}")

def scrape_realtor(location, max_listings=20):
    """
    Scrape real estate listings from Realtor.com
    
    Args:
        location (str): City, state or zip code
        max_listings (int): Maximum number of listings to scrape
        
    Returns:
        pandas.DataFrame: DataFrame containing the scraped listings
    """
    # Format the location for the URL
    formatted_location = quote_plus(location)
    url = f"https://www.realtor.com/realestateandhomes-search/{formatted_location}"
    
    try:
        response = handle_request(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all property listing cards
        listing_cards = soup.select('div[data-testid="property-card"]')
        
        # Initialize lists to store property details
        addresses = []
        prices = []
        bedrooms = []
        bathrooms = []
        square_feet = []
        property_types = []
        links = []
        cities = []
        
        # Extract data from each listing card (up to max_listings)
        for card in listing_cards[:max_listings]:
            try:
                # Extract address
                address_elem = card.select_one('[data-testid="card-address"]')
                address = address_elem.text.strip() if address_elem else "N/A"
                addresses.append(address)
                
                # Extract city from address (usually after the comma)
                city = "N/A"
                if ',' in address:
                    city = address.split(',')[1].strip()
                cities.append(city)
                
                # Extract price
                price_elem = card.select_one('[data-testid="card-price"]')
                price_text = price_elem.text.strip() if price_elem else "N/A"
                prices.append(clean_price(price_text))
                
                # Extract bedrooms
                beds_elem = card.select_one('[data-testid="property-meta-beds"]')
                beds_text = beds_elem.text.strip() if beds_elem else "N/A"
                bedrooms.append(extract_number(beds_text))
                
                # Extract bathrooms
                baths_elem = card.select_one('[data-testid="property-meta-baths"]')
                baths_text = baths_elem.text.strip() if baths_elem else "N/A"
                bathrooms.append(extract_number(baths_text))
                
                # Extract square feet
                sqft_elem = card.select_one('[data-testid="property-meta-sqft"]')
                sqft_text = sqft_elem.text.strip() if sqft_elem else "N/A"
                sqft = re.sub(r'[^\d.]', '', sqft_text) if sqft_text != "N/A" else None
                square_feet.append(float(sqft) if sqft else None)
                
                # Extract property type
                property_type_elem = card.select_one('[data-testid="property-type"]')
                property_type = property_type_elem.text.strip() if property_type_elem else "House"
                property_types.append(property_type)
                
                # Extract link
                link_elem = card.select_one('a[data-testid="property-anchor"]')
                link = "https://www.realtor.com" + link_elem['href'] if link_elem and 'href' in link_elem.attrs else "N/A"
                links.append(link)
                
            except Exception as e:
                # Skip this listing if there's an error processing it
                print(f"Error processing Realtor.com listing: {str(e)}")
                continue
        
        # Create DataFrame
        data = {
            'address': addresses,
            'city': cities,
            'price': prices,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'square_feet': square_feet,
            'property_type': property_types,
            'link': links
        }
        
        df = pd.DataFrame(data)
        return df
    
    except Exception as e:
        raise Exception(f"Failed to scrape Realtor.com: {str(e)}")

def generate_sample_data(location, num_listings=10, source="Sample"):
    """
    Generate sample property data for testing when real scraping fails
    
    Args:
        location (str): Location string to include in the addresses
        num_listings (int): Number of sample listings to generate
        source (str): Name of the source to include
        
    Returns:
        pandas.DataFrame: DataFrame containing sample property listings
    """
    # Extract city name from location for more realistic data
    city = location.split(',')[0].strip() if ',' in location else location
    
    # Lists to store property data
    addresses = []
    cities = []
    prices = []
    bedrooms = []
    bathrooms = []
    square_feet = []
    property_types = []
    links = []
    
    # Property type options
    prop_types = ["House", "Condo", "Townhouse", "Multi-Family", "Land"]
    
    # Street names for variety
    street_names = ["Main St", "Oak Ave", "Maple Dr", "Washington Blvd", "Cedar Ln", 
                   "Park Ave", "Lake Dr", "Forest Rd", "Sunset Blvd", "River Rd"]
    
    # Generate random properties
    for i in range(num_listings):
        # Generate address
        house_num = random.randint(100, 9999)
        street = random.choice(street_names)
        address = f"{house_num} {street}, {city}"
        addresses.append(address)
        
        # Use the provided city
        cities.append(city)
        
        # Generate price (between $100k and $1.5M)
        price = random.randint(100000, 1500000)
        prices.append(price)
        
        # Generate bedrooms (1-6)
        bedroom = random.randint(1, 6)
        bedrooms.append(bedroom)
        
        # Generate bathrooms (1-4.5)
        bathroom = round(random.uniform(1, 4.5) * 2) / 2  # Round to nearest 0.5
        bathrooms.append(bathroom)
        
        # Generate square feet (800-5000)
        sqft = random.randint(800, 5000)
        square_feet.append(sqft)
        
        # Select property type
        property_type = random.choice(prop_types)
        property_types.append(property_type)
        
        # Generate fake link
        link = f"https://example.com/property/{source.lower()}/{i}"
        links.append(link)
    
    # Create DataFrame
    data = {
        'address': addresses,
        'city': cities,
        'price': prices,
        'bedrooms': bedrooms,
        'bathrooms': bathrooms,
        'square_feet': square_feet,
        'property_type': property_types,
        'link': links
    }
    
    return pd.DataFrame(data)

def scrape_trulia(location, max_listings=20):
    """
    Scrape real estate listings from Trulia
    
    Args:
        location (str): City, state or zip code
        max_listings (int): Maximum number of listings to scrape
        
    Returns:
        pandas.DataFrame: DataFrame containing the scraped listings
    """
    # Format the location for the URL
    formatted_location = quote_plus(location)
    url = f"https://www.trulia.com/for_sale/{formatted_location}/SINGLE-FAMILY_HOME,TOWNHOUSE_type/"
    
    try:
        response = handle_request(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all property listing cards
        listing_cards = soup.select('div[data-testid="home-card-container"]')
        
        # Initialize lists to store property details
        addresses = []
        prices = []
        bedrooms = []
        bathrooms = []
        square_feet = []
        property_types = []
        links = []
        cities = []
        
        # Extract data from each listing card (up to max_listings)
        for card in listing_cards[:max_listings]:
            try:
                # Extract address
                address_elem = card.select_one('[data-testid="property-address"]')
                address = address_elem.text.strip() if address_elem else "N/A"
                addresses.append(address)
                
                # Extract city from address (usually after the comma)
                city = "N/A"
                if ',' in address:
                    city = address.split(',')[1].strip()
                cities.append(city)
                
                # Extract price
                price_elem = card.select_one('[data-testid="property-price"]')
                price_text = price_elem.text.strip() if price_elem else "N/A"
                prices.append(clean_price(price_text))
                
                # Extract bedrooms, bathrooms, and square feet from property details
                details_elem = card.select_one('[data-testid="property-beds-baths"]')
                details_text = details_elem.text.strip() if details_elem else ""
                
                # Extract bedrooms
                bed_match = re.search(r'(\d+)\s*(?:bd|bed)', details_text)
                bedrooms.append(float(bed_match.group(1)) if bed_match else None)
                
                # Extract bathrooms
                bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ba|bath)', details_text)
                bathrooms.append(float(bath_match.group(1)) if bath_match else None)
                
                # Extract square feet
                sqft_elem = card.select_one('[data-testid="property-floorSpace"]')
                sqft_text = sqft_elem.text.strip() if sqft_elem else "N/A"
                sqft = re.sub(r'[^\d.]', '', sqft_text) if sqft_text != "N/A" else None
                square_feet.append(float(sqft) if sqft else None)
                
                # Extract property type (Trulia doesn't always show this explicitly)
                property_type = "House"  # Default to House if not found
                if "condo" in details_text.lower():
                    property_type = "Condo"
                elif "townhouse" in details_text.lower():
                    property_type = "Townhouse"
                property_types.append(property_type)
                
                # Extract link
                link_elem = card.select_one('a[data-testid="property-card-link"]')
                link = "https://www.trulia.com" + link_elem['href'] if link_elem and 'href' in link_elem.attrs else "N/A"
                links.append(link)
                
            except Exception as e:
                # Skip this listing if there's an error processing it
                print(f"Error processing Trulia listing: {str(e)}")
                continue
        
        # Create DataFrame
        data = {
            'address': addresses,
            'city': cities,
            'price': prices,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'square_feet': square_feet,
            'property_type': property_types,
            'link': links
        }
        
        df = pd.DataFrame(data)
        return df
    
    except Exception as e:
        raise Exception(f"Failed to scrape Trulia: {str(e)}")
