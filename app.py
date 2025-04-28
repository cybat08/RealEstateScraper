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
from utils import get_unique_values, format_price, display_property_card, display_interactive_comparison, display_favorites_view
from web_content import extract_property_details
from link_scraper import scrape_links, extract_specific_links
from sheets_exporter import export_dataframe_to_sheet, list_available_spreadsheets

# Set page configuration
st.set_page_config(
    page_title="Real Estate Scraper",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .main-header {color: #2c39b1;}
    .property-card {
        border: 1px solid #ddd; 
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .label {font-weight: bold;}
    .favorite-btn {color: gold;}
    .button-row {display: flex; gap: 10px;}
</style>
""", unsafe_allow_html=True)

# App title
st.title("🏠 Real Estate Scraper & Analysis")

# Application description
st.markdown("""
This app allows you to scrape and analyze real estate listings from multiple websites. 
Search for properties by location, compare them side by side, and perform investment analysis.
""")

# Initialize session state
if 'properties_df' not in st.session_state:
    st.session_state.properties_df = pd.DataFrame()
    
if 'scrape_status' not in st.session_state:
    st.session_state.scrape_status = ""
    
if 'selected_property' not in st.session_state:
    st.session_state.selected_property = None
    
if 'comparison_list' not in st.session_state:
    st.session_state.comparison_list = []

if 'favorites' not in st.session_state:
    st.session_state.favorites = []

# Create tabs for different functionality
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Real Estate Scraper", 
    "Property Comparison", 
    "Favorites", 
    "ROI Analysis", 
    "Link Scraper", 
    "Google Sheets Export"
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
                    
            # Calculate and display ROI metrics
            st.subheader("Investment Analysis")
            with st.spinner("Calculating investment metrics..."):
                try:
                    # Estimate rental yield and appreciation rate based on property characteristics
                    rental_yield = estimate_rental_yield(property_data)
                    appreciation_rate = estimate_appreciation_rate(property_data)
                    
                    # Calculate ROI metrics
                    roi_metrics = calculate_roi_metrics(
                        property_data, 
                        rental_yield_percent=rental_yield,
                        appreciation_rate=appreciation_rate
                    )
                    
                    # Display the metrics in columns
                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                    
                    with metric_col1:
                        st.metric("Est. Monthly Rent", f"${roi_metrics['monthly_rent']:.2f}")
                        
                    with metric_col2:
                        st.metric("Cap Rate", f"{roi_metrics['cap_rate']:.2f}%")
                        
                    with metric_col3:
                        st.metric("Cash on Cash Return", f"{roi_metrics['cash_on_cash_return']:.2f}%")
                        
                    with metric_col4:
                        st.metric("5-Year Equity Growth", f"${roi_metrics['equity_5yr']:.2f}")
                        
                    # Add a disclaimer
                    st.caption("Note: These are estimates based on available data and market assumptions. Always perform your own due diligence.")
                    
                except Exception as e:
                    st.error(f"Error calculating investment metrics: {str(e)}")
            
            # Display a link to the original listing
            st.markdown(f"[View Original Listing]({property_link})")
    else:
        # Display the main property listings
        if not st.session_state.properties_df.empty:
            st.subheader("Property Listings")
            
            # Add filtering options
            st.markdown("### Filter Listings")
            
            # Create columns for filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Get min and max price values
                min_price = int(st.session_state.properties_df['price'].min()) if not st.session_state.properties_df.empty else 0
                max_price = int(st.session_state.properties_df['price'].max()) if not st.session_state.properties_df.empty else 1000000
                
                # Price range filter
                price_range = st.slider(
                    "Price Range",
                    min_value=min_price,
                    max_value=max_price,
                    value=(min_price, max_price),
                    step=10000,
                    format="$%d"
                )
                
                # Bedrooms filter
                min_beds = st.number_input(
                    "Minimum Bedrooms",
                    min_value=0,
                    max_value=10,
                    value=0,
                    key="min_beds_filter"
                )
                
            with col2:
                # Bathrooms filter
                min_baths = st.number_input(
                    "Minimum Bathrooms",
                    min_value=0,
                    max_value=10,
                    value=0,
                    key="min_baths_filter"
                )
                
                # Property type filter
                property_types = st.multiselect(
                    "Property Types",
                    options=get_unique_values(st.session_state.properties_df, 'property_type'),
                    default=get_unique_values(st.session_state.properties_df, 'property_type'),
                    key="property_types_filter"
                )
                
            with col3:
                # Source filter
                sources = st.multiselect(
                    "Sources",
                    options=get_unique_values(st.session_state.properties_df, 'source'),
                    default=get_unique_values(st.session_state.properties_df, 'source'),
                    key="sources_filter"
                )
                
                # City filter
                cities = st.multiselect(
                    "Cities",
                    options=get_unique_values(st.session_state.properties_df, 'city'),
                    default=get_unique_values(st.session_state.properties_df, 'city'),
                    key="cities_filter"
                )
            
            # Apply filters
            if st.session_state.properties_df is not None and not st.session_state.properties_df.empty:
                filtered_df = filter_properties(
                    st.session_state.properties_df,
                    price_range,
                    min_beds,
                    min_baths,
                    sources,
                    cities,
                    property_types
                )
                
                # Calculate and display statistics
                stats_df = get_statistics(filtered_df)
                
                # Display statistics in columns
                stat_cols = st.columns(5)
                with stat_cols[0]:
                    st.metric("Total Properties", f"{len(filtered_df)}")
                with stat_cols[1]:
                    st.metric("Avg. Price", f"${stats_df['avg_price']:.0f}")
                with stat_cols[2]:
                    st.metric("Avg. Price/Sqft", f"${stats_df['avg_price_per_sqft']:.2f}")
                with stat_cols[3]:
                    st.metric("Avg. Bedrooms", f"{stats_df['avg_bedrooms']:.1f}")
                with stat_cols[4]:
                    st.metric("Avg. Bathrooms", f"{stats_df['avg_bathrooms']:.1f}")
                
                # Display sorted properties with pagination
                st.markdown("### Results")
                
                # Add sorting options
                sort_col, order_col = st.columns(2)
                with sort_col:
                    sort_by = st.selectbox(
                        "Sort By",
                        ["price", "bedrooms", "bathrooms", "square_feet", "data_quality_score"],
                        index=0,
                        key="sort_by_option"
                    )
                
                with order_col:
                    sort_order = st.radio(
                        "Order",
                        ["Ascending", "Descending"],
                        index=1,
                        horizontal=True,
                        key="sort_order_option"
                    )
                
                is_ascending = sort_order == "Ascending"
                
                # Sort the dataframe
                sorted_df = filtered_df.sort_values(by=sort_by, ascending=is_ascending)
                
                # Pagination controls
                properties_per_page = 5
                total_pages = (len(sorted_df) + properties_per_page - 1) // properties_per_page
                
                if total_pages > 1:
                    page_col1, page_col2 = st.columns([3, 1])
                    with page_col1:
                        page = st.slider("Page", 1, max(1, total_pages), 1)
                    with page_col2:
                        st.write(f"Page {page} of {total_pages}")
                else:
                    page = 1
                
                # Calculate start and end indices
                start_idx = (page - 1) * properties_per_page
                end_idx = min(start_idx + properties_per_page, len(sorted_df))
                
                # Display properties for the current page
                for i in range(start_idx, end_idx):
                    property_data = sorted_df.iloc[i]
                    property_link = property_data.get('url', '#')
                    
                    # Display the property card
                    with st.container():
                        display_property_card(property_data)
                        
                        # Create a row of buttons for actions
                        col1, col2, col3 = st.columns([1, 1, 2])
                        
                        with col1:
                            if st.button("View Details", key=f"view_{i}"):
                                st.session_state.selected_property = {
                                    'data': property_data,
                                    'link': property_link
                                }
                                st.rerun()
                        
                        with col2:
                            if st.button("Compare", key=f"compare_{i}"):
                                # Add to comparison list if not already there
                                property_dict = property_data.to_dict()
                                if property_dict not in st.session_state.comparison_list:
                                    st.session_state.comparison_list.append(property_dict)
                                    st.success(f"Added property to comparison list! ({len(st.session_state.comparison_list)} properties)")
                                    st.rerun()
                                else:
                                    st.warning("This property is already in your comparison list")
                        
                        with col3:
                            if st.button("Add to Favorites ⭐", key=f"favorite_{i}"):
                                # Add to favorites if not already there
                                property_dict = property_data.to_dict()
                                property_dict['url'] = property_link
                                if property_dict not in st.session_state.favorites:
                                    st.session_state.favorites.append(property_dict)
                                    st.success(f"Added property to favorites! ({len(st.session_state.favorites)} favorites)")
                                    st.rerun()
                                else:
                                    st.warning("This property is already in your favorites")
                    
                    # Add a separator between properties
                    st.markdown("---")
                
                # Show export button when properties are available
                if not filtered_df.empty:
                    export_col1, export_col2 = st.columns([3, 1])
                    with export_col1:
                        st.markdown("### Export Options")
                        
                    with export_col2:
                        if st.button("Export to Google Sheets", key="export_sheets_button"):
                            st.session_state.export_data = filtered_df
                            st.session_state.active_tab = "export"
                            # Switch to the export tab
                            st.rerun()
            else:
                st.warning("No properties found with the selected filters. Try adjusting your filters.")
        else:
            st.write("No properties found. Use the scraper controls in the sidebar to fetch property listings.")

# Tab 2: Property Comparison
with tab2:
    st.header("Property Comparison")
    st.markdown("Compare properties side by side to help make the best investment decision.")
    
    if st.session_state.comparison_list:
        # Create a dataframe from the comparison list
        comparison_df = pd.DataFrame(st.session_state.comparison_list)
        
        # Display the comparison table interactively
        display_interactive_comparison(comparison_df)
        
        # Add a button to clear the comparison list
        if st.button("Clear Comparison List", key="clear_comparison_button"):
            st.session_state.comparison_list = []
            st.rerun()
    else:
        st.info("Add properties to your comparison list from the scraper tab to see them compared side by side.")

# Tab 3: Favorites
with tab3:
    st.header("Favorites")
    st.markdown("View and manage your saved favorite properties.")
    
    if st.session_state.favorites:
        # Show the favorites
        display_favorites_view(st.session_state.favorites)
        
        # Add a button to clear favorites
        if st.button("Clear All Favorites", key="clear_favorites_button"):
            st.session_state.favorites = []
            st.rerun()
    else:
        if not st.session_state.properties_df.empty:
            st.write("Go to the Real Estate Scraper tab to start adding favorites")
        else:
            st.write("First scrape some listings using the Real Estate Scraper tab")

# Map View tab has been removed as requested

# Tab 4: ROI Analysis
with tab4:
    st.header("ROI Analysis")
    st.markdown("""
    This tool helps you analyze the potential return on investment for real estate properties.
    Enter property details to calculate key investment metrics such as cap rate, cash flow, and projected returns.
    """)
    
    # Create two columns for input and results
    input_col, result_col = st.columns([1, 1])
    
    with input_col:
        st.subheader("Property Details")
        
        # Create a form for ROI analysis
        with st.form(key="roi_form"):
            # Basic property information
            property_price = st.number_input("Property Price ($)", min_value=1000, value=500000, step=5000, key="roi_property_price")
            bedrooms = st.number_input("Bedrooms", min_value=0, max_value=10, value=3, key="roi_bedrooms")
            bathrooms = st.number_input("Bathrooms", min_value=0.0, max_value=10.0, value=2.0, step=0.5, key="roi_bathrooms")
            square_feet = st.number_input("Square Feet", min_value=100, value=1800, step=100, key="roi_square_feet")
            property_type = st.selectbox(
                "Property Type",
                ["House", "Condo", "Townhouse", "Multi-Family", "Apartment", "Land", "Commercial"],
                index=0,
                key="roi_property_type"
            )
            property_age = st.number_input("Property Age (years)", min_value=0, value=20, step=1, key="roi_property_age")
            
            # Location quality (proxy for appreciation potential)
            location_rating = st.slider(
                "Location Quality (1-10)",
                min_value=1,
                max_value=10,
                value=7,
                help="Higher rating indicates better location (schools, amenities, employment opportunities)",
                key="roi_location_rating"
            )
            
            st.subheader("Financing Details")
            down_payment_pct = st.slider("Down Payment (%)", min_value=0, max_value=100, value=20, key="roi_down_payment")
            interest_rate = st.slider("Interest Rate (%)", min_value=1.0, max_value=10.0, value=4.5, step=0.1, key="roi_interest_rate")
            loan_term = st.slider("Loan Term (years)", min_value=5, max_value=30, value=30, step=5, key="roi_loan_term")
            
            st.subheader("Income & Expenses")
            monthly_rent_override = st.number_input(
                "Monthly Rent ($, leave at 0 for estimate)", 
                min_value=0, 
                value=0, 
                step=100,
                help="Enter 0 to use an estimated rent based on property characteristics",
                key="roi_monthly_rent"
            )
            
            vacancy_rate = st.slider("Vacancy Rate (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.5, key="roi_vacancy_rate")
            property_tax_rate = st.slider("Property Tax Rate (%/year)", min_value=0.0, max_value=5.0, value=1.2, step=0.1, key="roi_property_tax")
            insurance_rate = st.slider("Insurance Rate (%/year)", min_value=0.0, max_value=2.0, value=0.5, step=0.1, key="roi_insurance")
            maintenance_rate = st.slider("Maintenance (%/year)", min_value=0.0, max_value=5.0, value=1.0, step=0.1, key="roi_maintenance")
            property_mgmt_rate = st.slider("Property Management (%/month)", min_value=0.0, max_value=15.0, value=8.0, step=0.5, key="roi_mgmt")
            utilities = st.number_input("Monthly Utilities ($, if owner-paid)", min_value=0, value=0, step=10, key="roi_utilities")
            hoa_fees = st.number_input("Monthly HOA Fees ($)", min_value=0, value=0, step=10, key="roi_hoa")
            
            st.subheader("Appreciation & Investment Horizon")
            appreciation_override = st.slider(
                "Annual Appreciation Rate (%, leave at 0 for estimate)", 
                min_value=0.0, 
                max_value=10.0, 
                value=0.0, 
                step=0.1,
                help="Enter 0 to use an estimated appreciation rate based on property characteristics",
                key="roi_appreciation"
            )
            
            investment_horizon = st.slider("Investment Horizon (years)", min_value=1, max_value=30, value=5, key="roi_horizon")
            
            # Submit button
            analyze_button = st.form_submit_button(label="Analyze Investment")
    
    with result_col:
        if analyze_button:
            st.subheader("Investment Analysis Results")
            
            # Create a property data dictionary
            property_data = {
                'price': property_price,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'square_feet': square_feet,
                'property_type': property_type,
                'property_age': property_age,
                'location_quality': location_rating
            }
            
            # Only use override values if they are non-zero
            rental_yield = None if monthly_rent_override > 0 else None
            appreciation_rate = None if appreciation_override > 0 else None
            
            # If overrides are provided, calculate the rates
            if monthly_rent_override > 0:
                annual_rent = monthly_rent_override * 12
                rental_yield = (annual_rent / property_price) * 100
            
            if appreciation_override > 0:
                appreciation_rate = appreciation_override
            
            # Calculate ROI metrics with additional parameters
            roi_metrics = calculate_roi_metrics(
                property_data, 
                rental_yield_percent=rental_yield,
                appreciation_rate=appreciation_rate,
                down_payment_pct=down_payment_pct,
                interest_rate=interest_rate,
                loan_term_years=loan_term,
                vacancy_rate=vacancy_rate,
                property_tax_rate=property_tax_rate,
                insurance_rate=insurance_rate,
                maintenance_rate=maintenance_rate,
                property_mgmt_rate=property_mgmt_rate,
                monthly_utilities=utilities,
                monthly_hoa=hoa_fees,
                investment_horizon_years=investment_horizon
            )
            
            # Display key metrics with visual indicators
            col1, col2 = st.columns(2)
            
            with col1:
                # Monthly cash flow
                monthly_cash_flow = roi_metrics['monthly_cash_flow']
                st.metric(
                    "Monthly Cash Flow", 
                    f"${monthly_cash_flow:.2f}",
                    delta=None,
                    delta_color="normal"
                )
                
                # Cap rate
                cap_rate = roi_metrics['cap_rate']
                st.metric(
                    "Cap Rate", 
                    f"{cap_rate:.2f}%",
                    delta=None,
                    delta_color="normal" 
                )
                
                # Monthly mortgage payment
                mortgage_payment = roi_metrics['mortgage_payment']
                st.metric(
                    "Monthly Mortgage", 
                    f"${mortgage_payment:.2f}",
                    delta=None,
                    delta_color="normal"
                )
                
                # Monthly expenses
                monthly_expenses = roi_metrics['monthly_expenses']
                st.metric(
                    "Monthly Expenses", 
                    f"${monthly_expenses:.2f}",
                    delta=None,
                    delta_color="normal"
                )
                
            with col2:
                # Cash on cash return
                cash_on_cash = roi_metrics['cash_on_cash_return']
                st.metric(
                    "Cash on Cash Return", 
                    f"{cash_on_cash:.2f}%",
                    delta=None,
                    delta_color="normal"
                )
                
                # 5-year equity growth
                equity_5yr = roi_metrics['equity_5yr']
                st.metric(
                    "Equity in 5 Years", 
                    f"${equity_5yr:.2f}",
                    delta=None,
                    delta_color="normal"
                )
                
                # Total return on investment
                total_roi = roi_metrics['total_roi_pct']
                st.metric(
                    f"Total ROI ({investment_horizon} years)", 
                    f"{total_roi:.2f}%",
                    delta=None,
                    delta_color="normal"
                )
                
                # Annualized ROI
                annualized_roi = roi_metrics['annualized_roi']
                st.metric(
                    "Annualized ROI", 
                    f"{annualized_roi:.2f}%",
                    delta=None,
                    delta_color="normal"
                )
            
            # Display a summary assessment
            st.subheader("Investment Summary")
            
            # Determine overall assessment
            if cash_on_cash >= 8 and cap_rate >= 6 and monthly_cash_flow > 0:
                assessment = "Excellent Investment Opportunity"
                assessment_color = "green"
            elif cash_on_cash >= 5 and cap_rate >= 4 and monthly_cash_flow > 0:
                assessment = "Good Investment Opportunity"
                assessment_color = "blue"
            elif monthly_cash_flow > 0:
                assessment = "Fair Investment Opportunity"
                assessment_color = "orange"
            else:
                assessment = "Poor Investment Opportunity"
                assessment_color = "red"
            
            # Display colored assessment
            st.markdown(f"<h3 style='color:{assessment_color}'>{assessment}</h3>", unsafe_allow_html=True)
            
            # List key strengths and weaknesses
            strengths = []
            weaknesses = []
            
            if cash_on_cash >= 8:
                strengths.append("Strong cash on cash return")
            elif cash_on_cash < 4:
                weaknesses.append("Low cash on cash return")
                
            if cap_rate >= 6:
                strengths.append("Strong cap rate")
            elif cap_rate < 4:
                weaknesses.append("Low cap rate")
                
            if monthly_cash_flow > 200:
                strengths.append("Strong positive cash flow")
            elif monthly_cash_flow < 0:
                weaknesses.append("Negative cash flow")
                
            if total_roi > 50:
                strengths.append(f"Strong total ROI over {investment_horizon} years")
            elif total_roi < 20:
                weaknesses.append(f"Low total ROI over {investment_horizon} years")
            
            # Display strengths and weaknesses
            if strengths:
                st.markdown("**Strengths:**")
                for strength in strengths:
                    st.markdown(f"- {strength}")
                    
            if weaknesses:
                st.markdown("**Weaknesses:**")
                for weakness in weaknesses:
                    st.markdown(f"- {weakness}")
            
            # Add a disclaimer
            st.caption("Note: These calculations are estimates based on the provided inputs. Actual results may vary based on market conditions, property management, and other factors.")
            
            # Display a chart showing cash flow over time
            st.subheader("Cash Flow Projection")
            
            # Create data for the chart
            years = list(range(1, investment_horizon + 1))
            annual_cash_flows = [(roi_metrics['monthly_cash_flow'] * 12) * (1.03 ** (year - 1)) for year in years]
            
            # Create the chart
            fig = px.bar(
                x=years, 
                y=annual_cash_flows,
                labels={'x': 'Year', 'y': 'Annual Cash Flow ($)'},
                title='Projected Annual Cash Flow'
            )
            
            fig.update_traces(marker_color='blue')
            st.plotly_chart(fig, use_container_width=True)
            
            # Display a table with year-by-year projections
            st.subheader("Year-by-Year Projections")
            
            # Create projection data
            projection_data = []
            property_value = property_price
            loan_balance = property_price * (1 - down_payment_pct / 100)
            
            for year in range(1, investment_horizon + 1):
                # Calculate appreciation for this year
                annual_appreciation_rate = appreciation_rate if appreciation_override > 0 else roi_metrics['appreciation_rate']
                property_value *= (1 + annual_appreciation_rate / 100)
                
                # Calculate loan paydown
                # Simple approximation of loan balance
                if loan_balance > 0:
                    annual_payment = mortgage_payment * 12
                    annual_interest = loan_balance * (interest_rate / 100)
                    principal_payment = min(annual_payment - annual_interest, loan_balance)
                    loan_balance -= principal_payment
                
                # Calculate equity
                equity = property_value - loan_balance
                
                # Calculate cash flow with small inflation adjustment for expenses
                annual_cash_flow = annual_cash_flows[year-1]
                
                # Add to projection data
                projection_data.append({
                    'Year': year,
                    'Property Value': f"${property_value:.2f}",
                    'Loan Balance': f"${loan_balance:.2f}",
                    'Equity': f"${equity:.2f}",
                    'Annual Cash Flow': f"${annual_cash_flow:.2f}"
                })
            
            # Create DataFrame and display
            projection_df = pd.DataFrame(projection_data)
            st.dataframe(projection_df, use_container_width=True)
        else:
            # Show instructions when first loading the tab
            st.info("Enter property details in the form on the left and click 'Analyze Investment' to see results.")
            
            # Display educational content about investment metrics
            st.subheader("Understanding Investment Metrics")
            
            metrics_expander = st.expander("Key Investment Metrics Explained", expanded=False)
            with metrics_expander:
                st.markdown("""
                - **Cap Rate**: The ratio of net operating income (NOI) to property value. Higher values indicate better return potential.
                - **Cash on Cash Return**: Annual cash flow divided by total cash invested. Measures the cash income earned on cash invested.
                - **Cash Flow**: The money left over after all expenses and mortgage payments have been paid.
                - **ROI (Return on Investment)**: The total return including appreciation and cash flow, expressed as a percentage of initial investment.
                - **Equity Growth**: Increase in ownership value from loan paydown and property appreciation.
                """)
                
            strategy_expander = st.expander("Investment Strategies", expanded=False)
            with strategy_expander:
                st.markdown("""
                **Cash Flow Strategy**: Focus on properties with strong monthly cash flow. Look for:
                - Cap rate above 6%
                - Cash on cash return above 8%
                - Positive monthly cash flow
                
                **Appreciation Strategy**: Focus on properties likely to increase in value. Look for:
                - Properties in up-and-coming areas
                - Areas with strong economic and population growth
                - Properties where improvements can add significant value
                
                **Balanced Approach**: Look for properties with:
                - Moderate cash flow (at least break-even)
                - Good appreciation potential
                - Opportunity to force appreciation through improvements
                """)

# Tab 5: Link Scraper
with tab5:
    st.header("Link Scraper")
    st.markdown("""
    This tool allows you to scrape links from any website. Enter a URL below to extract all links from that page.
    You can use this to find property listings on websites not directly supported by the main scraper.
    """)
    
    # Create a form for link scraping
    with st.form(key="link_scraper_form"):
        url = st.text_input("Website URL", placeholder="https://example.com")
        max_links = st.slider("Maximum Number of Links", min_value=10, max_value=500, value=100)
        same_domain_only = st.checkbox("Only scrape links from the same domain", value=True)
        
        # Advanced options
        with st.expander("Advanced Options"):
            link_pattern = st.text_input(
                "Link Pattern (regex, optional)", 
                placeholder="property|listing|home",
                help="Optional regex pattern to filter links by. Example: 'property|listing|home' will only return links containing these words."
            )
            
            use_specific_selector = st.checkbox("Use CSS Selector", value=False, 
                                              help="Use a specific CSS selector to target only certain elements containing links")
            
            if use_specific_selector:
                css_selector = st.text_input(
                    "CSS Selector", 
                    placeholder="div.property-listings a",
                    help="CSS selector to target specific elements. Example: 'div.property-listings a' targets all anchor tags within elements with class 'property-listings'"
                )
        
        # Submit button
        scrape_links_button = st.form_submit_button(label="Scrape Links")
    
    # Handle link scraping
    if scrape_links_button:
        if not url:
            st.error("Please enter a URL to scrape")
        else:
            with st.spinner(f"Scraping links from {url}..."):
                try:
                    # Call the appropriate scraping function based on user selection
                    if use_specific_selector and css_selector:
                        links_df = extract_specific_links(url, css_selector, max_links, link_pattern)
                        scrape_method = f"CSS Selector: '{css_selector}'"
                    else:
                        links_df = scrape_links(url, max_links, link_pattern, same_domain_only)
                        scrape_method = "General link extraction"
                    
                    # Display results
                    if not links_df.empty:
                        st.success(f"Successfully scraped {len(links_df)} links!")
                        
                        # Display a summary
                        st.subheader("Scraping Summary")
                        st.markdown(f"""
                        - **Source URL:** {url}
                        - **Links Found:** {len(links_df)}
                        - **Method:** {scrape_method}
                        - **Link Pattern Filter:** {link_pattern if link_pattern else "None"}
                        - **Same Domain Only:** {"Yes" if same_domain_only else "No"}
                        """)
                        
                        # Create tabs for different views
                        link_tab1, link_tab2, link_tab3 = st.tabs(["Table View", "List View", "Analysis"])
                        
                        # Table view
                        with link_tab1:
                            st.dataframe(links_df, use_container_width=True)
                            
                        # List view
                        with link_tab2:
                            for idx, row in links_df.iterrows():
                                st.markdown(f"{idx+1}. [{row['text'] if row['text'] else row['url']}]({row['url']})")
                        
                        # Analysis view
                        with link_tab3:
                            # Analyze domains
                            if 'domain' in links_df.columns:
                                domain_counts = links_df['domain'].value_counts()
                                
                                # Display domain distribution
                                st.subheader("Domain Distribution")
                                
                                # Create a bar chart
                                fig = px.bar(
                                    x=domain_counts.index, 
                                    y=domain_counts.values,
                                    labels={'x': 'Domain', 'y': 'Count'},
                                    title='Link Distribution by Domain'
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Analyze link text
                            if 'text' in links_df.columns:
                                # Filter out empty text
                                text_df = links_df[links_df['text'].notna() & (links_df['text'] != '')]
                                
                                if not text_df.empty:
                                    # Display common words in link text
                                    st.subheader("Common Words in Link Text")
                                    
                                    # Extract words and count frequencies
                                    all_text = ' '.join(text_df['text'].str.lower())
                                    words = all_text.split()
                                    word_counts = {}
                                    
                                    # Filter out very common words
                                    stop_words = ['a', 'the', 'and', 'of', 'to', 'in', 'is', 'it', 'that', 'for', 'on', 'with']
                                    
                                    for word in words:
                                        # Clean the word
                                        word = word.strip('.,!?()[]{}"\'')
                                        if word and len(word) > 2 and word not in stop_words:
                                            if word in word_counts:
                                                word_counts[word] += 1
                                            else:
                                                word_counts[word] = 1
                                    
                                    # Sort by frequency
                                    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
                                    
                                    # Display the top words
                                    top_words = sorted_words[:20]
                                    words_df = pd.DataFrame(top_words, columns=['Word', 'Frequency'])
                                    
                                    fig = px.bar(
                                        words_df,
                                        x='Word',
                                        y='Frequency',
                                        title='Top 20 Words in Link Text'
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                        
                        # Export options
                        st.subheader("Export Options")
                        export_col1, export_col2 = st.columns(2)
                        
                        with export_col1:
                            if st.button("Export to Google Sheets", key="export_links_sheets_button"):
                                st.session_state.export_data = links_df
                                st.session_state.active_tab = "export"
                                st.rerun()
                        
                        with export_col2:
                            # Create a CSV download button
                            @st.cache_data
                            def convert_df_to_csv(df):
                                return df.to_csv(index=False).encode('utf-8')
                            
                            csv = convert_df_to_csv(links_df)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name="scraped_links.csv",
                                mime="text/csv",
                                key="download_links_csv"
                            )
                    else:
                        st.warning("No links found. Try adjusting your scraping parameters.")
                except Exception as e:
                    st.error(f"Error scraping links: {str(e)}")

# Tab 6: Google Sheets Export
with tab6:
    st.header("Google Sheets Export")
    st.markdown("""
    Export property data to Google Sheets for further analysis or sharing with others.
    You can export either your scraped listings or your comparison list.
    """)
    
    # Check if we have data to export
    has_property_data = not st.session_state.properties_df.empty
    has_comparison_data = len(st.session_state.comparison_list) > 0
    has_favorite_data = len(st.session_state.favorites) > 0
    has_link_data = hasattr(st.session_state, 'export_data') and not st.session_state.export_data.empty
    
    # Check if any data is available for export
    if has_property_data or has_comparison_data or has_favorite_data or has_link_data:
        # Create a form for export
        with st.form(key="sheet_export_form"):
            # Data source selection
            data_source = st.radio(
                "Select Data to Export",
                ["Scraped Properties", "Comparison List", "Favorites", "Custom Data"],
                index=0 if has_property_data else (1 if has_comparison_data else (2 if has_favorite_data else 3)),
                disabled=False
            )
            
            # Sheet name
            spreadsheet_name = st.text_input(
                "Google Sheet Name", 
                value=f"Real Estate Data - {dt.datetime.now().strftime('%Y-%m-%d')}"
            )
            
            # Option to append to existing sheet
            append_option = st.checkbox("Append to existing sheet (if available)", value=False)
            
            # Submit button
            export_button = st.form_submit_button(label="Export to Google Sheets")
        
        # Handle export
        if export_button:
            # Prepare the data for export
            if data_source == "Scraped Properties" and has_property_data:
                export_df = st.session_state.properties_df
            elif data_source == "Comparison List" and has_comparison_data:
                export_df = pd.DataFrame(st.session_state.comparison_list)
            elif data_source == "Favorites" and has_favorite_data:
                export_df = pd.DataFrame(st.session_state.favorites)
            elif data_source == "Custom Data" and has_link_data:
                export_df = st.session_state.export_data
            else:
                st.error("No data available for the selected source.")
                export_df = None
            
            # Process the export
            if export_df is not None and not export_df.empty:
                with st.spinner("Exporting to Google Sheets..."):
                    try:
                        # Execute the export
                        result = export_dataframe_to_sheet(
                            export_df,
                            spreadsheet_name=spreadsheet_name,
                            append=append_option
                        )
                        
                        if "error" not in result:
                            st.success("Export successful!")
                            
                            # Display the URL
                            st.markdown(f"**Sheet URL:** [{result['spreadsheet_url']}]({result['spreadsheet_url']})")
                            
                            # Display additional info
                            st.markdown(f"""
                            - **Spreadsheet Name:** {result['spreadsheet_name']}
                            - **Worksheet Name:** {result['worksheet_name']}
                            - **Rows Exported:** {result['rows_exported']}
                            - **Columns Exported:** {result['columns_exported']}
                            """)
                        else:
                            st.error(f"Export failed: {result['error']}")
                    except Exception as e:
                        st.error(f"Error during export: {str(e)}")
    else:
        st.info("No data available for export. Scrape some properties or add items to your comparison list first.")