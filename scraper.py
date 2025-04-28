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

def handle_request(url, max_retries=2, use_proxy=False):
    """Make a request with error handling, random delays, and retry logic
    
    Args:
        url (str): URL to request
        max_retries (int): Maximum number of retry attempts (reduced for speed)
        use_proxy (bool): Whether to use a proxy service (for advanced usage)
        
    Returns:
        requests.Response: Response object if successful
        
    Raises:
        Exception: If all retry attempts fail
    """
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "dnt": "1"
    }
    
    # Add a random referrer from major sites
    referrers = [
        "https://www.google.com/",
        "https://www.bing.com/",
        "https://www.facebook.com/",
        "https://www.twitter.com/",
        "https://www.instagram.com/"
    ]
    headers["Referer"] = random.choice(referrers)
    
    # Add cookies to seem more like a real browser
    cookies = {
        "_ga": f"GA1.2.{random.randint(1000000, 9999999)}.{random.randint(1000000, 9999999)}",
        "_gid": f"GA1.2.{random.randint(1000000, 9999999)}.{random.randint(1000000, 9999999)}",
    }
    
    proxy = None
    if use_proxy:
        # This would use a proxy service in a production environment
        # For demo purposes, we're not implementing actual proxy usage
        pass
    
    for attempt in range(max_retries):
        try:
            # Add a smaller random delay between attempts
            # First attempt is fast, then increase for retries
            if attempt == 0:
                delay = random.uniform(0.1, 0.5)
            else:
                delay = random.uniform(1, 2) * attempt
            time.sleep(delay)
            
            # Make the request with a shorter timeout
            response = requests.get(
                url, 
                headers=headers, 
                cookies=cookies,
                proxies=proxy, 
                timeout=10
            )
            
            # If successful, return the response
            if response.status_code == 200:
                return response
            
            # If we get blocked (403), raise specific exception
            if response.status_code == 403:
                raise Exception(f"Access forbidden (403) for url: {url}")
                
            # For other status codes, try to raise for status
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            # If this was our last attempt, raise the exception
            if attempt == max_retries - 1:
                raise Exception(f"Request failed after {max_retries} attempts: {str(e)}")
            
            # Otherwise, try again with different parameters
            print(f"Request attempt {attempt + 1} failed: {str(e)}. Retrying...")
    
    # This should not be reached due to the exception in the loop
    raise Exception(f"Request failed after {max_retries} attempts due to unknown error")

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

