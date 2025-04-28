import streamlit as st
import pandas as pd
import plotly.express as px
import time
from scraper import scrape_zillow, scrape_realtor, scrape_trulia
from data_processor import filter_properties, get_statistics
from utils import get_unique_values, format_price, display_property_card
from web_content import extract_property_details

# Configure the page
st.set_page_config(
    page_title="Real Estate Scraper",
    page_icon="🏠",
    layout="wide"
)

# Initialize session states
if 'properties_df' not in st.session_state:
    st.session_state.properties_df = pd.DataFrame()

if 'scrape_status' not in st.session_state:
    st.session_state.scrape_status = ""
    
if 'selected_property' not in st.session_state:
    st.session_state.selected_property = None

# Title and description
st.title("🏠 Real Estate Listings Scraper")
st.markdown("""
This app scrapes real estate listings from popular websites and allows you to filter and analyze the results.
""")

# Sidebar for scraping controls
st.sidebar.header("Scraper Controls")

# Website selection
websites = st.sidebar.multiselect(
    "Select websites to scrape",
    ["Zillow", "Realtor.com", "Trulia"],
    default=["Zillow"]
)

# Location input
location = st.sidebar.text_input("Location (city, state or zip code)", "Seattle, WA")

# Number of listings to scrape
num_listings = st.sidebar.slider("Maximum number of listings to scrape per site", 5, 100, 20)

# Scrape button
scrape_button = st.sidebar.button("Scrape Listings")

# Handle scraping process
if scrape_button:
    if not websites:
        st.sidebar.error("Please select at least one website to scrape")
    elif not location:
        st.sidebar.error("Please enter a location")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize empty dataframe to store all listings
        all_listings = pd.DataFrame()
        
        # Initialize counters for progress bar
        total_sites = len(websites)
        sites_completed = 0
        
        # Scrape each selected website
        for website in websites:
            status_text.text(f"Scraping {website}...")
            
            try:
                if website == "Zillow":
                    new_listings = scrape_zillow(location, num_listings)
                elif website == "Realtor.com":
                    new_listings = scrape_realtor(location, num_listings)
                elif website == "Trulia":
                    new_listings = scrape_trulia(location, num_listings)
                
                if not new_listings.empty:
                    # Add a source column
                    new_listings['source'] = website
                    # Append to the main dataframe
                    all_listings = pd.concat([all_listings, new_listings], ignore_index=True)
                    status_text.text(f"Successfully scraped {len(new_listings)} listings from {website}")
                else:
                    status_text.text(f"No listings found on {website} for {location}")
            except Exception as e:
                status_text.text(f"Error scraping {website}: {str(e)}")
            
            # Update progress
            sites_completed += 1
            progress_bar.progress(sites_completed / total_sites)
            time.sleep(0.5)  # Small delay for better UX
        
        # Save results to session state
        if not all_listings.empty:
            st.session_state.properties_df = all_listings
            st.session_state.scrape_status = f"Successfully scraped {len(all_listings)} listings"
            # Show success message
            st.sidebar.success(f"Successfully scraped {len(all_listings)} listings!")
        else:
            st.session_state.scrape_status = "No listings found"
            st.sidebar.warning("No listings were found. Try a different location or website.")
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Rerun to refresh the page with new data
        st.rerun()

# Display the last scrape status
if st.session_state.scrape_status:
    st.info(st.session_state.scrape_status)

# Handle property details view
if st.session_state.selected_property:
    # Create a modal-like experience with a container
    with st.container():
        st.subheader("Property Details")
        
        # Create a button to close the modal
        if st.button("× Close Details"):
            st.session_state.selected_property = None
            st.rerun()
        
        # Display property information
        property_data = st.session_state.selected_property['data']
        property_link = st.session_state.selected_property['link']
        
        # Display basic property information
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Address:** {property_data['address']}")
            st.markdown(f"**Price:** {format_price(property_data['price'])}")
            st.markdown(f"**Property Type:** {property_data['property_type']}")
            
        with col2:
            st.markdown(f"**Bedrooms:** {property_data['bedrooms']}")
            st.markdown(f"**Bathrooms:** {property_data['bathrooms']}")
            st.markdown(f"**Square Feet:** {property_data['square_feet']}")
            
        # Get detailed content using trafilatura
        st.subheader("Additional Information")
        with st.spinner("Loading detailed property information..."):
            try:
                details = extract_property_details(property_link)
                if "error" not in details:
                    # Show a sample of the description (first 1000 chars)
                    description = details["full_description"]
                    if description:
                        st.markdown("**Property Description:**")
                        st.write(description[:1000] + ("..." if len(description) > 1000 else ""))
                    else:
                        st.info("No detailed description available.")
                else:
                    st.warning("Could not retrieve detailed information for this property.")
            except Exception as e:
                st.error(f"Error retrieving property details: {str(e)}")
        
        # Link to the original listing
        st.markdown(f"[View Full Listing on {property_data['source']}]({property_link})")

