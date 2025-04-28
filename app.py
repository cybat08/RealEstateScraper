import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import json
import os
import datetime as dt
import yfinance as yf
from scraper import scrape_zillow, scrape_realtor, scrape_trulia, generate_sample_data
from data_processor import filter_properties, get_statistics, validate_and_clean_data, calculate_roi_metrics, estimate_rental_yield, estimate_appreciation_rate
from utils import get_unique_values, format_price, display_property_card, display_interactive_comparison, display_favorites_view, geocode_properties, display_property_map
from web_content import extract_property_details
from link_scraper import scrape_links, extract_specific_links
from sheets_exporter import export_dataframe_to_sheet, list_available_spreadsheets

# Configure the page
# Try to use our custom icon if possible, otherwise use a house emoji as fallback
try:
    from pathlib import Path
    icon_path = Path(".streamlit/static/icon.svg")
    if icon_path.exists():
        page_icon = "icon.svg"
    else:
        page_icon = "🏠"
except:
    page_icon = "🏠"
    
st.set_page_config(
    page_title="Real Estate Scraper",
    page_icon=page_icon,
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
This app scrapes real estate listings and web links from popular websites and allows you to filter, analyze, and export the results including to Google Sheets.
""")

# Initialize additional session state variables
if 'links_df' not in st.session_state:
    st.session_state.links_df = pd.DataFrame()

if 'links_scrape_status' not in st.session_state:
    st.session_state.links_scrape_status = ""

if 'google_credentials' not in st.session_state:
    st.session_state.google_credentials = None
    
# Initialize comparison and favorites variables
if 'compare_properties' not in st.session_state:
    st.session_state.compare_properties = []

if 'favorites' not in st.session_state:
    st.session_state.favorites = []

# Create tabs for different functionality
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Real Estate Scraper", 
    "Property Comparison", 
    "Favorites", 
    "Map View",
    "ROI Analysis", 
    "Link Scraper", 
    "Google Sheets Export", 
    "Stock Viewer"
])

# Initialize stock-related session state variables
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = pd.DataFrame()

if 'stock_symbols' not in st.session_state:
    st.session_state.stock_symbols = ["AAPL", "MSFT", "GOOG", "AMZN", "META"]

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

# Advanced scraping filters
with st.sidebar.expander("Advanced Scraping Filters"):
    # Price range filter for scraping
    min_price_scrape = st.number_input("Minimum Price ($)", 
                                       min_value=0, 
                                       max_value=10000000, 
                                       value=0,
                                       step=50000)
    
    max_price_scrape = st.number_input("Maximum Price ($)", 
                                       min_value=0, 
                                       max_value=10000000, 
                                       value=2000000,
                                       step=50000)
    
    # Bedrooms filter
    min_beds_scrape = st.number_input("Minimum Bedrooms", 
                                     min_value=0, 
                                     max_value=10, 
                                     value=0)
    
    # Bathrooms filter
    min_baths_scrape = st.number_input("Minimum Bathrooms", 
                                      min_value=0, 
                                      max_value=10, 
                                      value=0)
    
    # Property type filter
    property_types_scrape = st.multiselect(
        "Property Types",
        ["House", "Condo", "Townhouse", "Multi-Family", "Apartment", "Land", "Commercial"],
        default=["House", "Condo", "Townhouse"]
    )
    
    # Additional filters
    only_new_listings = st.checkbox("Only New Listings (last 7 days)", value=False)
    include_sold = st.checkbox("Include Recently Sold Properties", value=False)
    include_pending = st.checkbox("Include Pending/Contingent Listings", value=True)

# Option to load demo data
use_demo_data = st.sidebar.checkbox("Use demo data for testing", value=False, 
                                    help="Generate sample data for testing data validation and cleanup features")

# Scrape button
scrape_button = st.sidebar.button("Scrape Listings", key="scrape_listings_button")

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
        
        # Scrape each selected website or use demo data
        if use_demo_data:
            # Generate demo data for each selected website
            for website in websites:
                status_text.text(f"Generating demo data for {website}...")
                
                # Generate sample data for this website
                demo_listings = generate_sample_data(location, num_listings, website)
                demo_listings['source'] = website
                
                # Add to the combined listings
                all_listings = pd.concat([all_listings, demo_listings], ignore_index=True)
                
                status_text.text(f"Generated {len(demo_listings)} demo listings for {website}")
                st.sidebar.write(f"Demo data: {len(demo_listings)} listings for {website}")
                
                # Update progress
                sites_completed += 1
                progress_bar.progress(sites_completed / total_sites)
                time.sleep(0.5)  # Small delay for better UX
        else:
            # Scrape real data from each selected website
            for website in websites:
                status_text.text(f"Scraping {website}...")
                
                try:
                    status_text.text(f"Scraping {website}... Please wait...")
                    
                    # Create a dictionary with all filter parameters
                    filter_params = {
                        'min_price': min_price_scrape,
                        'max_price': max_price_scrape,
                        'min_beds': min_beds_scrape,
                        'min_baths': min_baths_scrape,
                        'property_types': property_types_scrape,
                        'new_listings': only_new_listings,
                        'include_sold': include_sold,
                        'include_pending': include_pending
                    }
                    
                    if website == "Zillow":
                        new_listings = scrape_zillow(location, num_listings, **filter_params)
                        st.sidebar.write(f"Debug: Zillow listings count: {len(new_listings) if not isinstance(new_listings, Exception) else 'Error'}")
                    elif website == "Realtor.com":
                        new_listings = scrape_realtor(location, num_listings, **filter_params)
                        st.sidebar.write(f"Debug: Realtor listings count: {len(new_listings) if not isinstance(new_listings, Exception) else 'Error'}")
                    elif website == "Trulia":
                        new_listings = scrape_trulia(location, num_listings, **filter_params)
                        st.sidebar.write(f"Debug: Trulia listings count: {len(new_listings) if not isinstance(new_listings, Exception) else 'Error'}")
                    
                    if isinstance(new_listings, pd.DataFrame) and not new_listings.empty:
                        # Add a source column
                        new_listings['source'] = website
                        # Append to the main dataframe
                        all_listings = pd.concat([all_listings, new_listings], ignore_index=True)
                        status_text.text(f"Successfully scraped {len(new_listings)} listings from {website}")
                    else:
                        status_text.text(f"No listings found on {website} for {location}")
                        
                        # If real scraping failed, use demo data as fallback
                        fallback_listings = generate_sample_data(location, max(5, num_listings // 2), website)
                        fallback_listings['source'] = website
                        all_listings = pd.concat([all_listings, fallback_listings], ignore_index=True)
                        st.sidebar.warning(f"Using {len(fallback_listings)} demo listings for {website} as fallback")
                        
                except Exception as e:
                    status_text.text(f"Error scraping {website}: {str(e)}")
                    st.sidebar.error(f"Debug: Error details for {website}: {str(e)}")
                    
                    # If real scraping failed with an error, use demo data as fallback
                    fallback_listings = generate_sample_data(location, max(5, num_listings // 2), website)
                    fallback_listings['source'] = website
                    all_listings = pd.concat([all_listings, fallback_listings], ignore_index=True)
                    st.sidebar.warning(f"Using {len(fallback_listings)} demo listings for {website} as fallback")
                
                # Update progress
                sites_completed += 1
                progress_bar.progress(sites_completed / total_sites)
                time.sleep(0.5)  # Small delay for better UX
        
        # Save results to session state
        if not all_listings.empty:
            # Apply data validation and cleanup
            status_text.text("Validating and cleaning property data...")
            clean_listings = validate_and_clean_data(all_listings)
            
            # Save the cleaned data
            st.session_state.properties_df = clean_listings
            st.session_state.scrape_status = f"Successfully scraped and validated {len(clean_listings)} listings"
            
            # Show success message with data quality info
            if 'data_quality_score' in clean_listings.columns:
                avg_quality = clean_listings['data_quality_score'].mean()
                st.sidebar.success(f"Successfully scraped {len(clean_listings)} listings! Average data quality: {avg_quality:.0f}%")
            else:
                st.sidebar.success(f"Successfully scraped {len(clean_listings)} listings!")
        else:
            st.session_state.scrape_status = "No listings found"
            st.sidebar.warning("No listings were found. Try a different location or website.")
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Rerun to refresh the page with new data
        st.rerun()

# Display content in tabs
with tab1:  # Real Estate Scraper tab
    # Display the last scrape status
    if st.session_state.scrape_status:
        st.info(st.session_state.scrape_status)

    # Handle property details view
    if st.session_state.selected_property:
        # Create a modal-like experience with a container
        with st.container():
            st.subheader("Property Details")
            
            # Create a button to close the modal
            if st.button("× Close Details", key="close_property_details_button"):
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
            min_beds = st.number_input("Minimum Bedrooms", 0, 10, 0, key="filter_min_bedrooms")
            min_baths = st.number_input("Minimum Bathrooms", 0, 10, 0, key="filter_min_bathrooms")
        
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
            
            # Display data quality metrics if available
            if 'data_quality_score' in filtered_df.columns or 'price_outlier' in filtered_df.columns or 'sqft_outlier' in filtered_df.columns:
                st.subheader("Data Quality Metrics")
                
                quality_col1, quality_col2 = st.columns(2)
                
                with quality_col1:
                    # Show data quality score distribution if available
                    if 'data_quality_score' in filtered_df.columns:
                        fig = px.histogram(
                            filtered_df,
                            x="data_quality_score",
                            nbins=10,
                            title="Data Quality Score Distribution",
                            labels={"data_quality_score": "Quality Score (%)", "count": "Number of Listings"}
                        )
                        fig.update_layout(xaxis_range=[0, 100])
                        st.plotly_chart(fig, use_container_width=True)
                
                with quality_col2:
                    # Show derived fields statistics
                    metrics = []
                    
                    if 'price_outlier' in filtered_df.columns:
                        outlier_count = filtered_df['price_outlier'].sum()
                        outlier_pct = (outlier_count / len(filtered_df)) * 100
                        metrics.append(f"Price Outliers: {outlier_count} ({outlier_pct:.1f}%)")
                    
                    if 'sqft_outlier' in filtered_df.columns:
                        outlier_count = filtered_df['sqft_outlier'].sum()
                        outlier_pct = (outlier_count / len(filtered_df)) * 100
                        metrics.append(f"Square Footage Outliers: {outlier_count} ({outlier_pct:.1f}%)")
                    
                    if 'price_category' in filtered_df.columns:
                        category_counts = filtered_df['price_category'].value_counts()
                        st.write("**Price Categories:**")
                        for category, count in category_counts.items():
                            st.write(f"- {category}: {count} listings ({(count/len(filtered_df))*100:.1f}%)")
                    
                    if metrics:
                        st.write("**Data Quality Metrics:**")
                        for metric in metrics:
                            st.write(f"- {metric}")
                    
                    if 'validated_at' in filtered_df.columns:
                        latest_validation = filtered_df['validated_at'].max()
                        st.write(f"**Last Validation:** {latest_validation}")
        
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
                    display_property_card(
                        property_row,
                        show_compare=True,
                        show_favorite=True
                    )
            
            # Option to download results as CSV
            st.download_button(
                label="Download Results as CSV",
                data=filtered_df.to_csv(index=False),
                file_name="real_estate_listings.csv",
                mime="text/csv",
                key="download_results_csv_button"
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
            
# Tab 2: Property Comparison
with tab2:
    st.header("Property Comparison")
    
    if 'compare_properties' in st.session_state and len(st.session_state.compare_properties) > 0:
        # Display comparison of selected properties
        display_interactive_comparison(st.session_state.compare_properties)
    else:
        # Show instructions if no properties are selected for comparison
        st.info("Select properties to compare by using the 'Compare' checkbox on property cards")
        
        if 'properties_df' in st.session_state and not st.session_state.properties_df.empty:
            st.write("Go to the Real Estate Scraper tab to start selecting properties for comparison")
        else:
            st.write("First scrape some listings using the Real Estate Scraper tab")

# Tab 3: Favorites
with tab3:
    st.header("My Favorites")
    
    if 'favorites' in st.session_state and len(st.session_state.favorites) > 0:
        # Display favorited properties
        display_favorites_view(st.session_state.favorites)
    else:
        # Show instructions if no properties are favorited
        st.info("You haven't added any properties to your favorites yet")
        
        if 'properties_df' in st.session_state and not st.session_state.properties_df.empty:
            st.write("Go to the Real Estate Scraper tab to start adding favorites")
        else:
            st.write("First scrape some listings using the Real Estate Scraper tab")

# Tab 4: Map View
with tab4:
    st.header("Property Map View")
    st.markdown("""
    This interactive map shows the locations of all properties in your search results. 
    Click on a property marker to view details about that property.
    """)
    
    if 'properties_df' in st.session_state and not st.session_state.properties_df.empty:
        # Get the property dataframe
        properties_df = st.session_state.properties_df
        
        # Display map statistics
        data_count = len(properties_df)
        price_avg = properties_df['price'].mean()
        price_min = properties_df['price'].min()
        price_max = properties_df['price'].max()
        
        # Display summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Properties", f"{data_count}")
        with col2:
            st.metric("Avg. Price", f"${price_avg:,.0f}")
        with col3:
            st.metric("Price Range", f"${price_min:,.0f} - ${price_max:,.0f}")
        
        # Show map
        st.subheader("Property Locations")
        display_property_map(properties_df)
        
        # Explanatory note
        st.caption("Note: Property locations are approximated based on address geocoding. Click on markers to see property details.")
        
        # Offer option to recalculate coordinates
        if st.button("Refresh Map Coordinates", key="refresh_map_coordinates_button"):
            with st.spinner("Updating property coordinates..."):
                # Force recalculate all coordinates
                updated_df = geocode_properties(properties_df)
                st.session_state.properties_df = updated_df
                st.rerun()
    else:
        # Show instructions if no properties available
        st.info("No properties available for mapping")
        
        # Information and image about the map feature
        st.markdown("""
        To use the map view:
        1. First scrape property listings using the Real Estate Scraper tab
        2. The map will automatically display all properties in your search results
        3. You can click on property markers to see detailed information
        4. Use the cluster markers to navigate areas with many properties
        """)
        
        # Show a sample image or further instructions
        st.write("The map will show property markers clustered by location, allowing you to easily identify property hotspots.")

# Tab 5: ROI Analysis
with tab5:
    st.header("AI-Powered ROI Analysis")
    st.markdown("""
    This tool uses AI to analyze potential Return on Investment (ROI) for real estate properties. 
    It calculates estimated rental yields, cash flow, and long-term appreciation to help you make smarter investment decisions.
    """)
    
    if 'properties_df' in st.session_state and not st.session_state.properties_df.empty:
        # Property selector
        st.subheader("Select Property to Analyze")
        
        # Display properties in a simple table to choose from
        property_table = st.session_state.properties_df[['address', 'city', 'price', 'bedrooms', 'bathrooms', 'property_type', 'source']].copy()
        st.dataframe(property_table, use_container_width=True)
        
        # User selects property by index
        selected_idx = st.number_input("Enter row number of property to analyze", 
                                       min_value=0, 
                                       max_value=len(st.session_state.properties_df)-1 if len(st.session_state.properties_df) > 0 else 0,
                                       value=0,
                                       key="property_row_selector")
        
        # Get the selected property
        selected_property = st.session_state.properties_df.iloc[selected_idx] if not st.session_state.properties_df.empty else None
        
        if selected_property is not None:
            st.subheader("Property Details")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Address:** {selected_property['address']}")
                st.markdown(f"**City:** {selected_property['city'] if 'city' in selected_property and pd.notna(selected_property['city']) else 'N/A'}")
                st.markdown(f"**Price:** {format_price(selected_property['price'])}")
            
            with col2:
                st.markdown(f"**Bedrooms:** {selected_property['bedrooms']}")
                st.markdown(f"**Bathrooms:** {selected_property['bathrooms']}")
                st.markdown(f"**Property Type:** {selected_property['property_type']}")
            
            # ROI parameters customization
            st.subheader("Investment Parameters")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Allow user to override estimated values
                default_yield = estimate_rental_yield(selected_property)
                rental_yield = st.number_input("Annual Rental Yield (%)", 
                                            min_value=1.0, 
                                            max_value=15.0, 
                                            value=default_yield,
                                            step=0.1,
                                            format="%.1f",
                                            key="rental_yield_input")
                
                st.caption(f"Estimated rental yield for this property is {default_yield:.1f}%")
            
            with col2:
                default_appreciation = estimate_appreciation_rate(selected_property)
                appreciation_rate = st.number_input("Annual Appreciation Rate (%)", 
                                                min_value=0.0, 
                                                max_value=10.0, 
                                                value=default_appreciation,
                                                step=0.1,
                                                format="%.1f",
                                                key="appreciation_rate_input")
                
                st.caption(f"Estimated appreciation rate for this area is {default_appreciation:.1f}%")
            
            col1, col2 = st.columns(2)
            
            with col1:
                down_payment_pct = st.slider("Down Payment (%)", 
                                            min_value=5, 
                                            max_value=100, 
                                            value=20,
                                            key="down_payment_slider")
            
            with col2:
                interest_rate = st.slider("Mortgage Interest Rate (%)", 
                                        min_value=2.0, 
                                        max_value=10.0, 
                                        value=6.5,
                                        step=0.1,
                                        key="interest_rate_slider")
            
            # Calculate ROI
            if st.button("Calculate ROI", key="calculate_roi_button"):
                with st.spinner("Analyzing investment potential..."):
                    # Override default values in the property data for calculation
                    property_data = selected_property.copy()
                    
                    # Calculate ROI metrics
                    roi_metrics = calculate_roi_metrics(property_data, rental_yield, appreciation_rate)
                    
                    # Display results
                    st.subheader("ROI Analysis Results")
                    
                    # Create metrics display
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Annual Rental Yield", f"{roi_metrics['rental_yield']:.1f}%")
                        st.metric("Monthly Cash Flow", f"${roi_metrics['monthly_cash_flow']:,.2f}")
                    
                    with col2:
                        annual_rental = roi_metrics['annual_rental_income']
                        st.metric("Annual Rental Income", f"${annual_rental:,.0f}")
                        st.metric("5-Year ROI", f"{roi_metrics['roi_5yr']:.1f}%")
                    
                    with col3:
                        current_price = selected_property['price']
                        future_value = roi_metrics['five_year_value']
                        appreciation_value = future_value - current_price
                        st.metric("5-Year Value", f"${future_value:,.0f}", 
                                 delta=f"${appreciation_value:,.0f}")
                        st.metric("Appreciation Rate", f"{roi_metrics['appreciation_rate']:.1f}%/year")
                    
                    # Investment recommendation
                    st.subheader("Investment Recommendation")
                    
                    # Format the recommendation with colorful background
                    recommendation = roi_metrics['investment_recommendation']
                    if "excellent" in recommendation.lower():
                        st.success(recommendation)
                    elif "good" in recommendation.lower():
                        st.info(recommendation)
                    elif "average" in recommendation.lower():
                        st.warning(recommendation)
                    else:
                        st.error(recommendation)
                    
                    # Show detailed analysis
                    with st.expander("Detailed Analysis"):
                        st.markdown("""
                        ### Methodology
                        
                        This analysis is based on the following calculations:
                        
                        - **Monthly Rental Income**: Estimated based on property characteristics and location
                        - **Monthly Expenses**: Estimated at 40% of rental income (taxes, insurance, maintenance, vacancy)
                        - **Mortgage Payment**: Calculated based on purchase price, down payment, and interest rate
                        - **Cash Flow**: Rental income minus expenses and mortgage payment
                        - **Appreciation**: Estimated based on location, property type, and market trends
                        - **5-Year ROI**: (5-year appreciation + 5-year cash flow) / initial investment
                        
                        > This is an estimate based on available data and should be used as a starting point for further due diligence.
                        """)
    else:
        # No properties available
        st.info("No properties available for analysis. Please use the Real Estate Scraper tab to find properties first.")
        
        # Show a sample of what the tool can do
        st.subheader("How This Tool Works")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **This tool helps you:**
            
            - Calculate potential rental income for properties
            - Estimate monthly cash flow after expenses
            - Project property value appreciation over time
            - Determine overall investment return (ROI)
            - Get AI-powered investment recommendations
            """)
        
        with col2:
            st.markdown("""
            **The analysis considers:**
            
            - Property location and market trends
            - Property type and characteristics
            - Current interest rates and financing options
            - Typical operating expenses
            - Long-term appreciation potential
            """)