def scrape_zillow(location, max_listings=20, min_price=0, max_price=None, min_beds=0, 
               min_baths=0, property_types=None, new_listings=False, include_sold=False, 
               include_pending=True):
    """
    Scrape real estate listings from Zillow with advanced filters
    
    Args:
        location (str): City, state or zip code
        max_listings (int): Maximum number of listings to scrape
        min_price (int): Minimum price filter
        max_price (int): Maximum price filter
        min_beds (int): Minimum number of bedrooms
        min_baths (int): Minimum number of bathrooms
        property_types (list): List of property types to include
        new_listings (bool): Whether to only show listings from the last 7 days
        include_sold (bool): Whether to include recently sold properties
        include_pending (bool): Whether to include pending/contingent listings
        
    Returns:
        pandas.DataFrame: DataFrame containing the scraped listings
    """
    # Format the location for the URL
    formatted_location = quote_plus(location)
    
    # Build URL with filters
    url = f"https://www.zillow.com/homes/"
    
    # Add status filters (for sale, sold, etc.)
    status_filters = ["for_sale"]
    if include_sold:
        status_filters.append("recently_sold")
    if include_pending:
        status_filters.append("pending")
    
    status_part = "-".join(status_filters)
    url += f"{status_part}/"
    
    # Add location
    url += f"{formatted_location}/"
    
    # Start building query parameters
    params = []
    
    # Add price range filter
    if min_price > 0 or max_price is not None:
        price_filter = f"price_{min_price}"
        if max_price is not None:
            price_filter += f"-{max_price}"
        else:
            price_filter += "-na"
        params.append(price_filter)
    
    # Add bedrooms filter
    if min_beds > 0:
        params.append(f"{min_beds}-_beds")
    
    # Add bathrooms filter
    if min_baths > 0:
        params.append(f"{min_baths}-_baths")
    
    # Add property type filter
    if property_types and len(property_types) > 0:
        # Map our property types to Zillow's
        zillow_property_map = {
            "House": "house",
            "Condo": "condo,apartment",
            "Townhouse": "townhouse",
            "Multi-Family": "multi_family",
            "Apartment": "apartment",
            "Land": "land",
            "Commercial": "commercial"
        }
        
        # Get Zillow property type codes
        property_codes = []
        for prop in property_types:
            if prop in zillow_property_map:
                property_codes.append(zillow_property_map[prop])
        
        if property_codes:
            params.append(f"type_{','.join(property_codes)}")
    
    # Add new listings filter (last 7 days)
    if new_listings:
        params.append("days_7")
    
    # Combine parameters
    if params:
        url += f"{'/'.join(params)}/"
    
    # Add trailing parts
    url += "_rb/"
    
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
                if link_elem and 'href' in link_elem.attrs:
                    href = link_elem['href']
                    # Handle both absolute and relative URLs
                    if isinstance(href, str) and href.startswith('http'):
                        link = href
                    elif isinstance(href, str):
                        link = f"https://www.zillow.com{href}"
                    else:
                        link = "N/A"
                else:
                    link = "N/A"
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
        error_message = f"Failed to scrape Zillow: {str(e)}"
        print(f"Debug: Error details for Zillow: {error_message}")
        
        # Explain to the user what happened
        if "403" in str(e):
            print("Zillow has detected and blocked our scraping attempt. This is a common issue as real estate sites have anti-scraping measures.")
            
        # Try falling back to sample data for the requested location
        print(f"Generating sample data for {location} as Zillow scraping failed.")
        return generate_sample_data(location, max_listings, source="Zillow (Sample)")

def scrape_realtor(location, max_listings=20, min_price=0, max_price=None, min_beds=0, 
               min_baths=0, property_types=None, new_listings=False, include_sold=False, 
               include_pending=True):
    """
    Scrape real estate listings from Realtor.com with advanced filters
    
    Args:
        location (str): City, state or zip code
        max_listings (int): Maximum number of listings to scrape
        min_price (int): Minimum price filter
        max_price (int): Maximum price filter
        min_beds (int): Minimum number of bedrooms
        min_baths (int): Minimum number of bathrooms
        property_types (list): List of property types to include
        new_listings (bool): Whether to only show listings from the last 7 days
        include_sold (bool): Whether to include recently sold properties
        include_pending (bool): Whether to include pending/contingent listings
        
    Returns:
        pandas.DataFrame: DataFrame containing the scraped listings
    """
    # Format the location for the URL
    formatted_location = quote_plus(location)
    
    # Build URL with filters
    base_url = "https://www.realtor.com/realestateandhomes-search/"
    url = base_url + formatted_location
    
    # Add query parameters
    params = []
    
    # Property status filter
    if include_sold and not include_pending:
        params.append(("prop_status", "recently_sold"))
    elif include_pending and not include_sold:
        params.append(("prop_status", "pending"))
    elif include_sold and include_pending:
        params.append(("prop_status", "recently_sold,pending,active"))
    
    # Price range filter
    if min_price > 0:
        params.append(("price_min", str(min_price)))
    if max_price is not None:
        params.append(("price_max", str(max_price)))
    
    # Bedrooms filter
    if min_beds > 0:
        params.append(("beds_min", str(min_beds)))
    
    # Bathrooms filter
    if min_baths > 0:
        params.append(("baths_min", str(min_baths)))
    
    # Property type filter
    if property_types and len(property_types) > 0:
        # Map our property types to Realtor.com's
        realtor_property_map = {
            "House": "single_family",
            "Condo": "condo",
            "Townhouse": "townhome",
            "Multi-Family": "multi_family",
            "Land": "land",
            "Commercial": "commercial"
        }
        
        # Get Realtor property type codes
        property_codes = []
        for prop in property_types:
            if prop in realtor_property_map:
                property_codes.append(realtor_property_map[prop])
        
        if property_codes:
            params.append(("prop_type", ",".join(property_codes)))
    
    # New listings filter (last 7 days)
    if new_listings:
        params.append(("age", "7"))
    
    # Add query parameters to URL
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params])
        url = f"{url}?{query_string}"
    
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
                if link_elem and 'href' in link_elem.attrs:
                    href = link_elem['href']
                    # Handle both absolute and relative URLs
                    if isinstance(href, str) and href.startswith('http'):
                        link = href
                    elif isinstance(href, str):
                        link = f"https://www.realtor.com{href}"
                    else:
                        link = "N/A"
                else:
                    link = "N/A"
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
        error_message = f"Failed to scrape Realtor.com: {str(e)}"
        print(f"Debug: Error details for Realtor.com: {error_message}")
        
        # Try falling back to sample data for the requested location
        print(f"Generating sample data for {location} as Realtor.com scraping failed.")
        return generate_sample_data(location, max_listings, source="Realtor (Sample)")

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

