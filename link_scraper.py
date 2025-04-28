"""
Link Scraper Module

This module provides functions to scrape links from any website.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import random
import time
from urllib.parse import urljoin, urlparse

# List of user agents to rotate through
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
]

def get_random_user_agent():
    """Return a random user agent from the list"""
    return random.choice(USER_AGENTS)

def handle_request(url):
    """Make a request with error handling and random delays"""
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    # Random delay between 1-3 seconds to avoid being blocked
    time.sleep(random.uniform(1, 3))
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error requesting {url}: {e}")
        return None

def extract_domain(url):
    """Extract the domain from a URL"""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return domain

def clean_url(base_url, href):
    """Clean and normalize URLs"""
    # Join relative URLs with the base URL
    full_url = urljoin(base_url, href)
    
    # Remove URL fragments
    full_url = full_url.split('#')[0]
    
    # Remove URL parameters
    if '?' in full_url:
        full_url = full_url.split('?')[0]
    
    return full_url

def scrape_links(url, max_links=100, link_pattern=None, same_domain_only=True):
    """
    Scrape links from a website
    
    Args:
        url (str): URL to scrape links from
        max_links (int): Maximum number of links to scrape
        link_pattern (str, optional): Regex pattern to filter links by
        same_domain_only (bool): Only return links from the same domain
        
    Returns:
        pd.DataFrame: DataFrame containing scraped links with metadata
    """
    html_content = handle_request(url)
    if not html_content:
        return pd.DataFrame()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    base_domain = extract_domain(url)
    links_data = []
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag.get('href')
        if not href or href == "#" or href.startswith('javascript:'):
            continue
        
        # Clean the URL
        full_url = clean_url(url, href)
        
        # Apply domain filter if requested
        if same_domain_only and extract_domain(full_url) != base_domain:
            continue
        
        # Apply regex pattern filter if provided
        if link_pattern and not re.search(link_pattern, full_url):
            continue
        
        # Get link text and title
        link_text = a_tag.get_text().strip()
        link_title = a_tag.get('title', '')
        
        links_data.append({
            'url': full_url,
            'text': link_text,
            'title': link_title,
            'domain': extract_domain(full_url)
        })
        
        # Stop if we've reached the maximum number of links
        if len(links_data) >= max_links:
            break
    
    # Create DataFrame
    links_df = pd.DataFrame(links_data)
    
    # Remove duplicate URLs
    if not links_df.empty:
        links_df = links_df.drop_duplicates(subset=['url'])
    
    return links_df

def extract_specific_links(url, css_selector, max_links=100, link_pattern=None):
    """
    Extract links using a specific CSS selector
    
    Args:
        url (str): URL to scrape links from
        css_selector (str): CSS selector to find specific link elements
        max_links (int): Maximum number of links to scrape
        link_pattern (str, optional): Regex pattern to filter links by
        
    Returns:
        pd.DataFrame: DataFrame containing scraped links with metadata
    """
    html_content = handle_request(url)
    if not html_content:
        return pd.DataFrame()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    links_data = []
    
    for element in soup.select(css_selector):
        # Find the anchor tag if the selector didn't directly target it
        a_tag = element if element.name == 'a' else element.find('a')
        
        if not a_tag or not a_tag.has_attr('href'):
            continue
        
        href = a_tag.get('href')
        if not href or href == "#" or href.startswith('javascript:'):
            continue
        
        # Clean the URL
        full_url = clean_url(url, href)
        
        # Apply regex pattern filter if provided
        if link_pattern and not re.search(link_pattern, full_url):
            continue
        
        # Get link text and title
        link_text = a_tag.get_text().strip()
        link_title = a_tag.get('title', '')
        
        links_data.append({
            'url': full_url,
            'text': link_text,
            'title': link_title,
            'domain': extract_domain(full_url)
        })
        
        # Stop if we've reached the maximum number of links
        if len(links_data) >= max_links:
            break
    
    # Create DataFrame
    links_df = pd.DataFrame(links_data)
    
    # Remove duplicate URLs
    if not links_df.empty:
        links_df = links_df.drop_duplicates(subset=['url'])
    
    return links_df