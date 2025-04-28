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

# Tab 8: Stock Portfolio Tracker
def portfolio_tracker():
    st.subheader("Stock Portfolio Tracker")
    st.markdown("Track your stock investments without storing any data. All information is kept only in your current session.")
    
    # Initialize portfolio in session state if it doesn't exist
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = []
        
    # Portfolio entry form
    st.write("Add stocks to your portfolio:")
    
    port_col1, port_col2, port_col3 = st.columns([2, 1, 1])
    
    with port_col1:
        stock_symbol = st.text_input("Stock Symbol", key="portfolio_symbol_input").upper()
    
    with port_col2:
        shares = st.number_input("Number of Shares", min_value=0.01, value=1.0, step=0.01, key="portfolio_shares_input")
    
    with port_col3:
        purchase_price = st.number_input("Purchase Price ($)", min_value=0.01, value=100.0, step=0.01, key="portfolio_price_input")
        
    # Add button
    if st.button("Add to Portfolio", key="add_portfolio_button"):
        if stock_symbol:
            # Check if the symbol is valid by trying to get current price
            try:
                stock_data = yf.Ticker(stock_symbol)
                current_info = stock_data.info
                if 'regularMarketPrice' in current_info:
                    current_price = current_info['regularMarketPrice']
                    
                    # Calculate position value
                    position_value = shares * purchase_price
                    current_value = shares * current_price
                    profit_loss = current_value - position_value
                    profit_loss_pct = (profit_loss / position_value) * 100 if position_value > 0 else 0
                    
                    # Add to portfolio
                    st.session_state.portfolio.append({
                        'symbol': stock_symbol,
                        'shares': shares,
                        'purchase_price': purchase_price,
                        'current_price': current_price,
                        'position_value': position_value,
                        'current_value': current_value,
                        'profit_loss': profit_loss,
                        'profit_loss_pct': profit_loss_pct
                    })
                    
                    st.success(f"Added {shares} shares of {stock_symbol} to your portfolio")
                else:
                    st.error(f"Could not get price information for {stock_symbol}")
            except Exception as e:
                st.error(f"Error adding stock to portfolio: {str(e)}")
        else:
            st.warning("Please enter a stock symbol")
            
    # Display portfolio
    if st.session_state.portfolio:
        st.subheader("Your Portfolio")
        
        # Convert portfolio to DataFrame for easier display
        portfolio_df = pd.DataFrame(st.session_state.portfolio)
        
        # Calculate totals
        total_investment = portfolio_df['position_value'].sum()
        total_current_value = portfolio_df['current_value'].sum()
        total_profit_loss = portfolio_df['profit_loss'].sum()
        total_profit_loss_pct = (total_profit_loss / total_investment) * 100 if total_investment > 0 else 0
        
        # Display summary metrics
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric("Total Investment", f"${total_investment:.2f}")
            
        with metric_col2:
            st.metric("Current Value", f"${total_current_value:.2f}")
            
        with metric_col3:
            st.metric("Total Profit/Loss", 
                     f"${total_profit_loss:.2f}",
                     f"{total_profit_loss_pct:.2f}%")
        
        # Display portfolio table
        st.dataframe(
            portfolio_df.assign(
                shares=portfolio_df['shares'].map(lambda x: f"{x:.2f}"),
                purchase_price=portfolio_df['purchase_price'].map(lambda x: f"${x:.2f}"),
                current_price=portfolio_df['current_price'].map(lambda x: f"${x:.2f}"),
                position_value=portfolio_df['position_value'].map(lambda x: f"${x:.2f}"),
                current_value=portfolio_df['current_value'].map(lambda x: f"${x:.2f}"),
                profit_loss=portfolio_df['profit_loss'].map(lambda x: f"${x:.2f}"),
                profit_loss_pct=portfolio_df['profit_loss_pct'].map(lambda x: f"{x:.2f}%")
            ),
            use_container_width=True,
            column_config={
                "symbol": "Symbol",
                "shares": "Shares",
                "purchase_price": "Purchase Price",
                "current_price": "Current Price",
                "position_value": "Investment",
                "current_value": "Current Value",
                "profit_loss": "Profit/Loss",
                "profit_loss_pct": "Profit/Loss %"
            }
        )
        
        # Clear portfolio button
        if st.button("Clear Portfolio", key="clear_portfolio_button"):
            st.session_state.portfolio = []
            st.rerun()
            
        st.caption("Note: Portfolio data is only stored in your current session and will be cleared when you refresh the page.")
        
    else:
        st.info("Your portfolio is empty. Add stocks to track your investments.")