def scrape_trulia(location, max_listings=20, min_price=0, max_price=None, min_beds=0, 
               min_baths=0, property_types=None, new_listings=False, include_sold=False, 
               include_pending=True):
    """
    Scrape real estate listings from Trulia with advanced filters
    
    Args:
        location (str): City, state or zip code
        max_listings (int): Maximum number of listings to scrape
        min_price (int): Minimum price filter
        max_price (int): Maximum price filter
        min_beds (int): Minimum number of bedrooms
        min_baths (int): Minimum number of bathrooms
        property_types (list): List of property types to include
        new_listings (bool): Whether to only show listings from the last 7 days
        include_sold (bool): Whether to include recently sold properties
        include_pending (bool): Whether to include pending/contingent listings
        
    Returns:
        pandas.DataFrame: DataFrame containing the scraped listings
    """
    # Format the location for the URL
    formatted_location = quote_plus(location)
    
    # Base URL with property status
    url_type = "for_sale"
    if include_sold and not include_pending:
        url_type = "sold"
    elif include_pending and not include_sold:
        url_type = "sold_pending"
    
    # Start building the URL
    url = f"https://www.trulia.com/{url_type}/{formatted_location}/"
    
    # Add property type filters
    property_type_string = ""
    
    if property_types and len(property_types) > 0:
        # Map our property types to Trulia's format
        trulia_property_map = {
            "House": "SINGLE-FAMILY_HOME",
            "Condo": "CONDO",
            "Townhouse": "TOWNHOUSE",
            "Multi-Family": "MULTI-FAMILY",
            "Land": "LAND",
            "Commercial": "COMMERCIAL",
            "Apartment": "APARTMENT"
        }
        
        # Get Trulia property type codes
        property_codes = []
        for prop in property_types:
            if prop in trulia_property_map:
                property_codes.append(trulia_property_map[prop])
        
        if property_codes:
            property_type_string = ",".join(property_codes) + "_type/"
    else:
        # Default to common property types
        property_type_string = "SINGLE-FAMILY_HOME,TOWNHOUSE,CONDO_type/"
    
    # Add property types to URL
    url += property_type_string
    
    # Build query parameters for additional filters
    params = []
    
    # Price range filter
    if min_price > 0:
        params.append(f"price_min={min_price}")
    if max_price is not None:
        params.append(f"price_max={max_price}")
    
    # Bedroom filter
    if min_beds > 0:
        params.append(f"beds_min={min_beds}")
    
    # Bathroom filter
    if min_baths > 0:
        params.append(f"baths_min={min_baths}")
    
    # New listings filter
    if new_listings:
        params.append("market=new-listings")
    
    # Add query parameters to URL
    if params:
        url += "?" + "&".join(params)
    
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
                if link_elem and 'href' in link_elem.attrs:
                    href = link_elem['href']
                    # Handle both absolute and relative URLs
                    if isinstance(href, str) and href.startswith('http'):
                        link = href
                    elif isinstance(href, str):
                        link = f"https://www.trulia.com{href}"
                    else:
                        link = "N/A"
                else:
                    link = "N/A"
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
        error_message = f"Failed to scrape Trulia: {str(e)}"
        print(f"Debug: Error details for Trulia: {error_message}")
        
        # Try falling back to sample data for the requested location
        print(f"Generating sample data for {location} as Trulia scraping failed.")
        return generate_sample_data(location, max_listings, source="Trulia (Sample)")

