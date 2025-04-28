import trafilatura


def get_website_text_content(url: str) -> str:
    """
    This function takes a url and returns the main text content of the website.
    The text content is extracted using trafilatura and easier to understand.
    The results are not directly readable, better to be summarized by LLM before consume
    by the user.

    Args:
        url (str): The URL of the website to extract content from
        
    Returns:
        str: Extracted main content from the website
    """
    # Send a request to the website
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded)
    return text


def extract_property_details(url: str) -> dict:
    """
    Extract more detailed information about a specific property listing.
    
    Args:
        url (str): URL to the property listing detail page
        
    Returns:
        dict: Dictionary containing extracted property details
    """
    # Get the full text content
    content = get_website_text_content(url)
    
    if not content:
        return {"error": "Failed to extract content"}
    
    # Return both the raw content and some basic structure
    return {
        "full_description": content,
        "content_length": len(content),
        "url": url
    }