# Tab 6: Link Scraper
with tab6:
    st.header("Website Link Scraper")
    st.markdown("This tool allows you to extract links from any website for further analysis.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # URL input and scraping controls
        url = st.text_input("Website URL", "https://www.example.com", key="link_scraper_url_input")
        max_links = st.slider("Maximum number of links to extract", 10, 500, 100, key="max_links_slider")
        same_domain_only = st.checkbox("Only links from same domain", value=True, key="same_domain_checkbox")
        
        # Optional pattern filter
        link_pattern = st.text_input("Filter links by pattern (regex, optional)", "")
        
        # CSS selector for specific links
        use_css_selector = st.checkbox("Use CSS selector to find specific links", value=False)
        css_selector = st.text_input("CSS Selector (e.g., 'a.listing-link')", "", disabled=not use_css_selector)
        
    with col2:
        # Add some helpful information
        st.subheader("Tips")
        st.markdown("""
        - Enter a complete URL including 'https://'
        - CSS selectors are useful for targeting specific types of links
        - Examples:
            - `a.product-link` - links with class 'product-link'
            - `.listings a` - links inside elements with class 'listings'
            - `#main-content a` - links inside element with ID 'main-content'
        """)
    
    # Scrape button
    scrape_links_button = st.button("Scrape Links", key="scrape_links_button")
    
    if scrape_links_button:
        if not url:
            st.error("Please enter a valid URL")
        else:
            with st.spinner("Scraping links... This may take a moment"):
                try:
                    if use_css_selector and css_selector:
                        st.session_state.links_df = extract_specific_links(
                            url, css_selector, max_links, link_pattern
                        )
                    else:
                        st.session_state.links_df = scrape_links(
                            url, max_links, link_pattern, same_domain_only
                        )
                    
                    st.session_state.links_scrape_status = f"Successfully scraped {len(st.session_state.links_df)} links"
                    st.success(f"Successfully scraped {len(st.session_state.links_df)} links!")
                except Exception as e:
                    st.error(f"Error scraping links: {str(e)}")
                    st.session_state.links_scrape_status = f"Error: {str(e)}"
    
    # Display the last scrape status
    if st.session_state.links_scrape_status:
        st.info(st.session_state.links_scrape_status)
    
    # Display results if available
    if not st.session_state.links_df.empty:
        st.header("Results")
        
        # Filter options
        st.subheader("Filter Links")
        filter_text = st.text_input("Filter by text contained in URL or title", key="link_filter_text_input")
        
        filtered_links_df = st.session_state.links_df
        if filter_text:
            mask = (
                filtered_links_df['url'].str.contains(filter_text, case=False, na=False) | 
                filtered_links_df['title'].str.contains(filter_text, case=False, na=False)
            )
            filtered_links_df = filtered_links_df[mask]
        
        # Display the dataframe
        st.dataframe(filtered_links_df, use_container_width=True)
        
        # Download options
        st.download_button(
            label="Download as CSV",
            data=filtered_links_df.to_csv(index=False),
            file_name="scraped_links.csv",
            mime="text/csv",
            key="download_links_csv_button"
        )
        
        # Export to Google Sheets button
        if st.button("Export to Google Sheets", key="links_export_to_sheets_button"):
            st.markdown("""
            **Google Sheets Integration**
            
            To export data to Google Sheets, you need to provide Google API credentials.
            """)
            
            # We'll implement this in the Google Sheets tab

# Tab 7: Google Sheets Export
with tab7:
    st.header("Google Sheets Export")
    st.markdown("Export your scraped data to Google Sheets for easier sharing and collaboration.")
    
    # Set up the credentials
    credentials_json = st.text_area(
        "Google API Credentials (JSON)",
        placeholder="Paste your Google Service Account credentials JSON here",
        height=150,
        key="google_credentials_input"
    )
    
    # Create columns for data source selection and export options
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Data Source")
        data_source = st.radio(
            "Select data to export",
            ["Real Estate Listings", "Scraped Links"],
            disabled=st.session_state.properties_df.empty and st.session_state.links_df.empty,
            key="export_data_source_radio"
        )
        
        # Show a preview of the selected data
        if data_source == "Real Estate Listings" and not st.session_state.properties_df.empty:
            st.write("Preview (first 5 rows):")
            st.dataframe(st.session_state.properties_df.head(5), use_container_width=True)
        elif data_source == "Scraped Links" and not st.session_state.links_df.empty:
            st.write("Preview (first 5 rows):")
            st.dataframe(st.session_state.links_df.head(5), use_container_width=True)
        else:
            st.info("No data available for the selected source. Please use the scrapers first.")
            
    with col2:
        st.subheader("Export Options")
        
        # Spreadsheet options
        new_spreadsheet = st.checkbox("Create new spreadsheet", value=True, key="new_spreadsheet_checkbox")
        
        if new_spreadsheet:
            spreadsheet_name = st.text_input("New spreadsheet name", "Real Estate Data", key="new_spreadsheet_name_input")
            spreadsheet_id = None
        else:
            # Would provide a dropdown of existing spreadsheets here
            spreadsheet_id = st.text_input("Existing spreadsheet ID", key="existing_spreadsheet_id_input")
            spreadsheet_name = None
        
        worksheet_name = st.text_input("Worksheet name", "Data", key="worksheet_name_input")
        append_data = st.checkbox("Append to existing data in worksheet", value=False, key="append_data_checkbox")
    
    # Export button
    export_button = st.button(
        "Export to Google Sheets",
        key="export_to_sheets_button",
        disabled=(
            st.session_state.properties_df.empty and st.session_state.links_df.empty
            or not credentials_json
            or (not new_spreadsheet and not spreadsheet_id)
        )
    )
    
    if export_button:
        with st.spinner("Exporting to Google Sheets..."):
            try:
                # Select the correct dataframe based on user choice
                if data_source == "Real Estate Listings":
                    export_df = st.session_state.properties_df
                else:  # Scraped Links
                    export_df = st.session_state.links_df
                
                # Call the export function
                result = export_dataframe_to_sheet(
                    export_df,
                    credentials_json=credentials_json,
                    spreadsheet_name=spreadsheet_name,
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=worksheet_name,
                    append=append_data
                )
                
                if "error" not in result:
                    st.success("Data successfully exported to Google Sheets!")
                    st.markdown(f"[Open Spreadsheet]({result['spreadsheet_url']})")
                    
                    # Save the credentials for future use
                    st.session_state.google_credentials = credentials_json
                else:
                    st.error(f"Export failed: {result['error']}")
            except Exception as e:
                st.error(f"Error during export: {str(e)}")
                
# Tab 8: Stock Viewer
with tab8:
    st.header("Stock Market Viewer")
    st.markdown("Monitor stock performance and analyze market trends to inform your real estate investment decisions.")
    
    # Stock selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Stock symbols input - limit to 5 for performance
        symbols_input = st.text_input(
            "Stock Symbols (comma-separated, max 5)",
            value=",".join(st.session_state.stock_symbols)
        )
        
        # Parse the input symbols and limit to 5
        input_symbols = [s.strip() for s in symbols_input.split(",") if s.strip()][:5]
        if input_symbols:
            st.session_state.stock_symbols = input_symbols
        
        # Date range selection
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input(
                "Start Date", 
                value=dt.datetime.now() - dt.timedelta(days=365)
            )
        with date_col2:
            end_date = st.date_input("End Date", value=dt.datetime.now())
            
    with col2:
        # Chart type selection
        chart_type = st.selectbox(
            "Chart Type",
            ["Closing Price", "Candlestick", "Volume", "Returns"]
        )
        
        # Comparison option
        compare_stocks = st.checkbox("Compare Performance", value=True)
        
        # Fetch button
        fetch_data = st.button("Fetch Stock Data", key="fetch_stock_data_button")
    
    # Fetch data
    if fetch_data or not st.session_state.stock_data.empty:
        if fetch_data:
            with st.spinner("Fetching stock data..."):
                try:
                    # Convert dates to string format
                    start_date_str = start_date.strftime('%Y-%m-%d')
                    end_date_str = end_date.strftime('%Y-%m-%d')
                    
                    # Fetch data for all symbols
                    stock_data = yf.download(
                        st.session_state.stock_symbols,
                        start=start_date_str,
                        end=end_date_str
                    )
                    
                    # Store in session state
                    st.session_state.stock_data = stock_data
                    st.success(f"Successfully fetched data for {', '.join(st.session_state.stock_symbols)}")
                except Exception as e:
                    st.error(f"Error fetching stock data: {str(e)}")
        
        if not st.session_state.stock_data.empty:
            # Show charts based on selection
            if chart_type == "Closing Price" and compare_stocks:
                # Show comparative closing prices
                if len(st.session_state.stock_symbols) > 1:
                    st.subheader("Comparative Stock Performance")
                    
                    # Extract closing prices
                    closing_prices = st.session_state.stock_data['Close']
                    
                    # Create normalized chart (percentage change)
                    normalized = closing_prices.copy()
                    for symbol in st.session_state.stock_symbols:
                        if symbol in normalized.columns:
                            normalized[symbol] = normalized[symbol] / normalized[symbol].iloc[0] * 100
                    
                    # Create a figure
                    fig = go.Figure()
                    
                    for symbol in st.session_state.stock_symbols:
                        if symbol in normalized.columns:
                            fig.add_trace(go.Scatter(
                                x=normalized.index,
                                y=normalized[symbol],
                                mode='lines',
                                name=symbol
                            ))
                    
                    fig.update_layout(
                        title="Normalized Stock Performance (Starting Value = 100%)",
                        xaxis_title="Date",
                        yaxis_title="Performance (%)",
                        legend_title="Stocks",
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Please select multiple stocks to compare performance.")
            
            # Individual stock details
            st.subheader("Individual Stock Analysis")
            
            # Create tabs for each stock
            stock_tabs = st.tabs(st.session_state.stock_symbols)
            
            for i, symbol in enumerate(st.session_state.stock_symbols):
                with stock_tabs[i]:
                    # Check if data exists for this symbol
                    has_data = False
                    
                    if len(st.session_state.stock_symbols) > 1:
                        # Multi-stock dataframe
                        if symbol in st.session_state.stock_data['Close'].columns:
                            has_data = True
                            stock_df = pd.DataFrame({
                                'Open': st.session_state.stock_data['Open'][symbol],
                                'High': st.session_state.stock_data['High'][symbol],
                                'Low': st.session_state.stock_data['Low'][symbol],
                                'Close': st.session_state.stock_data['Close'][symbol],
                                'Volume': st.session_state.stock_data['Volume'][symbol]
                            })
                    else:
                        # Single stock dataframe
                        has_data = True
                        stock_df = st.session_state.stock_data.copy()
                    
                    if has_data:
                        # Stock info
                        try:
                            stock_info = yf.Ticker(symbol).info
                            if stock_info:
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    if 'currentPrice' in stock_info:
                                        st.metric(
                                            "Current Price", 
                                            f"${stock_info['currentPrice']:.2f}",
                                            f"{stock_info.get('regularMarketChangePercent', 0):.2f}%"
                                        )
                                
                                with col2:
                                    if 'fiftyTwoWeekHigh' in stock_info and 'fiftyTwoWeekLow' in stock_info:
                                        st.metric(
                                            "52 Week Range", 
                                            f"${stock_info['fiftyTwoWeekHigh']:.2f}",
                                            f"Low: ${stock_info['fiftyTwoWeekLow']:.2f}"
                                        )
                                
                                with col3:
                                    if 'marketCap' in stock_info:
                                        market_cap_b = stock_info['marketCap'] / 1e9
                                        st.metric("Market Cap", f"${market_cap_b:.2f}B")
                        except Exception as e:
                            st.warning(f"Could not fetch additional info: {str(e)}")
                        
                        # Create chart based on selection
                        if chart_type == "Closing Price":
                            # Check if stock_df has multi-index columns (happens with multiple symbols)
                            if isinstance(stock_df.columns, pd.MultiIndex):
                                # When we have a multi-index DataFrame
                                fig = px.line(
                                    stock_df, 
                                    x=stock_df.index, 
                                    y=('Close', symbol) if ('Close', symbol) in stock_df.columns else stock_df.columns[0],
                                    title=f"{symbol} Closing Price"
                                )
                            else:
                                # When we have a regular DataFrame
                                fig = px.line(
                                    stock_df, 
                                    x=stock_df.index, 
                                    y='Close' if 'Close' in stock_df.columns else stock_df.columns[0],
                                    title=f"{symbol} Closing Price"
                                )
                            st.plotly_chart(fig, use_container_width=True)
                            
                        elif chart_type == "Candlestick":
                            # Get column names based on DataFrame structure
                            if isinstance(stock_df.columns, pd.MultiIndex):
                                open_col = ('Open', symbol) if ('Open', symbol) in stock_df.columns else stock_df.columns[0]
                                high_col = ('High', symbol) if ('High', symbol) in stock_df.columns else stock_df.columns[1]
                                low_col = ('Low', symbol) if ('Low', symbol) in stock_df.columns else stock_df.columns[2]
                                close_col = ('Close', symbol) if ('Close', symbol) in stock_df.columns else stock_df.columns[3]
                            else:
                                open_col = 'Open'
                                high_col = 'High'
                                low_col = 'Low'
                                close_col = 'Close'
                            
                            fig = go.Figure(data=[go.Candlestick(
                                x=stock_df.index,
                                open=stock_df[open_col],
                                high=stock_df[high_col],
                                low=stock_df[low_col],
                                close=stock_df[close_col],
                                name=symbol
                            )])
                            
                            fig.update_layout(
                                title=f"{symbol} Stock Price",
                                xaxis_title="Date",
                                yaxis_title="Price ($)",
                                height=500
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                        elif chart_type == "Volume":
                            # Determine volume column based on DataFrame structure
                            if isinstance(stock_df.columns, pd.MultiIndex):
                                vol_col = ('Volume', symbol) if ('Volume', symbol) in stock_df.columns else stock_df.columns[4]
                            else:
                                vol_col = 'Volume'
                                
                            fig = px.bar(
                                stock_df, 
                                x=stock_df.index, 
                                y=vol_col,
                                title=f"{symbol} Trading Volume"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                        elif chart_type == "Returns":
                            # Determine close column based on DataFrame structure
                            if isinstance(stock_df.columns, pd.MultiIndex):
                                close_col = ('Close', symbol) if ('Close', symbol) in stock_df.columns else stock_df.columns[3]
                            else:
                                close_col = 'Close'
                                
                            # Calculate daily returns
                            returns = stock_df[close_col].pct_change() * 100
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=returns.index, 
                                y=returns,
                                mode='lines',
                                name='Daily Returns'
                            ))
                            
                            fig.update_layout(
                                title=f"{symbol} Daily Returns (%)",
                                xaxis_title="Date",
                                yaxis_title="Returns (%)",
                                height=500
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Show recent data
                        st.subheader("Recent Data")
                        st.dataframe(stock_df.tail(10), use_container_width=True)
                    else:
                        st.warning(f"No data available for {symbol}")
    else:
        # Information message
        st.info("Enter stock symbols and click 'Fetch Stock Data' to view stock information and charts.")