def scrape_redfin(location, max_listings=20, min_price=0, max_price=None, min_beds=0, 
             min_baths=0, property_types=None, new_listings=False, include_sold=False, 
             include_pending=True):
    """
    Scrape real estate listings from Redfin with advanced filters
    
    Args:
        location (str): City, state or zip code
        max_listings (int): Maximum number of listings to scrape
        min_price (int): Minimum price filter
        max_price (int): Maximum price filter
        min_beds (int): Minimum number of bedrooms
        min_baths (int): Minimum number of bathrooms
        property_types (list): List of property types to include
        new_listings (bool): Whether to only show listings from the last 7 days
        include_sold (bool): Whether to include recently sold properties
        include_pending (bool): Whether to include pending/contingent listings
        
    Returns:
        pandas.DataFrame: DataFrame containing the scraped listings
    """
    # Format the location for the URL
    formatted_location = quote_plus(location)
    
    # Build base URL
    base_url = "https://www.redfin.com/city/"
    
    # Start with a search URL that should work for most locations
    url = f"https://www.redfin.com/search/real-estate-in-{formatted_location}"
    
    # Build filter parameters
    params = []
    
    # Price filter
    if min_price > 0 or max_price is not None:
        price_param = f"min-price={min_price}"
        if max_price is not None:
            price_param += f",max-price={max_price}"
        params.append(price_param)
    
    # Beds filter
    if min_beds > 0:
        params.append(f"min-beds={min_beds}")
    
    # Baths filter
    if min_baths > 0:
        params.append(f"min-baths={min_baths}")
    
    # Property type filter
    if property_types:
        # Convert our property types to Redfin's format
        redfin_property_map = {
            'House': 'house',
            'Condo': 'condo',
            'Townhouse': 'townhome',
            'Multi-Family': 'multifamily',
            'Land': 'land',
            'Apartment': 'apartment'
        }
        
        redfin_types = [redfin_property_map.get(pt, '') for pt in property_types if pt in redfin_property_map]
        if redfin_types:
            property_param = f"property-type={','.join(redfin_types)}"
            params.append(property_param)
    
    # New listings filter
    if new_listings:
        params.append("include=new-listings")
    
    # Status filter (sold, pending)
    status_types = ["active"]
    if include_sold:
        status_types.append("sold-3mo") # Sold in last 3 months
    if include_pending:
        status_types.append("pending")
    
    params.append(f"status={','.join(status_types)}")
    
    # Add parameters to URL
    if params:
        url += "/filter/" + ";".join(params)
    
    try:
        # Make the request with extra precautions for Redfin
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/",
            "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        
        # Use sessions for better cookie handling
        session = requests.Session()
        for key, value in headers.items():
            session.headers[key] = value
        
        response = session.get(url, timeout=15)
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all property cards
        property_cards = soup.select('.HomeCardContainer')
        
        # Limit to the maximum number requested
        property_cards = property_cards[:max_listings]
        
        # Initialize lists to store property details
        addresses = []
        prices = []
        bedrooms = []
        bathrooms = []
        square_feet = []
        property_types = []
        links = []
        cities = []
        
        # Extract data from each property card
        for card in property_cards:
            try:
                # Extract price
                price_elem = card.select_one('.homecardV2Price')
                price = clean_price(price_elem.text) if price_elem else None
                prices.append(price)
                
                # Extract address
                address_parts = []
                street_elem = card.select_one('.displayAddressLine')
                if street_elem:
                    address_parts.append(street_elem.text.strip())
                
                city_state_elem = card.select_one('.cityStateAddress')
                if city_state_elem:
                    address_parts.append(city_state_elem.text.strip())
                
                address = ", ".join(address_parts) if address_parts else "N/A"
                addresses.append(address)
                
                # Extract city from address
                city = "N/A"
                if ',' in address:
                    city_parts = address.split(',')
                    if len(city_parts) > 1:
                        city = city_parts[1].strip()
                cities.append(city)
                
                # Extract details (beds, baths, sqft)
                beds = None
                baths = None
                sqft = None
                
                stats_elem = card.select_one('.HomeStatsV2')
                if stats_elem:
                    stats_text = stats_elem.text.lower()
                    
                    # Extract beds
                    beds_match = re.search(r'(\d+\.?\d*)\s*bed', stats_text)
                    if beds_match:
                        beds = float(beds_match.group(1))
                    
                    # Extract baths
                    baths_match = re.search(r'(\d+\.?\d*)\s*bath', stats_text)
                    if baths_match:
                        baths = float(baths_match.group(1))
                    
                    # Extract square feet
                    sqft_match = re.search(r'(\d+[,\d]*)\s*sq ?ft', stats_text)
                    if sqft_match:
                        sqft = float(sqft_match.group(1).replace(',', ''))
                
                bedrooms.append(beds)
                bathrooms.append(baths)
                square_feet.append(sqft)
                
                # Extract property type
                property_type_elem = card.select_one('.propertyType')
                property_type = property_type_elem.text.strip() if property_type_elem else "House"
                
                # Standardize property type
                if property_type:
                    property_type = property_type.title()
                property_types.append(property_type)
                
                # Extract link
                link_elem = card.select_one('a.link-to-home-details')
                if link_elem and 'href' in link_elem.attrs:
                    link = f"https://www.redfin.com{link_elem['href']}"
                else:
                    link = "N/A"
                links.append(link)
                
            except Exception as e:
                print(f"Error parsing Redfin property card: {str(e)}")
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
        error_message = f"Failed to scrape Redfin: {str(e)}"
        print(f"Debug: Error details for Redfin: {error_message}")
        
        # Try falling back to sample data for the requested location
        print(f"Generating sample data for {location} as Redfin scraping failed.")
        return generate_sample_data(location, max_listings, source="Redfin (Sample)")