# Filtering section (only show if we have data)
if not st.session_state.properties_df.empty:
    st.header("Filter Listings")
    
    col1, col2, col3 = st.columns(3)
    
    # Get unique values for filters
    unique_sources = get_unique_values(st.session_state.properties_df, 'source')
    unique_cities = get_unique_values(st.session_state.properties_df, 'city')
    unique_property_types = get_unique_values(st.session_state.properties_df, 'property_type')
    
    # Price range filter
    min_price = int(st.session_state.properties_df['price'].min()) if not st.session_state.properties_df.empty else 0
    max_price = int(st.session_state.properties_df['price'].max()) if not st.session_state.properties_df.empty else 1000000
    
    with col1:
        price_range = st.slider(
            "Price Range ($)",
            min_price,
            max_price,
            (min_price, max_price)
        )
    
    # Bedrooms and bathrooms filters
    with col2:
        min_beds = st.number_input("Minimum Bedrooms", 0, 10, 0)
        min_baths = st.number_input("Minimum Bathrooms", 0, 10, 0)
    
    # Additional filters
    with col3:
        selected_sources = st.multiselect("Sources", unique_sources, default=unique_sources)
        selected_cities = st.multiselect("Cities", unique_cities, default=unique_cities)
        selected_property_types = st.multiselect("Property Types", unique_property_types, default=unique_property_types)
    
    # Apply filters
    filtered_df = filter_properties(
        st.session_state.properties_df,
        price_range,
        min_beds,
        min_baths,
        selected_sources,
        selected_cities,
        selected_property_types
    )
    
    # Display statistics
    if not filtered_df.empty:
        st.header("Statistics")
        stats_df = get_statistics(filtered_df)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Price distribution histogram
            fig = px.histogram(
                filtered_df,
                x="price",
                nbins=20,
                title="Price Distribution",
                labels={"price": "Price ($)", "count": "Number of Listings"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Bedrooms vs Price scatter plot
            fig = px.scatter(
                filtered_df,
                x="bedrooms",
                y="price",
                color="source",
                title="Bedrooms vs Price",
                labels={"bedrooms": "Bedrooms", "price": "Price ($)"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Display statistics table
        st.subheader("Summary Statistics")
        st.dataframe(stats_df, use_container_width=True)
    
    # Display results
    st.header(f"Results ({len(filtered_df)} listings)")
    
    if filtered_df.empty:
        st.warning("No properties match your filters. Try adjusting your criteria.")
    else:
        # Sort options
        sort_by = st.selectbox(
            "Sort by",
            ["Price (Low to High)", "Price (High to Low)", "Bedrooms", "Bathrooms", "Square Feet"]
        )
        
        # Apply sorting
        if sort_by == "Price (Low to High)":
            filtered_df = filtered_df.sort_values(by="price")
        elif sort_by == "Price (High to Low)":
            filtered_df = filtered_df.sort_values(by="price", ascending=False)
        elif sort_by == "Bedrooms":
            filtered_df = filtered_df.sort_values(by="bedrooms", ascending=False)
        elif sort_by == "Bathrooms":
            filtered_df = filtered_df.sort_values(by="bathrooms", ascending=False)
        elif sort_by == "Square Feet":
            filtered_df = filtered_df.sort_values(by="square_feet", ascending=False)
        
        # Display property cards in a grid (3 per row)
        cols = st.columns(3)
        for i, (_, property_row) in enumerate(filtered_df.iterrows()):
            with cols[i % 3]:
                display_property_card(property_row)
        
        # Option to download results as CSV
        st.download_button(
            label="Download Results as CSV",
            data=filtered_df.to_csv(index=False),
            file_name="real_estate_listings.csv",
            mime="text/csv"
        )
else:
    # Initial state or no data available
    st.info("Use the sidebar controls to scrape real estate listings.")
    
    # Show a sample of what the app can do
    st.header("How to use this app")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Select websites and location")
        st.markdown("""
        - Choose one or more real estate websites to scrape
        - Enter a location (city, state, or zip code)
        - Set the maximum number of listings to retrieve
        - Click "Scrape Listings" to start
        """)
    
    with col2:
        st.subheader("2. Filter and analyze results")
        st.markdown("""
        - Filter listings by price, bedrooms, bathrooms, etc.
        - View statistics and visualizations
        - Sort results by various criteria
        - Download the data as a CSV file
        """)