def scrape_homes_com(location, max_listings=20, min_price=0, max_price=None, min_beds=0, 
               min_baths=0, property_types=None, new_listings=False, include_sold=False, 
               include_pending=True):
    """
    Scrape real estate listings from Homes.com with advanced filters
    
    Args:
        location (str): City, state or zip code
        max_listings (int): Maximum number of listings to scrape
        min_price (int): Minimum price filter
        max_price (int): Maximum price filter
        min_beds (int): Minimum number of bedrooms
        min_baths (int): Minimum number of bathrooms
        property_types (list): List of property types to include
        new_listings (bool): Whether to only show listings from the last 7 days
        include_sold (bool): Whether to include recently sold properties
        include_pending (bool): Whether to include pending/contingent listings
        
    Returns:
        pandas.DataFrame: DataFrame containing the scraped listings
    """
    # Format the location for the URL
    formatted_location = quote_plus(location)
    
    # Build base URL
    url = f"https://www.homes.com/for-sale/{formatted_location}/"
    
    # Add filters
    filter_parts = []
    
    # Price filter
    if min_price > 0:
        filter_parts.append(f"min-price-{min_price}")
    if max_price is not None:
        filter_parts.append(f"max-price-{max_price}")
    
    # Beds filter
    if min_beds > 0:
        filter_parts.append(f"min-beds-{min_beds}")
    
    # Baths filter
    if min_baths > 0:
        filter_parts.append(f"min-baths-{min_baths}")
    
    # Property type filter
    if property_types:
        # Convert our property types to Homes.com format
        homes_property_map = {
            'House': 'single-family',
            'Condo': 'condos-townhomes',
            'Townhouse': 'condos-townhomes',
            'Multi-Family': 'multi-family',
            'Land': 'land',
            'Apartment': 'condos-townhomes'
        }
        
        homes_types = []
        for pt in property_types:
            mapped_type = homes_property_map.get(pt)
            if mapped_type and mapped_type not in homes_types:
                homes_types.append(mapped_type)
        
        if homes_types:
            for property_type in homes_types:
                filter_parts.append(f"property-type-{property_type}")
    
    # Add status filters
    if include_sold:
        filter_parts.append("include-sold")
    if include_pending:
        filter_parts.append("include-pending")
    
    # Add new listings filter
    if new_listings:
        filter_parts.append("new-7-days")
    
    # Complete the URL with filters
    if filter_parts:
        url += "/".join(filter_parts) + "/"
    
    try:
        # Make the request
        response = handle_request(url)
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all property cards
        property_cards = soup.select('.for-sale-card')
        
        # Limit to maximum number requested
        property_cards = property_cards[:max_listings]
        
        # Initialize lists to store property details
        addresses = []
        prices = []
        bedrooms = []
        bathrooms = []
        square_feet = []
        property_types = []
        links = []
        cities = []
        
        # Extract data from each property card
        for card in property_cards:
            try:
                # Extract price
                price_elem = card.select_one('.price')
                price = clean_price(price_elem.text) if price_elem else None
                prices.append(price)
                
                # Extract address
                street_elem = card.select_one('.street-address')
                locality_elem = card.select_one('.locality')
                region_elem = card.select_one('.region')
                
                address_parts = []
                if street_elem:
                    address_parts.append(street_elem.text.strip())
                
                location_parts = []
                if locality_elem:
                    location_parts.append(locality_elem.text.strip())
                if region_elem:
                    location_parts.append(region_elem.text.strip())
                
                if location_parts:
                    address_parts.append(", ".join(location_parts))
                
                address = ", ".join(address_parts) if address_parts else "N/A"
                addresses.append(address)
                
                # Extract city
                city = "N/A"
                if locality_elem:
                    city = locality_elem.text.strip()
                cities.append(city)
                
                # Extract details (beds, baths, sqft)
                beds = None
                baths = None
                sqft = None
                
                details_elems = card.select('.property-details-value')
                details_labels = card.select('.property-details-label')
                
                for i, label_elem in enumerate(details_labels):
                    if i < len(details_elems):
                        label = label_elem.text.lower().strip()
                        value = details_elems[i].text.strip()
                        
                        if 'bed' in label:
                            beds = extract_number(value)
                        elif 'bath' in label:
                            baths = extract_number(value)
                        elif 'sq ft' in label or 'sqft' in label:
                            sqft = extract_number(value)
                
                bedrooms.append(beds)
                bathrooms.append(baths)
                square_feet.append(sqft)
                
                # Extract property type
                property_type_elem = card.select_one('.property-type')
                property_type = property_type_elem.text.strip() if property_type_elem else "House"
                
                # Standardize property type
                if property_type:
                    property_type = property_type.title()
                    # Map Homes.com types to our standard types
                    if 'Single Family' in property_type:
                        property_type = 'House'
                    elif 'Condo' in property_type or 'Town' in property_type:
                        property_type = 'Condo'
                
                property_types.append(property_type)
                
                # Extract link
                link_elem = card.select_one('a.for-sale-card-link')
                if link_elem and 'href' in link_elem.attrs:
                    link = f"https://www.homes.com{link_elem['href']}"
                else:
                    link = "N/A"
                links.append(link)
                
            except Exception as e:
                print(f"Error parsing Homes.com property card: {str(e)}")
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
        
        # Add data quality score
        if not df.empty and 'data_quality_score' not in df.columns:
            df['data_quality_score'] = df.apply(lambda row: calculate_data_quality(row), axis=1)
        
        return df
    
    except Exception as e:
        error_message = f"Failed to scrape Homes.com: {str(e)}"
        print(f"Debug: Error details for Homes.com: {error_message}")
        
        # Try falling back to sample data for the requested location
        print(f"Generating sample data for {location} as Homes.com scraping failed.")
        return generate_sample_data(location, max_listings, source="Homes.com (Sample)")
