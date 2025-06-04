import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from io import BytesIO
import time
import os
import numpy as np
import database as db
from nsetools import Nse
import streamlit.components.v1 as components

# Set page configuration
st.set_page_config(
    page_title="PROJECTX - Financial Dashboard",
    page_icon="📈",
    layout="wide"
)

# Create a splash screen element
def create_splash_screen():
    # Create a container with styling for the splash screen
    st.markdown("""
    <style>
    .splash-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100vh;
        background: linear-gradient(to bottom, #1e3c72, #2a5298);
        color: white;
        text-align: center;
        padding: 2rem;
    }
    .splash-title {
        font-size: 5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .splash-subtitle {
        font-size: 1.5rem;
        margin-bottom: 2rem;
    }
    </style>
    
    <div class="splash-container">
        <div class="splash-title">PROJECTX</div>
        <div class="splash-subtitle">Financial Ecosystem</div>
    </div>
    """, unsafe_allow_html=True)

# Initialize session state variables
if 'splash_shown' not in st.session_state:
    st.session_state.splash_shown = False
    
# Get demo user
if 'user_id' not in st.session_state:
    try:
        user = db.get_or_create_user("demo_user", "demo@example.com")
        st.session_state.user_id = user.id
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        st.session_state.user_id = 1  # Default user ID

# Load user preferences from database
if 'preferences_loaded' not in st.session_state:
    try:
        user_prefs = db.get_user_preferences(st.session_state.user_id)
        
        # Load preferred theme
        st.session_state.theme = user_prefs.theme
        
        # Load default app
        st.session_state.selected_app = user_prefs.default_app
        
        # Load favorite symbols
        st.session_state.favorite_symbols = user_prefs.favorite_symbols_list
        
        # Load chart preferences
        chart_prefs = user_prefs.chart_preferences_dict
        st.session_state.show_ma = chart_prefs.get("show_moving_averages", True)
        st.session_state.selected_ma = chart_prefs.get("default_ma_periods", [20, 50])
        st.session_state.compare_benchmark = True
    except Exception as e:
        # Set default values if database connection fails
        st.session_state.theme = "light"
        st.session_state.selected_app = "Stock Analysis"
        st.session_state.favorite_symbols = ["TATASTEEL", "RELIANCE", "TATAPWR"]
        st.session_state.show_ma = True
        st.session_state.selected_ma = [20, 50]
        st.session_state.compare_benchmark = True
    
    # Mark preferences as loaded
    st.session_state.preferences_loaded = True
    
# Initialize default app values in session state
if 'symbol' not in st.session_state:
    st.session_state.symbol = "TATASTEEL.NS"
if 'days' not in st.session_state:
    st.session_state.days = 365
if 'watchlist_id' not in st.session_state:
    # Get user's default watchlist
    try:
        watchlists = db.get_user_watchlists(st.session_state.user_id)
        if watchlists:
            st.session_state.watchlist_id = watchlists[0].id
        else:
            # Create a default watchlist if none exists
            watchlist = db.Watchlist(name="My Watchlist", user_id=st.session_state.user_id)
            db_session = db.SessionLocal()
            db_session.add(watchlist)
            db_session.commit()
            db_session.refresh(watchlist)
            db_session.close()
            st.session_state.watchlist_id = watchlist.id
    except Exception as e:
        # Default ID if database connection fails
        st.session_state.watchlist_id = 1
        
# Initialize Trading variables
if 'trade_mode' not in st.session_state:
    st.session_state.trade_mode = "paper"  # Options: paper, live
if 'trading_capital' not in st.session_state:
    st.session_state.trading_capital = 100000.0  # Initial paper trading capital

# Show splash screen for 2 seconds
if not st.session_state.splash_shown:
    create_splash_screen()
    time.sleep(2)
    st.session_state.splash_shown = True
    st.rerun()

# Title and description
st.title("📈 PROJECTX Financial Dashboard")
st.markdown("Complete financial ecosystem with stock analysis, investment tracking, and more.")

# Sidebar for navigation and inputs
with st.sidebar:
    st.header("Navigation")
    
    # App selection
    app_options = ["Stock Analysis", "Trading Platform", "TradingView Charts", "India Market", "My Portfolio Tracker", "Growth Tracker", "Dhan Trading", "Investment Portfolio", "Telegram Alerts"]
    st.session_state.selected_app = st.radio("Select Application", app_options)
    
    st.markdown("---")
    st.header("Settings")
    
    # Stock symbol input (for Stock Analysis)
    if st.session_state.selected_app == "Stock Analysis" or st.session_state.selected_app == "Trading Platform":
        st.session_state.symbol = st.text_input("Enter Stock Symbol (e.g., TATASTEEL, RELIANCE)", value=st.session_state.symbol).upper()
        
        # Time period selection
        period_options = {
            "1 Month": 30,
            "3 Months": 90,
            "6 Months": 180,
            "1 Year": 365,
            "2 Years": 730,
            "5 Years": 1825,
        }
        
        selected_period = st.selectbox("Select Time Period", list(period_options.keys()))
        st.session_state.days = period_options[selected_period]
        
        # Moving averages selection
        st.session_state.show_ma = st.checkbox("Show Moving Averages", value=st.session_state.show_ma)
        if st.session_state.show_ma:
            ma_options = [5, 20, 50, 100, 200]
            st.session_state.selected_ma = st.multiselect("Select Moving Average Periods", ma_options, default=st.session_state.selected_ma)
    
    # Trading Platform settings
    elif st.session_state.selected_app == "Trading Platform":
        st.subheader("Trading Settings")
        st.session_state.trade_mode = st.radio("Trading Mode", ["Paper Trading", "Live Trading"])
        if st.session_state.trade_mode == "Paper Trading":
            st.session_state.trading_capital = st.number_input("Paper Trading Capital", 
                                                          min_value=10000.0, 
                                                          max_value=10000000.0, 
                                                          value=float(st.session_state.trading_capital), 
                                                          step=10000.0,
                                                          format="%.2f")
    
    # Dhan Trading settings
    elif st.session_state.selected_app == "Dhan Trading":
        st.subheader("Trading Settings")
        trading_mode = st.selectbox("Trading Mode", ["Paper Trading", "Live Trading"])
        risk_level = st.slider("Risk Level", 1, 10, 5)
        
    # Investment Portfolio settings
    elif st.session_state.selected_app == "Investment Portfolio":
        st.subheader("Portfolio Settings")
        st.selectbox("Portfolio View", ["Summary", "Detailed", "Performance"])
        st.date_input("Date Range Start", datetime.today() - timedelta(days=365))
        
    # Growth Tracker settings
    elif st.session_state.selected_app == "Growth Tracker":
        st.subheader("Growth Settings")
        growth_metric = st.selectbox("Growth Metric", ["Total Returns", "CAGR", "Monthly Growth"])
        st.session_state.compare_benchmark = st.checkbox("Compare with Benchmark", value=st.session_state.compare_benchmark)
        
    # Telegram Alerts settings
    elif st.session_state.selected_app == "Telegram Alerts":
        st.subheader("Alert Settings")
        alert_type = st.multiselect("Alert Types", ["Price Movement", "Volume Spike", "News", "Earnings"])
        notify_method = st.radio("Notification Method", ["Telegram", "Email", "Both"])
    
    # Refresh data button
    if st.button("Refresh Data"):
        st.rerun()
        
    # Add app info at the bottom of sidebar
    st.markdown("---")
    st.markdown("### PROJECTX v1.0")
    st.markdown("Financial Ecosystem")
    st.markdown("© 2025 All rights reserved")

# Function to get stock data
@st.cache_data(ttl=3600)  # Cache data for an hour
def get_stock_data(ticker, days):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    
    try:
        # Handle Indian stock symbols
        if ticker.endswith('.NS') or ticker.endswith('.BO'):
            # Symbol already has exchange suffix
            query_ticker = ticker
        else:
            # Check if it's an Indian stock by trying with NSE suffix first
            try:
                test_data = yf.download(f"{ticker}.NS", period='1d')
                if not test_data.empty:
                    query_ticker = f"{ticker}.NS"
                    st.info(f"Using NSE exchange for {ticker}")
                else:
                    # Try BSE suffix
                    test_data = yf.download(f"{ticker}.BO", period='1d')
                    if not test_data.empty:
                        query_ticker = f"{ticker}.BO"
                        st.info(f"Using BSE exchange for {ticker}")
                    else:
                        # Use as-is (probably US stock)
                        query_ticker = ticker
            except Exception as e:
                # If error in checking, use as provided
                query_ticker = ticker
                st.warning(f"Could not verify exchange for {ticker}. Using as provided.")
        
        # Get historical data
        st.info(f"Fetching data for {query_ticker}...")
        data = yf.download(query_ticker, start=start_date, end=end_date)
        
        # Check if data was found
        if data.empty:
            st.error(f"No data found for {query_ticker}. Please check the symbol.")
            return None, None
            
        # Get company info
        ticker_info = yf.Ticker(query_ticker)
        info = ticker_info.info
        
        # Also get recommendations, institutional holders, and balance sheet
        try:
            recommendations = ticker_info.recommendations
            holders = ticker_info.institutional_holders
            balance_sheet = ticker_info.balance_sheet
            
            # Include these in the info dictionary
            info['recommendations'] = recommendations
            info['institutional_holders'] = holders
            info['balance_sheet'] = balance_sheet
            
            # Get more financial data
            financials = ticker_info.financials
            cashflow = ticker_info.cashflow
            earnings = ticker_info.earnings
            
            info['financials'] = financials
            info['cashflow'] = cashflow
            info['earnings'] = earnings
            
            # Get news
            try:
                news = ticker_info.news
                info['news'] = news
            except:
                pass
                
        except Exception as e:
            # Not all stocks have this data, so just continue
            pass
        
        return data, info
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None, None

# Function to create stock price chart
def create_stock_chart(data, ticker, selected_ma=None):
    fig = go.Figure()
    
    # Add candlestick chart
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name=ticker,
        increasing_line_color='green',
        decreasing_line_color='red'
    ))
    
    # Add moving averages if selected
    if selected_ma and len(selected_ma) > 0:
        for ma in selected_ma:
            ma_col = f'MA_{ma}'
            data[ma_col] = data['Close'].rolling(window=ma).mean()
            fig.add_trace(go.Scatter(
                x=data.index, 
                y=data[ma_col],
                name=f'{ma}-day MA',
                line=dict(width=1.5)
            ))
    
    # Configure chart layout
    fig.update_layout(
        title=f'{ticker} Stock Price',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    return fig

# Function to create volume chart
def create_volume_chart(data, ticker):
    fig = go.Figure()
    
    # Add volume bars
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Volume'],
        name='Volume',
        marker=dict(color='rgba(0, 0, 255, 0.5)')
    ))
    
    # Configure chart layout
    fig.update_layout(
        title=f'{ticker} Trading Volume',
        xaxis_title='Date',
        yaxis_title='Volume',
        height=300,
        margin=dict(l=50, r=50, t=50, b=50),
    )
    
    return fig

# Function to create download link for CSV
def get_csv_download_link(data, filename):
    csv = data.to_csv(index=True)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV file</a>'
    return href

# Function to display company info
def display_company_info(info):
    if not info:
        st.warning("Company information not available")
        return
    
    # Create two columns for company info
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            st.subheader(info.get('longName', 'Unknown Company'))
            st.write(f"**Symbol:** {info.get('symbol', 'N/A')}")
            st.write(f"**Industry:** {info.get('industry', 'N/A')}")
            st.write(f"**Sector:** {info.get('sector', 'N/A')}")
            st.write(f"**Country:** {info.get('country', 'N/A')}")
            st.write(f"**Exchange:** {info.get('exchange', 'N/A')}")
        except Exception as e:
            st.warning(f"Error displaying company metadata: {e}")
    
    with col2:
        try:
            st.write(f"**Market Cap:** ${info.get('marketCap', 0) / 1e9:.2f} Billion")
            st.write(f"**P/E Ratio:** {info.get('trailingPE', 'N/A')}")
            st.write(f"**Dividend Yield:** {info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "**Dividend Yield:** N/A")
            st.write(f"**52 Week Range:** ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}")
            st.write(f"**Previous Close:** ${info.get('previousClose', 'N/A')}")
        except Exception as e:
            st.warning(f"Error displaying financial metrics: {e}")
    
    # Business summary if available
    if info.get('longBusinessSummary'):
        with st.expander("Business Summary"):
            st.write(info.get('longBusinessSummary'))
    
    # Display news if available
    if info.get('news'):
        with st.expander("Recent News"):
            news_items = info.get('news')
            for i, news in enumerate(news_items[:5]):  # Show top 5 news
                st.markdown(f"### {news.get('title', 'News Title')}")
                st.write(f"**Source:** {news.get('publisher', 'Unknown')}")
                
                # Safely handle the publish time which might be None
                publish_time = news.get('providerPublishTime')
                if publish_time:
                    try:
                        time_str = datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d %H:%M')
                        st.write(f"**Published:** {time_str}")
                    except:
                        st.write("**Published:** Unknown")
                else:
                    st.write("**Published:** Unknown")
                    
                st.write(news.get('summary', 'No summary available'))
                if i < len(news_items) - 1:
                    st.markdown("---")
    
    # Display financial data if available
    if info.get('financials') is not None:
        with st.expander("Financial Data"):
            try:
                financials = info.get('financials')
                st.write("### Income Statement (Last 4 Quarters)")
                st.dataframe(financials)
            except Exception as e:
                st.write(f"Error displaying financials: {e}")
                
    # Display institutional holders if available
    if info.get('institutional_holders') is not None:
        with st.expander("Institutional Holders"):
            try:
                holders = info.get('institutional_holders')
                st.dataframe(holders)
            except Exception as e:
                st.write(f"Error displaying institutional holders: {e}")

    # Display recommendations if available
    if info.get('recommendations') is not None:
        with st.expander("Analyst Recommendations"):
            try:
                recommendations = info.get('recommendations')
                st.dataframe(recommendations)
            except Exception as e:
                st.write(f"Error displaying recommendations: {e}")

# Main app functions
def show_stock_analysis():
    # Use session state values
    symbol = st.session_state.symbol if 'symbol' in st.session_state else "TATASTEEL"
    days = st.session_state.days if 'days' in st.session_state else 365
    show_ma = st.session_state.show_ma if 'show_ma' in st.session_state else True
    selected_ma = st.session_state.selected_ma if 'selected_ma' in st.session_state else [20, 50]
    
    # Add Indian NSE stock lookup by sector
    st.sidebar.subheader("NSE India Stocks")
    
    # Organize NSE stocks by sector
    nse_sectors = {
        "Energy": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "BPCL.NS", "GAIL.NS", "ADANIGREEN.NS", "TATAPOWER.NS", "TATAPWR.NS"],
        "Financial": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "HDFC.NS"],
        "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "TECHM.NS", "HCLTECH.NS", "LTIM.NS", "MPHASIS.NS"],
        "Manufacturing": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "TATAMOTORS.NS", "MARUTI.NS", "M&M.NS", "HEROMOTOCO.NS", "ULTRACEMCO.NS"],
        "FMCG": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "DABUR.NS", "MARICO.NS", "GODREJCP.NS", "BRITANNIA.NS"],
        "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "BIOCON.NS"]
    }
    
    # Select sector first
    selected_sector = st.sidebar.selectbox("Select Sector", list(nse_sectors.keys()))
    
    # Then show stocks in that sector
    selected_indian_stock = st.sidebar.selectbox("Select NSE Stock", nse_sectors[selected_sector])
    if st.sidebar.button("Load Selected Stock"):
        symbol = selected_indian_stock
        st.session_state.symbol = selected_indian_stock
        st.rerun()
    
    # Get stock data
    data, info = get_stock_data(symbol, days)
    
    if data is not None and len(data) > 0:
        # Display company info
        st.header("Company Information")
        display_company_info(info)
        
        # Historical stock price chart
        st.header("Stock Price Chart")
        
        # Calculate moving averages for the chart
        ma_list = []
        if show_ma and 'selected_ma' in locals():
            ma_list = selected_ma
        
        # Create and display the price chart
        price_chart = create_stock_chart(data, symbol, ma_list)
        st.plotly_chart(price_chart, use_container_width=True)
        
        # Create and display the volume chart
        volume_chart = create_volume_chart(data, symbol)
        st.plotly_chart(volume_chart, use_container_width=True)
        
        # Financial metrics table
        st.header("Key Financial Metrics")
        
        # Prepare the data for display
        metrics_df = data.copy()
        metrics_df = metrics_df.round(2)
        
        # Add moving averages to the data if selected
        if show_ma and 'selected_ma' in locals():
            for ma in selected_ma:
                metrics_df[f'MA_{ma}'] = metrics_df['Close'].rolling(window=ma).mean().round(2)
        
        # Add daily returns
        metrics_df['Daily Return %'] = (metrics_df['Close'].pct_change() * 100).round(2)
        
        # Display the data table
        st.dataframe(metrics_df, use_container_width=True)
        
        # Provide download link
        st.markdown(f"### Download Data")
        st.markdown(get_csv_download_link(metrics_df, f"{symbol}_stock_data.csv"), unsafe_allow_html=True)
        
        # Display latest stock stats
        st.header("Latest Stock Statistics")
        latest_data = data.iloc[-1]
        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
        
        with stats_col1:
            st.metric("Open", f"${float(latest_data['Open']):.2f}")
        
        with stats_col2:
            st.metric("High", f"${float(latest_data['High']):.2f}")
        
        with stats_col3:
            st.metric("Low", f"${float(latest_data['Low']):.2f}")
        
        with stats_col4:
            st.metric("Close", f"${float(latest_data['Close']):.2f}")
            
        # Calculate and display price change
        if len(data) > 1:
            prev_close = float(data.iloc[-2]['Close'])
            current_close = float(latest_data['Close'])
            price_change = current_close - prev_close
            percent_change = (price_change / prev_close) * 100
            
            change_col1, change_col2 = st.columns(2)
            
            with change_col1:
                st.metric("Price Change", f"${price_change:.2f}", delta=f"{price_change:.2f}")
            
            with change_col2:
                st.metric("% Change", f"{percent_change:.2f}%", delta=f"{percent_change:.2f}%")
    else:
        st.error(f"No data found for ticker {symbol}. Please check the symbol and try again.")

# New Trading Platform feature
def show_trading_platform():
    st.header("💹 Trading Platform")
    
    # Get the symbol and data
    symbol = st.session_state.symbol
    days = 30  # We'll show recent data for trading
    data, info = get_stock_data(symbol, days)
    
    if data is None or len(data) == 0:
        st.error(f"Could not load data for {symbol}. Please try another symbol.")
        return
    
    # Basic info about the stock
    st.subheader(f"Trading {info.get('longName', symbol)}")
    
    current_price = float(data.iloc[-1]['Close'])
    st.write(f"**Current Price:** ${current_price:.2f}")
    
    # Trading container
    st.subheader("Execute Trade")
    
    trading_tabs = st.tabs(["Place Order", "Order History", "Portfolio", "Market Watch"])
    
    with trading_tabs[0]:  # Place Order
        col1, col2, col3 = st.columns(3)
        
        with col1:
            order_type = st.selectbox("Order Type", ["Market", "Limit", "Stop Loss", "Stop Limit"])
            
        with col2:
            buy_sell = st.selectbox("Action", ["Buy", "Sell"])
            
        with col3:
            quantity = st.number_input("Quantity", min_value=1, value=10, step=1)
            
        if order_type != "Market":
            col1, col2 = st.columns(2)
            with col1:
                limit_price = st.number_input("Limit Price", 
                                            min_value=0.01, 
                                            value=current_price,
                                            step=0.01, 
                                            format="%.2f")
            
            if order_type in ["Stop Loss", "Stop Limit"]:
                with col2:
                    stop_price = st.number_input("Stop Price", 
                                            min_value=0.01, 
                                            value=current_price * 0.95 if buy_sell == "Buy" else current_price * 1.05,
                                            step=0.01, 
                                            format="%.2f")
        
        # Calculate estimated value
        estimated_value = quantity * current_price
        
        st.write(f"**Estimated Value:** ${estimated_value:.2f}")
        
        # Trading capital and buying power
        st.write(f"**Available Trading Capital:** ${st.session_state.trading_capital:.2f}")
        
        # Execute button
        if st.button("Execute Trade"):
            # In a real app, we would execute the trade here
            if buy_sell == "Buy" and estimated_value > st.session_state.trading_capital:
                st.error("Insufficient funds to execute this trade.")
            else:
                try:
                    # Record transaction
                    if buy_sell == "Buy":
                        # Deduct from capital
                        st.session_state.trading_capital -= estimated_value
                        # Add to database
                        db.add_stock_transaction(
                            st.session_state.user_id,
                            symbol,
                            "Buy",
                            quantity,
                            current_price
                        )
                        st.success(f"Successfully bought {quantity} shares of {symbol} at ${current_price:.2f}")
                    else:
                        # Add to capital
                        st.session_state.trading_capital += estimated_value
                        # Add to database
                        db.add_stock_transaction(
                            st.session_state.user_id,
                            symbol,
                            "Sell",
                            quantity,
                            current_price
                        )
                        st.success(f"Successfully sold {quantity} shares of {symbol} at ${current_price:.2f}")
                    
                    # Add to watchlist if not already there
                    if 'watchlist_id' in st.session_state:
                        db.add_stock_to_watchlist(st.session_state.watchlist_id, symbol)
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error executing trade: {e}")
    
    with trading_tabs[1]:  # Order History
        st.subheader("Order History")
        
        # Get transactions from database
        try:
            transactions = db.get_user_transactions(st.session_state.user_id, limit=20)
            
            if transactions:
                transactions_data = {
                    "Date": [],
                    "Symbol": [],
                    "Type": [],
                    "Quantity": [],
                    "Price": [],
                    "Value": []
                }
                
                for transaction, symbol in transactions:
                    transactions_data["Date"].append(transaction.date.strftime("%Y-%m-%d %H:%M"))
                    transactions_data["Symbol"].append(symbol)
                    transactions_data["Type"].append(transaction.transaction_type)
                    transactions_data["Quantity"].append(transaction.quantity)
                    transactions_data["Price"].append(f"${transaction.price:.2f}")
                    transactions_data["Value"].append(f"${transaction.quantity * transaction.price:.2f}")
                
                transactions_df = pd.DataFrame(transactions_data)
                st.dataframe(transactions_df, use_container_width=True)
            else:
                st.info("No transaction history yet. Execute a trade to see it here.")
        except Exception as e:
            st.error(f"Error loading transaction history: {e}")
            st.info("No transaction history available.")
    
    with trading_tabs[2]:  # Portfolio
        st.subheader("Your Portfolio")
        
        # Get portfolio data
        try:
            portfolios = db.get_user_portfolios(st.session_state.user_id)
            if portfolios:
                portfolio_id = portfolios[0].id
                portfolio_items = db.get_portfolio_items(portfolio_id)
                
                if portfolio_items:
                    portfolio_data = {
                        "Symbol": [],
                        "Quantity": [],
                        "Avg. Price": [],
                        "Current Price": [],
                        "Market Value": [],
                        "Gain/Loss": [],
                        "% Return": []
                    }
                    
                    total_investment = 0
                    total_current_value = 0
                    
                    for item in portfolio_items:
                        stock = item[0]  # Stock object
                        quantity = item[1]  # Quantity
                        avg_price = item[2]  # Average purchase price
                        
                        # Get current price
                        try:
                            stock_data = yf.Ticker(stock.symbol).history(period="1d")
                            current_price = stock_data['Close'].iloc[-1]
                        except:
                            current_price = avg_price  # Fallback
                        
                        market_value = quantity * current_price
                        investment = quantity * avg_price
                        gain_loss = market_value - investment
                        pct_return = (gain_loss / investment) * 100 if investment > 0 else 0
                        
                        total_investment += investment
                        total_current_value += market_value
                        
                        portfolio_data["Symbol"].append(stock.symbol)
                        portfolio_data["Quantity"].append(quantity)
                        portfolio_data["Avg. Price"].append(f"${avg_price:.2f}")
                        portfolio_data["Current Price"].append(f"${current_price:.2f}")
                        portfolio_data["Market Value"].append(f"${market_value:.2f}")
                        portfolio_data["Gain/Loss"].append(f"${gain_loss:.2f}")
                        portfolio_data["% Return"].append(f"{pct_return:.2f}%")
                    
                    st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True)
                    
                    # Portfolio summary
                    total_gain = total_current_value - total_investment
                    total_return_pct = (total_gain / total_investment) * 100 if total_investment > 0 else 0
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Investment", f"${total_investment:.2f}")
                    
                    with col2:
                        st.metric("Portfolio Value", f"${total_current_value:.2f}")
                    
                    with col3:
                        st.metric("Total Gain/Loss", f"${total_gain:.2f}", delta=f"{total_gain:.2f}")
                    
                    with col4:
                        st.metric("Portfolio Return", f"{total_return_pct:.2f}%", delta=f"{total_return_pct:.2f}%")
                    
                    # Add pie chart for portfolio allocation
                    fig = go.Figure(data=[go.Pie(
                        labels=portfolio_data["Symbol"],
                        values=[float(value.replace("$", "")) for value in portfolio_data["Market Value"]],
                        hole=.4,
                        marker_colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']
                    )])
                    
                    fig.update_layout(
                        title="Portfolio Allocation",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Your portfolio is empty. Execute a trade to build your portfolio.")
            else:
                st.info("No portfolio found. Please execute a trade to create one.")
        except Exception as e:
            st.error(f"Error loading portfolio: {e}")
            st.info("Portfolio data unavailable. Please try again later.")
    
    with trading_tabs[3]:  # Market Watch
        st.subheader("Market Watch")
        
        # Show popular indices
        st.write("### Market Indices")
        
        indices = ["^NSEI", "^BSESN", "^GSPC", "^DJI", "^IXIC"]
        indices_names = ["Nifty 50", "Sensex", "S&P 500", "Dow Jones", "NASDAQ"]
        
        indices_data = []
        
        for idx, index_symbol in enumerate(indices):
            try:
                index_data = yf.download(index_symbol, period="5d")
                if len(index_data) > 1:
                    current = index_data['Close'].iloc[-1]
                    prev = index_data['Close'].iloc[-2]
                    change = current - prev
                    change_pct = (change / prev) * 100
                    
                    indices_data.append({
                        "Index": indices_names[idx],
                        "Last": f"{current:.2f}",
                        "Change": f"{change:.2f}",
                        "% Change": f"{change_pct:.2f}%"
                    })
            except:
                continue
        
        if indices_data:
            st.dataframe(pd.DataFrame(indices_data), use_container_width=True)
        
        # Show watchlist
        st.write("### Your Watchlist")
        
        if 'watchlist_id' in st.session_state:
            try:
                watchlist_stocks = db.get_watchlist_stocks(st.session_state.watchlist_id)
                
                if watchlist_stocks:
                    watchlist_data = {
                        "Symbol": [],
                        "Last Price": [],
                        "Change": [],
                        "% Change": [],
                        "Volume": []
                    }
                    
                    for stock in watchlist_stocks:
                        try:
                            stock_data = yf.Ticker(stock.symbol).history(period="2d")
                            if len(stock_data) >= 2:
                                current = stock_data['Close'].iloc[-1]
                                prev = stock_data['Close'].iloc[-2]
                                change = current - prev
                                change_pct = (change / prev) * 100
                                volume = stock_data['Volume'].iloc[-1]
                                
                                watchlist_data["Symbol"].append(stock.symbol)
                                watchlist_data["Last Price"].append(f"${current:.2f}")
                                watchlist_data["Change"].append(f"${change:.2f}")
                                watchlist_data["% Change"].append(f"{change_pct:.2f}%")
                                watchlist_data["Volume"].append(f"{int(volume):,}")
                        except:
                            pass
                    
                    if watchlist_data["Symbol"]:
                        st.dataframe(pd.DataFrame(watchlist_data), use_container_width=True)
                    else:
                        st.info("Could not retrieve data for your watchlist stocks.")
                else:
                    st.info("Your watchlist is empty. Add stocks to your watchlist in the Watchlist section.")
            except Exception as e:
                st.error(f"Error loading watchlist: {e}")
                st.info("Watchlist data unavailable. Please try again later.")
        else:
            st.info("No watchlist found.")
        
        # Add to watchlist
        with st.form("add_stock_to_watchlist"):
            st.subheader("Add to Watchlist")
            new_symbol = st.text_input("Enter Symbol")
            submitted = st.form_submit_button("Add to Watchlist")
            
            if submitted and new_symbol and 'watchlist_id' in st.session_state:
                try:
                    # Add to watchlist
                    success = db.add_stock_to_watchlist(st.session_state.watchlist_id, new_symbol.upper())
                    if success:
                        st.success(f"Added {new_symbol.upper()} to watchlist!")
                    else:
                        st.info(f"{new_symbol.upper()} is already in your watchlist.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding to watchlist: {e}")

def show_growth_tracker():
    st.header("📊 Growth Tracker")
    
    # Sample growth visualization
    st.subheader("Portfolio Growth")
    
    # Create a simple demonstration chart
    dates = pd.date_range(start='2023-01-01', end='2025-05-15', freq='ME')
    portfolio_values = [10000.0]  # Use float to avoid type issues
    
    # Generate some hypothetical growth data
    for i in range(1, len(dates)):
        # Random monthly growth between -5% and +8%
        growth = np.random.uniform(-0.05, 0.08)
        new_value = portfolio_values[-1] * (1 + growth)
        portfolio_values.append(new_value)
    
    growth_df = pd.DataFrame({
        'Date': dates,
        'Portfolio Value': portfolio_values
    })
    
    # Plot the growth 
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=growth_df['Date'],
        y=growth_df['Portfolio Value'],
        name="Portfolio Value",
        line=dict(color='green', width=2)
    ))
    
    # Add S&P 500 benchmark if selected
    if st.session_state.compare_benchmark:
        # Generate benchmark data (S&P 500 approximate)
        sp500_values = [10000.0]  # Use float
        for i in range(1, len(dates)):
            # Random monthly growth for S&P 500 between -4% and +6%
            growth = np.random.uniform(-0.04, 0.06)
            new_value = sp500_values[-1] * (1 + growth)
            sp500_values.append(new_value)
        
        fig.add_trace(go.Scatter(
            x=growth_df['Date'],
            y=sp500_values,
            name="S&P 500",
            line=dict(color='blue', width=2, dash='dash')
        ))
    
    fig.update_layout(
        title="Portfolio Growth Over Time",
        xaxis_title="Date",
        yaxis_title="Value ($)",
        height=500,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Growth metrics
    st.subheader("Growth Metrics")
    metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
    
    with metrics_col1:
        # Total growth
        initial_value = portfolio_values[0]
        current_value = portfolio_values[-1]
        total_growth = ((current_value - initial_value) / initial_value) * 100
        st.metric("Total Growth", f"{total_growth:.2f}%", delta=f"{total_growth:.2f}%")
    
    with metrics_col2:
        # CAGR - Compound Annual Growth Rate
        years = len(dates) / 12
        cagr = (((current_value / initial_value) ** (1 / years)) - 1) * 100
        st.metric("CAGR", f"{cagr:.2f}%", delta=f"{cagr:.2f}%")
        
    with metrics_col3:
        # Volatility (standard deviation of monthly returns)
        monthly_returns = [(portfolio_values[i] / portfolio_values[i-1]) - 1 for i in range(1, len(portfolio_values))]
        volatility = np.std(monthly_returns) * 100
        st.metric("Monthly Volatility", f"{volatility:.2f}%")

def show_dhan_trading():
    st.header("💹 Dhan Trading Platform")
    
    # Tabs for different trading sections
    trade_tabs = st.tabs(["Market Overview", "My Positions", "Order Book", "Watchlist"])
    
    with trade_tabs[0]:  # Market Overview
        st.subheader("Market Overview")
        
        # Market indices
        indices_col1, indices_col2, indices_col3 = st.columns(3)
        
        with indices_col1:
            # Random value for Nifty 50
            nifty_value = 24500 + np.random.uniform(-200, 200)
            nifty_change = np.random.uniform(-1.5, 1.5)
            st.metric("NIFTY 50", f"{nifty_value:.2f}", delta=f"{nifty_change:.2f}%")
            
        with indices_col2:
            # Random value for Sensex
            sensex_value = 81000 + np.random.uniform(-500, 500)
            sensex_change = np.random.uniform(-1.5, 1.5)
            st.metric("SENSEX", f"{sensex_value:.2f}", delta=f"{sensex_change:.2f}%")
            
        with indices_col3:
            # Random value for Nifty Bank
            bank_value = 48000 + np.random.uniform(-300, 300)
            bank_change = np.random.uniform(-1.5, 1.5)
            st.metric("NIFTY BANK", f"{bank_value:.2f}", delta=f"{bank_change:.2f}%")
        
        # Top gainers and losers
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Gainers")
            gainers_data = {
                "Symbol": ["RELIANCE", "TCS", "BAJAJFINS", "HDFCBANK", "ADANIPORT"],
                "Price": [2780.45, 3941.20, 1640.75, 1590.80, 985.65],
                "Change %": [3.45, 2.78, 2.56, 2.12, 1.89]
            }
            gainers_df = pd.DataFrame(gainers_data)
            st.dataframe(gainers_df, use_container_width=True)
            
        with col2:
            st.subheader("Top Losers")
            losers_data = {
                "Symbol": ["INFY", "WIPRO", "TATAMOTORS", "SUNPHARMA", "CIPLA"],
                "Price": [1450.30, 480.75, 920.40, 1280.25, 1110.90],
                "Change %": [-2.85, -2.45, -2.10, -1.95, -1.75]
            }
            losers_df = pd.DataFrame(losers_data)
            st.dataframe(losers_df, use_container_width=True)
    
    with trade_tabs[1]:  # My Positions
        st.subheader("Current Positions")
        
        # Get actual portfolio data from database
        try:
            portfolios = db.get_user_portfolios(st.session_state.user_id)
            if portfolios:
                portfolio_id = portfolios[0].id
                portfolio_items = db.get_portfolio_items(portfolio_id)
                
                positions_data = {
                    "Symbol": [],
                    "Qty": [],
                    "Avg Price": [],
                    "LTP": [],
                    "P&L": [],
                    "P&L %": []
                }
                
                total_investment = 0
                total_current_value = 0
                
                # Process each portfolio item
                for item in portfolio_items:
                    stock = item[0]  # Stock object
                    quantity = item[1]  # Quantity
                    avg_price = item[2]  # Average purchase price
                    
                    # Get current price from Yahoo Finance
                    try:
                        ticker_data = yf.Ticker(stock.symbol)
                        current_price = ticker_data.history(period='1d')['Close'].iloc[-1]
                    except:
                        current_price = avg_price  # Fallback if can't get current price
                    
                    # Calculate values
                    invested = quantity * avg_price
                    current_item_value = quantity * current_price
                    pnl = current_item_value - invested
                    pnl_pct = (pnl / invested) * 100 if invested > 0 else 0
                    
                    # Add to totals
                    total_investment += invested
                    total_current_value += current_item_value
                    
                    # Add to dataframe
                    positions_data["Symbol"].append(stock.symbol)
                    positions_data["Qty"].append(quantity)
                    positions_data["Avg Price"].append(f"${avg_price:.2f}")
                    positions_data["LTP"].append(f"${current_price:.2f}")
                    positions_data["P&L"].append(f"${pnl:.2f}")
                    positions_data["P&L %"].append(f"{pnl_pct:.2f}%")
                
                if positions_data["Symbol"]:
                    positions_df = pd.DataFrame(positions_data)
                    st.dataframe(positions_df, use_container_width=True)
                    
                    # Calculate overall P&L
                    total_pnl = total_current_value - total_investment
                    pnl_percent = (total_pnl / total_investment) * 100 if total_investment > 0 else 0
                    
                    st.metric("Overall P&L", f"${total_pnl:.2f}", delta=f"{pnl_percent:.2f}%")
                else:
                    st.info("No positions in portfolio yet. Add some transactions in the Investment Portfolio section.")
            else:
                st.info("No portfolio found. Please set up your portfolio in the Investment Portfolio section.")
        except Exception as e:
            st.error(f"Error loading positions: {e}")
            st.info("Position data unavailable. Please try again later.")
    
    with trade_tabs[2]:  # Order Book
        st.subheader("Order Book")
        
        # Get actual transactions from database
        try:
            transactions = db.get_user_transactions(st.session_state.user_id, limit=10)
            
            if transactions:
                orders_data = {
                    "Order ID": [],
                    "Symbol": [],
                    "Type": [],
                    "Qty": [],
                    "Price": [],
                    "Status": [],
                    "Time": []
                }
                
                for idx, (transaction, symbol) in enumerate(transactions):
                    orders_data["Order ID"].append(f"ORD{transaction.id}")
                    orders_data["Symbol"].append(symbol)
                    orders_data["Type"].append(transaction.transaction_type)
                    orders_data["Qty"].append(transaction.quantity)
                    orders_data["Price"].append(f"${transaction.price:.2f}")
                    orders_data["Status"].append("EXECUTED")
                    orders_data["Time"].append(transaction.date.strftime("%H:%M:%S"))
                
                orders_df = pd.DataFrame(orders_data)
                st.dataframe(orders_df, use_container_width=True)
            else:
                st.info("No transactions yet. Add some in the Investment Portfolio section.")
        except Exception as e:
            st.error(f"Error loading order book: {e}")
            st.info("Order book unavailable. Please try again later.")
    
    with trade_tabs[3]:  # Watchlist
        st.subheader("Watchlist")
        
        # Get watchlist from database
        if 'watchlist_id' in st.session_state:
            try:
                watchlist_stocks = db.get_watchlist_stocks(st.session_state.watchlist_id)
                
                if watchlist_stocks:
                    watchlist_data = {
                        "Symbol": [],
                        "LTP": [],
                        "Change %": [],
                        "Volume": []
                    }
                    
                    # Get current data for each stock
                    for stock in watchlist_stocks:
                        try:
                            ticker_data = yf.Ticker(stock.symbol)
                            history = ticker_data.history(period='2d')
                            
                            if len(history) >= 2:
                                current_price = history['Close'].iloc[-1]
                                prev_price = history['Close'].iloc[-2]
                                change_pct = ((current_price - prev_price) / prev_price) * 100
                                volume = history['Volume'].iloc[-1] / 1000
                                volume_str = f"{volume:.1f}K" if volume < 1000 else f"{volume/1000:.2f}M"
                                
                                watchlist_data["Symbol"].append(stock.symbol)
                                watchlist_data["LTP"].append(f"${current_price:.2f}")
                                watchlist_data["Change %"].append(f"{change_pct:.2f}%")
                                watchlist_data["Volume"].append(volume_str)
                        except Exception as e:
                            # Just skip this stock if there's an error
                            continue
                    
                    if watchlist_data["Symbol"]:
                        watchlist_df = pd.DataFrame(watchlist_data)
                        st.dataframe(watchlist_df, use_container_width=True)
                    else:
                        st.info("Could not retrieve data for stocks in watchlist.")
                else:
                    st.info("Your watchlist is empty. Add some stocks below.")
            except Exception as e:
                st.error(f"Error loading watchlist: {e}")
                st.info("Watchlist data unavailable. Please try again later.")
        else:
            st.info("No watchlist found.")
        
        # Add to watchlist form
        with st.form("add_to_watchlist"):
            st.subheader("Add to Watchlist")
            new_symbol = st.text_input("Enter Symbol")
            submitted = st.form_submit_button("Add")
            if submitted and new_symbol:
                try:
                    if 'watchlist_id' in st.session_state:
                        success = db.add_stock_to_watchlist(st.session_state.watchlist_id, new_symbol.upper())
                        if success:
                            st.success(f"Added {new_symbol.upper()} to watchlist!")
                        else:
                            st.warning(f"{new_symbol.upper()} is already in your watchlist.")
                        st.rerun()
                    else:
                        st.error("No watchlist found. Please contact support.")
                except Exception as e:
                    st.error(f"Error adding to watchlist: {e}")

def show_investment_portfolio():
    st.header("💼 Investment Portfolio")
    
    # Get portfolio data from the database
    portfolio_id = None
    try:
        portfolios = db.get_user_portfolios(st.session_state.user_id)
        if portfolios:
            portfolio_id = portfolios[0].id
        
        if portfolio_id:
            # Get portfolio items
            portfolio_items = db.get_portfolio_items(portfolio_id)
            
            # Prepare the portfolio data
            holdings_data = {
                "Symbol": [],
                "Quantity": [],
                "Avg. Purchase Price": [],
                "Current Price": [],
                "Current Value": [],
                "Gain/Loss": [],
                "Gain/Loss %": []
            }
            
            total_investment = 0
            current_value = 0
            
            # Get latest stock prices for each item in portfolio
            for item in portfolio_items:
                stock = item[0]  # Stock object
                quantity = item[1]  # Quantity
                avg_price = item[2]  # Average purchase price
                
                # Get current price from Yahoo Finance
                try:
                    ticker_data = yf.Ticker(stock.symbol)
                    current_price = ticker_data.history(period='1d')['Close'].iloc[-1]
                except:
                    current_price = avg_price  # Fallback if can't get current price
                
                # Calculate values
                invested = quantity * avg_price
                current_item_value = quantity * current_price
                gain_loss = current_item_value - invested
                gain_loss_percent = (gain_loss / invested) * 100 if invested > 0 else 0
                
                # Add to totals
                total_investment += invested
                current_value += current_item_value
                
                # Add to dataframe
                holdings_data["Symbol"].append(stock.symbol)
                holdings_data["Quantity"].append(quantity)
                holdings_data["Avg. Purchase Price"].append(f"${avg_price:.2f}")
                holdings_data["Current Price"].append(f"${current_price:.2f}")
                holdings_data["Current Value"].append(f"${current_item_value:.2f}")
                holdings_data["Gain/Loss"].append(f"${gain_loss:.2f}")
                holdings_data["Gain/Loss %"].append(f"{gain_loss_percent:.2f}%")
            
            # Calculate overall portfolio metrics
            if total_investment > 0:
                total_gain = current_value - total_investment
                gain_percent = (total_gain / total_investment) * 100
            else:
                total_gain = 0
                gain_percent = 0
            
            # Portfolio summary
            st.subheader("Portfolio Summary")
            
            # Asset allocation - get data from portfolio
            stocks_df = pd.DataFrame(holdings_data)
            
            # Create asset allocation chart
            if len(holdings_data["Symbol"]) > 0:
                # Extract numeric values from formatted strings
                values = [float(val.replace("$", "")) for val in holdings_data["Current Value"]]
                
                fig = go.Figure(data=[go.Pie(
                    labels=holdings_data["Symbol"],
                    values=values,
                    hole=.3,
                    marker_colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']
                )])
                
                fig.update_layout(
                    title="Portfolio Allocation",
                    height=400,
                    margin=dict(l=50, r=50, t=50, b=50)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No stocks in portfolio. Add stocks to see allocation chart.")
            
            # Portfolio holdings table
            st.subheader("Portfolio Holdings")
            
            if len(holdings_data["Symbol"]) > 0:
                holdings_df = pd.DataFrame(holdings_data)
                st.dataframe(holdings_df, use_container_width=True)
                
                # Summary metrics
                metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                
                with metrics_col1:
                    st.metric("Total Investment", f"${total_investment:.2f}")
                
                with metrics_col2:
                    st.metric("Current Value", f"${current_value:.2f}")
                
                with metrics_col3:
                    st.metric("Total Gain/Loss", f"${total_gain:.2f}", delta=f"${total_gain:.2f}")
                
                with metrics_col4:
                    st.metric("Return %", f"{gain_percent:.2f}%", delta=f"{gain_percent:.2f}%")
            else:
                st.info("No stocks in portfolio yet.")
            
            # Add new transaction section
            st.subheader("Add Transaction")
            
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                new_symbol = st.text_input("Symbol", key="new_transaction_symbol")
            
            with col2:
                transaction_type = st.selectbox("Type", ["Buy", "Sell"], key="transaction_type")
            
            with col3:
                quantity = st.number_input("Quantity", min_value=0.01, step=0.01, key="transaction_quantity")
            
            with col4:
                price = st.number_input("Price ($)", min_value=0.01, step=0.01, key="transaction_price")
            
            if st.button("Add Transaction"):
                if new_symbol and quantity > 0 and price > 0:
                    try:
                        # Add transaction to database
                        db.add_stock_transaction(
                            st.session_state.user_id,
                            new_symbol,
                            transaction_type,
                            quantity,
                            price
                        )
                        st.success(f"{transaction_type} transaction for {quantity} shares of {new_symbol} at ${price:.2f} added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding transaction: {e}")
                else:
                    st.error("Please fill all fields with valid values.")
                    
            # Recent transactions
            st.subheader("Recent Transactions")
            try:
                transactions = db.get_user_transactions(st.session_state.user_id)
                
                if transactions:
                    transactions_data = {
                        "Date": [],
                        "Symbol": [],
                        "Type": [],
                        "Quantity": [],
                        "Price": [],
                        "Total": []
                    }
                    
                    for transaction, symbol in transactions:
                        transactions_data["Date"].append(transaction.date.strftime("%Y-%m-%d %H:%M"))
                        transactions_data["Symbol"].append(symbol)
                        transactions_data["Type"].append(transaction.transaction_type)
                        transactions_data["Quantity"].append(transaction.quantity)
                        transactions_data["Price"].append(f"${transaction.price:.2f}")
                        transactions_data["Total"].append(f"${transaction.quantity * transaction.price:.2f}")
                    
                    transactions_df = pd.DataFrame(transactions_data)
                    st.dataframe(transactions_df, use_container_width=True)
                else:
                    st.info("No recent transactions.")
            except Exception as e:
                st.error(f"Error loading transactions: {e}")
                st.info("Transaction data unavailable. Please try again later.")
        else:
            st.error("No portfolio found. Please contact support.")
    except Exception as e:
        st.error(f"Error loading portfolio: {e}")
        st.info("Portfolio data unavailable. Please try again later.")

def show_telegram_alerts():
    st.header("📱 Telegram Alerts")
    
    # Alert configuration
    st.subheader("Configure Alerts")
    
    # Price alerts
    with st.expander("Price Alerts", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            alert_symbol = st.text_input("Symbol", "AAPL")
        
        with col2:
            alert_type = st.selectbox("Alert Type", ["Above", "Below", "% Change"])
        
        with col3:
            alert_value = st.number_input("Price/Percentage", value=150.00)
        
        if st.button("Create Price Alert"):
            if alert_symbol and alert_value > 0:
                try:
                    # Add alert to database
                    db.add_alert(st.session_state.user_id, alert_symbol.upper(), f"Price {alert_type}", alert_value)
                    st.success(f"Price alert created for {alert_symbol.upper()}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating alert: {e}")
            else:
                st.error("Please enter a valid symbol and value.")
    
    # Market news alerts
    with st.expander("News Alerts"):
        news_keywords = st.text_input("Keywords (comma separated)", "earnings, merger, acquisition")
        news_symbols = st.text_input("Symbols to track (comma separated)", "AAPL, MSFT, GOOG")
        
        if st.button("Create News Alert"):
            if news_symbols:
                try:
                    # For news alerts, we'll store the keywords in the value field as JSON
                    symbols = [s.strip().upper() for s in news_symbols.split(",")]
                    for symbol in symbols:
                        if symbol:
                            db.add_alert(st.session_state.user_id, symbol, "News", 0)
                    
                    st.success("News alerts created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating news alert: {e}")
            else:
                st.error("Please enter at least one symbol.")
    
    # Earnings alerts
    with st.expander("Earnings Alerts"):
        earnings_symbols = st.text_input("Companies (comma separated)", "AAPL, AMZN, META, NFLX, GOOG")
        notify_days_before = st.slider("Notify days before", 1, 7, 3)
        
        if st.button("Create Earnings Alert"):
            if earnings_symbols:
                try:
                    symbols = [s.strip().upper() for s in earnings_symbols.split(",")]
                    for symbol in symbols:
                        if symbol:
                            db.add_alert(st.session_state.user_id, symbol, "Earnings", notify_days_before)
                    
                    st.success("Earnings alerts created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating earnings alert: {e}")
            else:
                st.error("Please enter at least one symbol.")
    
    # Active alerts list
    st.subheader("Active Alerts")
    
    # Get alerts from database
    try:
        alerts = db.get_user_alerts(st.session_state.user_id)
        
        if alerts:
            active_alerts_data = {
                "Type": [],
                "Symbol": [],
                "Value": [],
                "Created": []
            }
            
            for alert, symbol in alerts:
                alert_type = alert.alert_type
                value_display = ""
                
                if "Price Above" in alert_type:
                    value_display = f"${alert.value:.2f}"
                elif "Price Below" in alert_type:
                    value_display = f"${alert.value:.2f}"
                elif "% Change" in alert_type:
                    value_display = f"{alert.value:.2f}%"
                elif "Earnings" in alert_type:
                    value_display = f"Notify {int(alert.value)} days before"
                elif "News" in alert_type:
                    value_display = "News alerts"
                
                active_alerts_data["Type"].append(alert_type)
                active_alerts_data["Symbol"].append(symbol)
                active_alerts_data["Value"].append(value_display)
                active_alerts_data["Created"].append(alert.created_at.strftime("%Y-%m-%d"))
            
            alerts_df = pd.DataFrame(active_alerts_data)
            st.dataframe(alerts_df, use_container_width=True)
        else:
            st.info("No active alerts. Create some using the options above.")
    except Exception as e:
        st.error(f"Error loading alerts: {e}")
        st.info("Alert data unavailable. Please try again later.")
    
    # Recent notifications section
    st.subheader("Recent Notifications")
    
    # This would typically be populated from a notification history table
    # For now, we'll show a placeholder for the concept
    notifications = [
        {"Time": "2025-05-16 08:45", "Alert": "AAPL dropped below $175.00", "Status": "Sent to Telegram"},
        {"Time": "2025-05-15 14:30", "Alert": "TSLA earnings report expected on May 18", "Status": "Sent to Telegram"},
        {"Time": "2025-05-14 10:15", "Alert": "News: Microsoft announces new AI partnership", "Status": "Sent to Telegram"},
        {"Time": "2025-05-13 15:20", "Alert": "NFLX gained 5.2% today", "Status": "Sent to Telegram"}
    ]
    
    # In a full implementation, notifications would be tracked in the database
    notifications_df = pd.DataFrame(notifications)
    st.dataframe(notifications_df, use_container_width=True)
    
    # Settings for how to receive notifications
    st.subheader("Notification Settings")
    st.info("To receive alerts via Telegram, you would need to connect your Telegram account. This feature is currently in development.")
    
    col1, col2 = st.columns(2)
    with col1:
        telegram_connected = st.checkbox("Enable Telegram Notifications", value=True)
    with col2:
        email_notifications = st.checkbox("Enable Email Notifications", value=False)
        
    if st.button("Save Notification Settings"):
        st.success("Notification settings saved successfully!")

# Function to show India Market (NSE) data
def show_india_market():
    st.header("🇮🇳 India Market Dashboard (NSE)")
    
    try:
        # Initialize NSE
        nse = Nse()
        
        # Show NSE Indices
        st.subheader("NSE Market Indices")
        
        # Get NIFTY data
        nifty_data = nse.get_index_quote("nifty 50")
        nifty_bank_data = nse.get_index_quote("nifty bank")
        nifty_it_data = nse.get_index_quote("nifty it")
        
        # Display indices in metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if nifty_data:
                change_pct = nifty_data.get('pChange', 0)
                st.metric(
                    "NIFTY 50", 
                    f"₹{nifty_data.get('lastPrice', 0):,.2f}", 
                    delta=f"{change_pct}%"
                )
            else:
                st.metric("NIFTY 50", "N/A")
                
        with col2:
            if nifty_bank_data:
                change_pct = nifty_bank_data.get('pChange', 0)
                st.metric(
                    "NIFTY BANK", 
                    f"₹{nifty_bank_data.get('lastPrice', 0):,.2f}", 
                    delta=f"{change_pct}%"
                )
            else:
                st.metric("NIFTY BANK", "N/A")
                
        with col3:
            if nifty_it_data:
                change_pct = nifty_it_data.get('pChange', 0)
                st.metric(
                    "NIFTY IT", 
                    f"₹{nifty_it_data.get('lastPrice', 0):,.2f}", 
                    delta=f"{change_pct}%"
                )
            else:
                st.metric("NIFTY IT", "N/A")
        
        # Market Status
        st.subheader("Market Status")
        market_status = nse.get_market_status()
        if market_status:
            st.info(f"Current NSE Market Status: {market_status}")
        else:
            st.info("Market status information not available")
        
        # Top gainers and losers
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Gainers")
            try:
                top_gainers = nse.get_top_gainers()
                if top_gainers:
                    gainers_df = pd.DataFrame(top_gainers)
                    st.dataframe(gainers_df[['symbol', 'ltp', 'netPrice', 'pChange']], use_container_width=True)
                else:
                    st.info("Top gainers data not available")
            except Exception as e:
                st.error(f"Error fetching top gainers: {e}")
                
        with col2:
            st.subheader("Top Losers")
            try:
                top_losers = nse.get_top_losers()
                if top_losers:
                    losers_df = pd.DataFrame(top_losers)
                    st.dataframe(losers_df[['symbol', 'ltp', 'netPrice', 'pChange']], use_container_width=True)
                else:
                    st.info("Top losers data not available")
            except Exception as e:
                st.error(f"Error fetching top losers: {e}")
        
        # Stock lookup
        st.subheader("NSE Stock Lookup")
        nse_symbol = st.text_input("Enter NSE Symbol (e.g., TATASTEEL, RELIANCE)", "TATASTEEL")
        
        if st.button("Get Stock Info"):
            try:
                stock_info = nse.get_quote(nse_symbol)
                if stock_info:
                    # Create columns for basic info
                    info_col1, info_col2 = st.columns(2)
                    
                    with info_col1:
                        st.write(f"**Company:** {stock_info.get('companyName', 'N/A')}")
                        st.write(f"**Series:** {stock_info.get('series', 'N/A')}")
                        st.write(f"**ISIN:** {stock_info.get('isinCode', 'N/A')}")
                        st.write(f"**Sector:** {stock_info.get('industryInfo', 'N/A')}")
                    
                    with info_col2:
                        st.write(f"**Last Price:** ₹{stock_info.get('lastPrice', 'N/A')}")
                        st.write(f"**Change:** ₹{stock_info.get('change', 'N/A')} ({stock_info.get('pChange', 'N/A')}%)")
                        st.write(f"**52 Week High:** ₹{stock_info.get('high52', 'N/A')}")
                        st.write(f"**52 Week Low:** ₹{stock_info.get('low52', 'N/A')}")
                    
                    # Create price and volume metrics
                    price_col1, price_col2, price_col3, price_col4 = st.columns(4)
                    
                    with price_col1:
                        st.metric("Open", f"₹{stock_info.get('open', 'N/A')}")
                        
                    with price_col2:
                        st.metric("High", f"₹{stock_info.get('dayHigh', 'N/A')}")
                        
                    with price_col3:
                        st.metric("Low", f"₹{stock_info.get('dayLow', 'N/A')}")
                        
                    with price_col4:
                        st.metric("Close", f"₹{stock_info.get('previousClose', 'N/A')}")
                    
                    # Additional market data
                    st.subheader(f"{stock_info.get('companyName', 'Company')} Market Data")
                    
                    market_col1, market_col2, market_col3 = st.columns(3)
                    
                    with market_col1:
                        st.write(f"**Total Traded Volume:** {stock_info.get('totalTradedVolume', 'N/A'):,}")
                        st.write(f"**Delivery Percentage:** {stock_info.get('deliveryQuantity', 'N/A')}%")
                        
                    with market_col2:
                        st.write(f"**Market Cap:** ₹{stock_info.get('marketCapFullFloat', 'N/A'):,} Cr")
                        st.write(f"**EPS:** ₹{stock_info.get('eps', 'N/A')}")
                        
                    with market_col3:
                        st.write(f"**PE Ratio:** {stock_info.get('pe', 'N/A')}")
                        st.write(f"**Book Value:** ₹{stock_info.get('bookValue', 'N/A')}")
                    
                    # Get Yahoo Finance data for charts
                    chart_data, _ = get_stock_data(f"{nse_symbol}.NS", 90)
                    if chart_data is not None and not chart_data.empty:
                        st.subheader(f"{nse_symbol} Price Chart (3 Months)")
                        price_chart = create_stock_chart(chart_data, f"{nse_symbol}.NS", [20, 50])
                        st.plotly_chart(price_chart, use_container_width=True)
                        
                        volume_chart = create_volume_chart(chart_data, f"{nse_symbol}.NS")
                        st.plotly_chart(volume_chart, use_container_width=True)
                    else:
                        st.warning("Could not load chart data for this stock.")
                else:
                    st.error(f"No data found for symbol {nse_symbol} on NSE")
            except Exception as e:
                st.error(f"Error looking up NSE stock: {e}")
                st.info("Try using the correct symbol code (e.g., TATASTEEL instead of TATA STEEL)")
        
        # Advanced Options
        with st.expander("Advanced NSE Options"):
            st.write("Search for stocks by name or classification:")
            search_text = st.text_input("Search Term", "")
            if st.button("Search NSE Stocks"):
                if search_text:
                    try:
                        # Search all stocks
                        all_stock_codes = nse.get_stock_codes()
                        
                        # Filter based on search text
                        filtered_stocks = {k: v for k, v in all_stock_codes.items() 
                                          if search_text.lower() in v.lower() or search_text.lower() in k.lower()}
                        
                        if filtered_stocks:
                            st.write(f"Found {len(filtered_stocks)} matches:")
                            st.json(filtered_stocks)
                        else:
                            st.info(f"No stocks found matching '{search_text}'")
                    except Exception as e:
                        st.error(f"Error searching NSE stocks: {e}")
                else:
                    st.warning("Please enter a search term")
                    
    except Exception as e:
        st.error(f"Error connecting to NSE: {e}")
        st.warning("The NSE API may be temporarily unavailable. Please try again later.")
        st.info("Alternatively, you can still use Yahoo Finance data for Indian stocks by adding .NS to stock symbols (e.g., TATASTEEL.NS)")

# Function to show Personal Portfolio Tracker
def show_my_portfolio_tracker():
    st.header("📊 My Personal Portfolio Tracker")
    st.write("Track your personal stock investments and monitor their performance over time")
    
    # Initialize portfolio state in session if not exists
    if 'my_portfolio' not in st.session_state:
        st.session_state.my_portfolio = []
    
    # Create tabs for different portfolio sections
    portfolio_tabs = st.tabs(["Portfolio Overview", "Add/Update Stock", "Trade History", "Performance Analytics"])
    
    with portfolio_tabs[0]:  # Portfolio Overview
        st.subheader("My Stock Portfolio")
        
        if not st.session_state.my_portfolio:
            st.info("Your portfolio is empty. Add stocks using the 'Add/Update Stock' tab.")
        else:
            # Create a dataframe for the portfolio
            portfolio_data = []
            total_investment = 0
            total_current_value = 0
            
            for stock in st.session_state.my_portfolio:
                symbol = stock['symbol']
                quantity = stock['quantity']
                buy_price = stock['buy_price']
                buy_date = stock['buy_date']
                notes = stock['notes']
                
                # Get current price data
                try:
                    # Handle Indian stocks by appending .NS if needed
                    if stock.get('exchange') == 'NSE' and not symbol.endswith('.NS'):
                        data_symbol = f"{symbol}.NS"
                    else:
                        data_symbol = symbol
                        
                    # Get current data
                    current_data = yf.Ticker(data_symbol).history(period="1d")
                    if not current_data.empty:
                        current_price = float(current_data['Close'].iloc[-1])
                    else:
                        current_price = buy_price  # Fallback to buy price if can't get current
                except Exception as e:
                    st.warning(f"Couldn't fetch current price for {symbol}: {e}")
                    current_price = buy_price  # Fallback
                
                # Calculate values
                investment = quantity * buy_price
                current_value = quantity * current_price
                profit_loss = current_value - investment
                profit_loss_pct = (profit_loss / investment) * 100 if investment > 0 else 0
                
                # Add to totals
                total_investment += investment
                total_current_value += current_value
                
                # Add to portfolio data
                portfolio_data.append({
                    "Symbol": symbol,
                    "Exchange": stock.get('exchange', 'Unknown'),
                    "Quantity": quantity,
                    "Buy Price": f"${buy_price:.2f}" if stock.get('exchange') != 'NSE' else f"₹{buy_price:.2f}",
                    "Current Price": f"${current_price:.2f}" if stock.get('exchange') != 'NSE' else f"₹{current_price:.2f}",
                    "Investment": f"${investment:.2f}" if stock.get('exchange') != 'NSE' else f"₹{investment:.2f}",
                    "Current Value": f"${current_value:.2f}" if stock.get('exchange') != 'NSE' else f"₹{current_value:.2f}",
                    "Profit/Loss": f"${profit_loss:.2f}" if stock.get('exchange') != 'NSE' else f"₹{profit_loss:.2f}",
                    "P/L %": f"{profit_loss_pct:.2f}%",
                    "Buy Date": buy_date,
                    "Days Held": (datetime.today() - datetime.strptime(buy_date, "%Y-%m-%d")).days,
                    "Notes": notes
                })
            
            # Calculate overall portfolio performance 
            total_profit_loss = total_current_value - total_investment
            total_profit_loss_pct = (total_profit_loss / total_investment) * 100 if total_investment > 0 else 0
            
            # Display summary metrics
            st.subheader("Portfolio Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Investment", f"${total_investment:.2f}")
            
            with col2:
                st.metric("Current Value", f"${total_current_value:.2f}")
            
            with col3:
                st.metric("Total Profit/Loss", f"${total_profit_loss:.2f}", 
                         delta=f"{total_profit_loss:.2f}")
            
            with col4:
                st.metric("Overall Return", f"{total_profit_loss_pct:.2f}%", 
                         delta=f"{total_profit_loss_pct:.2f}%")
            
            # Display portfolio table
            st.subheader("Holdings")
            portfolio_df = pd.DataFrame(portfolio_data)
            
            # Apply conditional formatting (green for profit, red for loss)
            def highlight_profit_loss(val):
                if isinstance(val, str) and val.startswith('$'):
                    if '-' in val:
                        return 'color: red'
                    else:
                        return 'color: green'
                elif isinstance(val, str) and '%' in val:
                    if '-' in val:
                        return 'color: red'
                    else:
                        return 'color: green'
                return ''
            
            # Display styled dataframe
            st.dataframe(portfolio_df.style.applymap(highlight_profit_loss, subset=['Profit/Loss', 'P/L %']), 
                        use_container_width=True)
            
            # Create a pie chart of portfolio allocation
            st.subheader("Portfolio Allocation")
            
            # Extract currency and numeric value from strings like "$123.45" or "₹123.45"
            def extract_numeric_value(value_str):
                if isinstance(value_str, str):
                    return float(value_str.replace('$', '').replace('₹', ''))
                return 0
            
            # Create values and labels lists for pie chart
            values = [extract_numeric_value(stock['Current Value']) for stock in portfolio_data]
            labels = [stock['Symbol'] for stock in portfolio_data]
            
            # Create pie chart
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.3,
                marker_colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']
            )])
            
            fig.update_layout(
                title="Portfolio Allocation by Current Value",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display performance visualization
            if len(portfolio_data) > 0:
                # Sort stocks by performance
                sorted_data = sorted(portfolio_data, key=lambda x: float(x['P/L %'].replace('%', '')), reverse=True)
                
                # Create bar chart of performance
                performance_fig = go.Figure()
                
                # Add bars for each stock
                performance_fig.add_trace(go.Bar(
                    x=[stock['Symbol'] for stock in sorted_data],
                    y=[float(stock['P/L %'].replace('%', '')) for stock in sorted_data],
                    marker_color=['green' if float(stock['P/L %'].replace('%', '')) >= 0 else 'red' for stock in sorted_data]
                ))
                
                performance_fig.update_layout(
                    title="Stock Performance (% Return)",
                    xaxis_title="Stock Symbol",
                    yaxis_title="Return (%)",
                    height=400
                )
                
                st.plotly_chart(performance_fig, use_container_width=True)
                
                # Option to download portfolio data as CSV
                csv = portfolio_df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="my_portfolio.csv">Download Portfolio Data as CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
    
    with portfolio_tabs[1]:  # Add/Update Stock
        st.subheader("Add or Update Stock in Portfolio")
        
        # Form for adding new stock
        with st.form("add_stock_form"):
            # Create two columns for layout
            form_col1, form_col2 = st.columns(2)
            
            with form_col1:
                symbol = st.text_input("Stock Symbol (e.g., AAPL, TATASTEEL)", "")
                exchange = st.selectbox("Exchange", ["US", "NSE", "Other"])
                quantity = st.number_input("Quantity", min_value=0.01, step=0.01, value=1.0)
                buy_price = st.number_input("Purchase Price", min_value=0.01, step=0.01, value=100.0)
            
            with form_col2:
                buy_date = st.date_input("Purchase Date", datetime.today()).strftime("%Y-%m-%d")
                notes = st.text_area("Notes (Optional)", "", height=100)
                
                # Option to automatically fetch current price
                fetch_price = st.checkbox("Fetch current price automatically", value=True)
            
            # Submit button
            submitted = st.form_submit_button("Add to Portfolio")
            
            if submitted:
                if symbol and quantity > 0 and buy_price > 0:
                    # Check if stock already exists in portfolio
                    stock_exists = False
                    for i, stock in enumerate(st.session_state.my_portfolio):
                        if stock['symbol'].upper() == symbol.upper():
                            # Update existing stock
                            st.session_state.my_portfolio[i] = {
                                'symbol': symbol.upper(),
                                'exchange': exchange,
                                'quantity': quantity,
                                'buy_price': buy_price,
                                'buy_date': buy_date,
                                'notes': notes
                            }
                            stock_exists = True
                            st.success(f"Updated {symbol.upper()} in your portfolio!")
                            break
                    
                    if not stock_exists:
                        # Add new stock
                        st.session_state.my_portfolio.append({
                            'symbol': symbol.upper(),
                            'exchange': exchange,
                            'quantity': quantity,
                            'buy_price': buy_price,
                            'buy_date': buy_date,
                            'notes': notes
                        })
                        st.success(f"Added {symbol.upper()} to your portfolio!")
                else:
                    st.error("Please fill all required fields with valid values.")
        
        # Remove stock section
        st.subheader("Remove Stock from Portfolio")
        
        if not st.session_state.my_portfolio:
            st.info("Your portfolio is empty. Nothing to remove.")
        else:
            # Get list of stock symbols in portfolio
            stock_symbols = [stock['symbol'] for stock in st.session_state.my_portfolio]
            
            # Create remove form
            with st.form("remove_stock_form"):
                stock_to_remove = st.selectbox("Select Stock to Remove", stock_symbols)
                remove_submitted = st.form_submit_button("Remove Stock")
                
                if remove_submitted and stock_to_remove:
                    # Remove the selected stock
                    st.session_state.my_portfolio = [stock for stock in st.session_state.my_portfolio 
                                                   if stock['symbol'] != stock_to_remove]
                    st.success(f"Removed {stock_to_remove} from your portfolio!")
    
    with portfolio_tabs[2]:  # Trade History
        st.subheader("Trade History")
        
        # Initialize trade history if not exists
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = []
            
        # Add new trade history record
        with st.form("add_trade_history"):
            st.write("Record a new trade:")
            
            history_col1, history_col2 = st.columns(2)
            
            with history_col1:
                h_symbol = st.text_input("Stock Symbol", "")
                h_trade_type = st.selectbox("Trade Type", ["Buy", "Sell"])
                h_quantity = st.number_input("Quantity", min_value=0.01, step=0.01, value=1.0)
                
            with history_col2:
                h_price = st.number_input("Price per Share", min_value=0.01, step=0.01, value=100.0)
                h_date = st.date_input("Trade Date", datetime.today()).strftime("%Y-%m-%d")
                h_notes = st.text_input("Notes", "")
                
            history_submitted = st.form_submit_button("Add to History")
            
            if history_submitted:
                if h_symbol and h_quantity > 0 and h_price > 0:
                    # Calculate trade value
                    trade_value = h_quantity * h_price
                    
                    # Add to history
                    st.session_state.trade_history.append({
                        'symbol': h_symbol.upper(),
                        'trade_type': h_trade_type,
                        'quantity': h_quantity,
                        'price': h_price,
                        'value': trade_value,
                        'date': h_date,
                        'notes': h_notes
                    })
                    
                    st.success(f"Added {h_trade_type} trade for {h_symbol} to history!")
                    
                    # Update main portfolio if it's a buy trade
                    if h_trade_type == "Buy":
                        # Check if stock already exists
                        stock_exists = False
                        for i, stock in enumerate(st.session_state.my_portfolio):
                            if stock['symbol'].upper() == h_symbol.upper():
                                # Update existing stock
                                new_quantity = stock['quantity'] + h_quantity
                                # Calculate new average purchase price
                                total_value = (stock['quantity'] * stock['buy_price']) + (h_quantity * h_price)
                                new_avg_price = total_value / new_quantity
                                
                                st.session_state.my_portfolio[i]['quantity'] = new_quantity
                                st.session_state.my_portfolio[i]['buy_price'] = new_avg_price
                                st.info(f"Updated {h_symbol} quantity and average purchase price in your portfolio.")
                                stock_exists = True
                                break
                        
                        if not stock_exists:
                            # Add new stock to portfolio
                            st.session_state.my_portfolio.append({
                                'symbol': h_symbol.upper(),
                                'exchange': "US",  # Default to US exchange
                                'quantity': h_quantity,
                                'buy_price': h_price,
                                'buy_date': h_date,
                                'notes': h_notes
                            })
                            st.info(f"Added {h_symbol} to your portfolio based on this trade.")
                    
                    # Update portfolio for sell trade
                    elif h_trade_type == "Sell":
                        for i, stock in enumerate(st.session_state.my_portfolio):
                            if stock['symbol'].upper() == h_symbol.upper():
                                # Reduce quantity
                                new_quantity = stock['quantity'] - h_quantity
                                
                                if new_quantity <= 0:
                                    # Remove stock from portfolio if quantity zero or negative
                                    st.session_state.my_portfolio.pop(i)
                                    st.info(f"Removed {h_symbol} from portfolio as all shares were sold.")
                                else:
                                    # Update quantity
                                    st.session_state.my_portfolio[i]['quantity'] = new_quantity
                                    st.info(f"Updated {h_symbol} quantity in your portfolio.")
                                break
                else:
                    st.error("Please fill all required fields with valid values.")
                
        # Display trade history
        if not st.session_state.trade_history:
            st.info("No trade history yet. Record your trades above.")
        else:
            st.subheader("Your Trade History")
            
            # Create dataframe from trade history
            history_data = []
            
            for trade in st.session_state.trade_history:
                history_data.append({
                    "Date": trade['date'],
                    "Symbol": trade['symbol'],
                    "Type": trade['trade_type'],
                    "Quantity": trade['quantity'],
                    "Price": f"${trade['price']:.2f}",
                    "Total Value": f"${trade['value']:.2f}",
                    "Notes": trade['notes']
                })
            
            # Display table
            history_df = pd.DataFrame(history_data)
            st.dataframe(history_df, use_container_width=True)
            
            # Option to download history as CSV
            csv = history_df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="trade_history.csv">Download Trade History as CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    with portfolio_tabs[3]:  # Performance Analytics
        st.subheader("Portfolio Performance Analytics")
        
        if not st.session_state.my_portfolio:
            st.info("Your portfolio is empty. Add stocks to see performance analytics.")
        else:
            # Date range selection
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", datetime.today() - timedelta(days=365))
            with col2:
                end_date = st.date_input("End Date", datetime.today())
                
            if start_date >= end_date:
                st.error("Start date must be before end date")
            else:
                # Fetch historical data for each stock
                st.info("Fetching historical performance data...")
                
                # Create a dataframe to store portfolio value over time
                date_range = pd.date_range(start=start_date, end=end_date, freq='D')
                portfolio_values = pd.DataFrame(index=date_range)
                portfolio_values['Total Value'] = 0
                
                # Create a figure for individual stock performance
                stock_fig = go.Figure()
                
                # Process each stock
                for stock in st.session_state.my_portfolio:
                    symbol = stock['symbol']
                    quantity = stock['quantity']
                    
                    # Handle Indian stocks
                    if stock.get('exchange') == 'NSE' and not symbol.endswith('.NS'):
                        data_symbol = f"{symbol}.NS"
                    else:
                        data_symbol = symbol
                    
                    # Fetch historical data
                    try:
                        hist_data = yf.download(data_symbol, start=start_date, end=end_date)
                        
                        if not hist_data.empty:
                            # Calculate daily values for this stock
                            stock_values = hist_data['Close'] * quantity
                            
                            # Add to portfolio total
                            portfolio_values[symbol] = stock_values
                            portfolio_values['Total Value'] += stock_values.fillna(0)
                            
                            # Add stock to performance chart
                            stock_fig.add_trace(go.Scatter(
                                x=hist_data.index,
                                y=hist_data['Close'] / hist_data['Close'].iloc[0] * 100 - 100,  # Normalize to % change
                                name=symbol,
                                mode='lines'
                            ))
                        else:
                            st.warning(f"No historical data available for {symbol}")
                    except Exception as e:
                        st.error(f"Error fetching data for {symbol}: {e}")
                
                # Add benchmark comparison (S&P 500)
                try:
                    benchmark = yf.download('^GSPC', start=start_date, end=end_date)
                    if not benchmark.empty:
                        benchmark_norm = benchmark['Close'] / benchmark['Close'].iloc[0] * 100 - 100
                        stock_fig.add_trace(go.Scatter(
                            x=benchmark.index,
                            y=benchmark_norm,
                            name='S&P 500',
                            mode='lines',
                            line=dict(dash='dash', color='black')
                        ))
                except:
                    pass
                
                # Configure stock performance chart
                stock_fig.update_layout(
                    title="Individual Stock Performance (% Change)",
                    xaxis_title="Date",
                    yaxis_title="% Change",
                    height=500,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                # Create portfolio value chart
                portfolio_fig = go.Figure()
                
                portfolio_fig.add_trace(go.Scatter(
                    x=portfolio_values.index,
                    y=portfolio_values['Total Value'],
                    name='Portfolio Value',
                    fill='tozeroy',
                    line=dict(color='green')
                ))
                
                portfolio_fig.update_layout(
                    title="Total Portfolio Value Over Time",
                    xaxis_title="Date",
                    yaxis_title="Value ($)",
                    height=400
                )
                
                # Calculate key metrics
                if not portfolio_values['Total Value'].empty:
                    initial_value = portfolio_values['Total Value'].iloc[0]
                    final_value = portfolio_values['Total Value'].iloc[-1]
                    
                    # Overall return
                    total_return = ((final_value / initial_value) - 1) * 100
                    
                    # Calculate daily returns
                    daily_returns = portfolio_values['Total Value'].pct_change().dropna()
                    
                    # Annualized return 
                    days = (end_date - start_date).days
                    if days > 0:
                        annual_return = ((final_value / initial_value) ** (365 / days) - 1) * 100
                    else:
                        annual_return = 0
                        
                    # Volatility (annualized)
                    volatility = daily_returns.std() * (252 ** 0.5) * 100
                    
                    # Sharpe ratio (assuming risk-free rate of 1%)
                    risk_free_rate = 0.01
                    sharpe = (annual_return/100 - risk_free_rate) / (volatility/100) if volatility > 0 else 0
                    
                    # Display metrics
                    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                    
                    with metrics_col1:
                        st.metric("Total Return", f"{total_return:.2f}%")
                    
                    with metrics_col2:
                        st.metric("Annual Return", f"{annual_return:.2f}%")
                    
                    with metrics_col3:
                        st.metric("Volatility", f"{volatility:.2f}%")
                    
                    with metrics_col4:
                        st.metric("Sharpe Ratio", f"{sharpe:.2f}")
                    
                    # Show charts
                    st.plotly_chart(portfolio_fig, use_container_width=True)
                    st.plotly_chart(stock_fig, use_container_width=True)
                    
                    # Return distribution
                    st.subheader("Return Distribution")
                    
                    # Create histogram of daily returns
                    return_fig = go.Figure()
                    
                    return_fig.add_trace(go.Histogram(
                        x=daily_returns * 100,
                        name='Daily Returns',
                        nbinsx=30,
                        marker_color='blue'
                    ))
                    
                    return_fig.update_layout(
                        title="Distribution of Daily Returns",
                        xaxis_title="Daily Return (%)",
                        yaxis_title="Frequency",
                        height=400
                    )
                    
                    st.plotly_chart(return_fig, use_container_width=True)
                    
                    # Correlation matrix
                    if len(st.session_state.my_portfolio) > 1:
                        st.subheader("Stock Correlation Matrix")
                        
                        # Calculate daily returns for each stock
                        stock_returns = portfolio_values.drop('Total Value', axis=1).pct_change().dropna()
                        
                        # Calculate correlation matrix
                        corr_matrix = stock_returns.corr()
                        
                        # Create heatmap
                        corr_fig = go.Figure(data=go.Heatmap(
                            z=corr_matrix.values,
                            x=corr_matrix.columns,
                            y=corr_matrix.columns,
                            colorscale='RdBu_r',
                            zmin=-1, zmax=1
                        ))
                        
                        corr_fig.update_layout(
                            title="Stock Correlation Matrix",
                            height=500
                        )
                        
                        st.plotly_chart(corr_fig, use_container_width=True)
                else:
                    st.warning("Not enough data to calculate performance metrics")

# Function to show TradingView charts
def show_tradingview_charts():
    st.header("📈 TradingView Advanced Charts")
    st.write("Access professional TradingView charts with technical analysis tools")
    
    # Initialize settings if not exists
    if 'tradingview_symbol' not in st.session_state:
        st.session_state.tradingview_symbol = "NASDAQ:AAPL"
    if 'tradingview_interval' not in st.session_state:
        st.session_state.tradingview_interval = "D"
    if 'tradingview_theme' not in st.session_state:
        st.session_state.tradingview_theme = "light"
    if 'tradingview_studies' not in st.session_state:
        st.session_state.tradingview_studies = []
    
    # Create tabs for different chart types
    chart_tabs = st.tabs(["Stock Chart", "Cryptocurrency", "Forex", "Futures", "Chart Settings"])
    
    with chart_tabs[0]:  # Stock Chart
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Stock symbol input
            symbol_input = st.text_input("Enter TradingView Stock Symbol", value=st.session_state.tradingview_symbol)
            if symbol_input != st.session_state.tradingview_symbol:
                st.session_state.tradingview_symbol = symbol_input
        
        with col2:
            # Timeframe selection
            interval_options = {
                "1 minute": "1",
                "5 minutes": "5",
                "15 minutes": "15",
                "30 minutes": "30",
                "1 hour": "60",
                "4 hours": "240",
                "1 day": "D",
                "1 week": "W",
                "1 month": "M"
            }
            interval = st.selectbox("Timeframe", list(interval_options.keys()), 
                                  index=list(interval_options.values()).index(st.session_state.tradingview_interval))
            st.session_state.tradingview_interval = interval_options[interval]
        
        with col3:
            # Theme selection
            theme = st.selectbox("Theme", ["Light", "Dark"], 
                               index=0 if st.session_state.tradingview_theme == "light" else 1)
            st.session_state.tradingview_theme = theme.lower()
        
        # Stock chart suggestions
        st.subheader("Popular Stocks")
        
        # Create columns for the buttons
        stock_col1, stock_col2, stock_col3, stock_col4, stock_col5 = st.columns(5)
        
        with stock_col1:
            if st.button("AAPL"):
                st.session_state.tradingview_symbol = "NASDAQ:AAPL"
                st.rerun()
            
            if st.button("TCS.NS"):
                st.session_state.tradingview_symbol = "NSE:TCS"
                st.rerun()
        
        with stock_col2:
            if st.button("MSFT"):
                st.session_state.tradingview_symbol = "NASDAQ:MSFT"
                st.rerun()
                
            if st.button("RELIANCE.NS"):
                st.session_state.tradingview_symbol = "NSE:RELIANCE"
                st.rerun()
                
        with stock_col3:
            if st.button("GOOG"):
                st.session_state.tradingview_symbol = "NASDAQ:GOOG"
                st.rerun()
                
            if st.button("INFY.NS"):
                st.session_state.tradingview_symbol = "NSE:INFY"
                st.rerun()
                
        with stock_col4:
            if st.button("AMZN"):
                st.session_state.tradingview_symbol = "NASDAQ:AMZN"
                st.rerun()
                
            if st.button("TATASTEEL.NS"):
                st.session_state.tradingview_symbol = "NSE:TATASTEEL"
                st.rerun()
                
        with stock_col5:
            if st.button("TSLA"):
                st.session_state.tradingview_symbol = "NASDAQ:TSLA"
                st.rerun()
                
            if st.button("TATAMOTORS.NS"):
                st.session_state.tradingview_symbol = "NSE:TATAMOTORS"
                st.rerun()
        
        # Display the TradingView widget
        st.subheader(f"TradingView Chart: {st.session_state.tradingview_symbol}")
        
        # Generate the TradingView Advanced Chart HTML
        tradingview_html = f"""
        <div class="tradingview-widget-container">
            <div id="tradingview_chart"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget(
            {{
                "autosize": true,
                "symbol": "{st.session_state.tradingview_symbol}",
                "interval": "{st.session_state.tradingview_interval}",
                "timezone": "exchange",
                "theme": "{st.session_state.tradingview_theme}",
                "style": "1",
                "locale": "en",
                "enable_publishing": false,
                "allow_symbol_change": true,
                "studies": {st.session_state.tradingview_studies},
                "container_id": "tradingview_chart",
                "withdateranges": true,
                "hide_side_toolbar": false,
                "details": true,
                "hotlist": true,
                "calendar": true,
                "save_image": true,
                "show_popup_button": true
            }});
            </script>
        </div>
        """
        
        # Set the height of the chart
        components.html(tradingview_html, height=600)
        
        # Additional Chart Information
        st.subheader("Chart Information")
        st.info("""
        - Use the toolbar at the top of the chart for drawing tools and indicators
        - Click on the gear icon to access chart settings
        - Use the timeframe selector to change the chart interval
        - Right-click on the chart for additional options
        - Search for any stock by changing the symbol in TradingView format (e.g., NASDAQ:AAPL, NSE:RELIANCE)
        """)
    
    with chart_tabs[1]:  # Cryptocurrency
        st.subheader("Cryptocurrency Charts")
        
        # Crypto symbol selection
        crypto_options = {
            "Bitcoin (BTC)": "BINANCE:BTCUSDT",
            "Ethereum (ETH)": "BINANCE:ETHUSDT",
            "Binance Coin (BNB)": "BINANCE:BNBUSDT",
            "Ripple (XRP)": "BINANCE:XRPUSDT",
            "Cardano (ADA)": "BINANCE:ADAUSDT",
            "Solana (SOL)": "BINANCE:SOLUSDT",
            "Dogecoin (DOGE)": "BINANCE:DOGEUSDT",
            "Polkadot (DOT)": "BINANCE:DOTUSDT",
            "Shiba Inu (SHIB)": "BINANCE:SHIBUSDT"
        }
        
        selected_crypto = st.selectbox("Select Cryptocurrency", list(crypto_options.keys()))
        crypto_symbol = crypto_options[selected_crypto]
        
        # Timeframe for crypto
        crypto_interval_options = {
            "1 minute": "1",
            "5 minutes": "5",
            "15 minutes": "15",
            "1 hour": "60",
            "4 hours": "240",
            "1 day": "D",
            "1 week": "W"
        }
        
        crypto_interval = st.selectbox("Select Timeframe", list(crypto_interval_options.keys()), key="crypto_interval")
        crypto_interval_value = crypto_interval_options[crypto_interval]
        
        # Generate TradingView widget for Crypto
        crypto_html = f"""
        <div class="tradingview-widget-container">
            <div id="tradingview_crypto"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget(
            {{
                "autosize": true,
                "symbol": "{crypto_symbol}",
                "interval": "{crypto_interval_value}",
                "timezone": "exchange",
                "theme": "{st.session_state.tradingview_theme}",
                "style": "1",
                "locale": "en",
                "enable_publishing": false,
                "hide_side_toolbar": false,
                "allow_symbol_change": true,
                "details": true,
                "studies": ["RSI", "MACD"],
                "container_id": "tradingview_crypto"
            }});
            </script>
        </div>
        """
        
        # Display crypto chart
        components.html(crypto_html, height=600)
        
        # Crypto market info
        st.subheader("Cryptocurrency Market Information")
        st.write(f"Viewing: {selected_crypto} ({crypto_symbol})")
        st.info("Cryptocurrency markets operate 24/7, unlike traditional stock markets. They're known for higher volatility and can be traded at any time.")
    
    with chart_tabs[2]:  # Forex
        st.subheader("Forex Trading Charts")
        
        # Forex pair selection
        forex_options = {
            "EUR/USD": "FX:EURUSD",
            "GBP/USD": "FX:GBPUSD",
            "USD/JPY": "FX:USDJPY",
            "USD/CHF": "FX:USDCHF",
            "AUD/USD": "FX:AUDUSD",
            "USD/CAD": "FX:USDCAD",
            "EUR/GBP": "FX:EURGBP",
            "EUR/JPY": "FX:EURJPY",
            "GBP/JPY": "FX:GBPJPY",
            "USD/INR": "FX:USDINR"
        }
        
        selected_forex = st.selectbox("Select Forex Pair", list(forex_options.keys()))
        forex_symbol = forex_options[selected_forex]
        
        # Generate TradingView widget for Forex
        forex_html = f"""
        <div class="tradingview-widget-container">
            <div id="tradingview_forex"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget(
            {{
                "autosize": true,
                "symbol": "{forex_symbol}",
                "interval": "D",
                "timezone": "exchange",
                "theme": "{st.session_state.tradingview_theme}",
                "style": "1",
                "locale": "en",
                "enable_publishing": false,
                "hide_side_toolbar": false,
                "allow_symbol_change": true,
                "details": true,
                "studies": ["RSI", "MACD"],
                "container_id": "tradingview_forex"
            }});
            </script>
        </div>
        """
        
        # Display forex chart
        components.html(forex_html, height=600)
        
        # Forex market info
        st.subheader("Forex Market Information")
        st.write(f"Viewing: {selected_forex} ({forex_symbol})")
        st.info("Forex markets operate 24 hours a day, 5 days a week. The major trading sessions are: Asian session, European session, and North American session.")
    
    with chart_tabs[3]:  # Futures
        st.subheader("Futures Markets")
        
        # Futures selection
        futures_options = {
            "E-mini S&P 500": "CME_MINI:ES1!",
            "E-mini NASDAQ": "CME_MINI:NQ1!",
            "Crude Oil": "NYMEX:CL1!",
            "Gold": "COMEX:GC1!",
            "Silver": "COMEX:SI1!",
            "Natural Gas": "NYMEX:NG1!",
            "Corn": "CBOT:ZC1!",
            "Wheat": "CBOT:ZW1!",
            "Cotton": "NYMEX:CT1!",
            "US 10-Year T-Note": "CBOT:ZN1!"
        }
        
        selected_futures = st.selectbox("Select Futures Contract", list(futures_options.keys()))
        futures_symbol = futures_options[selected_futures]
        
        # Generate TradingView widget for Futures
        futures_html = f"""
        <div class="tradingview-widget-container">
            <div id="tradingview_futures"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget(
            {{
                "autosize": true,
                "symbol": "{futures_symbol}",
                "interval": "D",
                "timezone": "exchange",
                "theme": "{st.session_state.tradingview_theme}",
                "style": "1",
                "locale": "en",
                "enable_publishing": false,
                "hide_side_toolbar": false,
                "allow_symbol_change": true,
                "details": true,
                "studies": ["Volume", "RSI"],
                "container_id": "tradingview_futures"
            }});
            </script>
        </div>
        """
        
        # Display futures chart
        components.html(futures_html, height=600)
        
        # Futures market info
        st.subheader("Futures Market Information")
        st.write(f"Viewing: {selected_futures} ({futures_symbol})")
        st.info("Futures contracts have expiration dates. The '1!' in the symbol indicates the front month (nearest expiration) contract. Trading hours vary by exchange and contract.")
    
    with chart_tabs[4]:  # Chart Settings
        st.subheader("Advanced Chart Settings")
        
        # Technical Indicators
        st.write("### Technical Indicators")
        st.write("Select technical indicators to add to your charts:")
        
        # Create columns for indicators
        ind_col1, ind_col2, ind_col3 = st.columns(3)
        
        indicators = []
        
        with ind_col1:
            if st.checkbox("Moving Average (MA)", value="MA" in st.session_state.tradingview_studies):
                indicators.append("MASimple@tv-basicstudies")
            if st.checkbox("Relative Strength Index (RSI)", value="RSI" in st.session_state.tradingview_studies):
                indicators.append("RSI@tv-basicstudies")
            if st.checkbox("Bollinger Bands", value="BBANDS" in st.session_state.tradingview_studies):
                indicators.append("BB@tv-basicstudies")
                
        with ind_col2:
            if st.checkbox("MACD", value="MACD" in st.session_state.tradingview_studies):
                indicators.append("MACD@tv-basicstudies")
            if st.checkbox("Stochastic Oscillator", value="STOCH" in st.session_state.tradingview_studies):
                indicators.append("Stochastic@tv-basicstudies")
            if st.checkbox("Average Directional Index (ADX)", value="ADX" in st.session_state.tradingview_studies):
                indicators.append("ADX@tv-basicstudies")
                
        with ind_col3:
            if st.checkbox("Ichimoku Cloud", value="ICHIMOKU" in st.session_state.tradingview_studies):
                indicators.append("IchimokuCloud@tv-basicstudies")
            if st.checkbox("Volume", value="VOL" in st.session_state.tradingview_studies):
                indicators.append("Volume@tv-basicstudies")
            if st.checkbox("On-Balance Volume (OBV)", value="OBV" in st.session_state.tradingview_studies):
                indicators.append("OBV@tv-basicstudies")
        
        # Update session state with selected indicators
        if st.button("Apply Indicators"):
            st.session_state.tradingview_studies = indicators
            st.success("Chart indicators updated! Return to the Stock Chart tab to see them.")
        
        # Chart Type Selection
        st.write("### Chart Type")
        chart_types = ["Candles", "Bars", "Line", "Area", "Heikin Ashi"]
        chart_type = st.selectbox("Select Chart Type", chart_types)
        
        st.info(f"Chart type '{chart_type}' selected. You can also change the chart type directly on the TradingView chart using the chart type selector in the top toolbar.")
        
        # Additional Chart Settings
        st.write("### Additional Options")
        st.write("These settings can be configured directly on the TradingView chart:")
        
        add_col1, add_col2 = st.columns(2)
        
        with add_col1:
            st.write("- Drawing tools for technical analysis")
            st.write("- Comparison with other symbols")
            st.write("- Add text notes to the chart")
            st.write("- Set price alerts")
            
        with add_col2:
            st.write("- Multiple timeframe analysis")
            st.write("- Chart patterns recognition")
            st.write("- Trading ranges and projections")
            st.write("- Save and share chart layouts")
        
        # TradingView Pro Information
        st.write("### Trading View Pro Features")
        st.info("The embedded charts provide basic functionality. For advanced features like custom indicators, server-side alerts, and multiple charts layout, consider signing up for a TradingView Pro account directly on their website.")

# Switch between different app sections based on user selection
if st.session_state.selected_app == "Stock Analysis":
    show_stock_analysis()
elif st.session_state.selected_app == "Trading Platform":
    show_trading_platform()
elif st.session_state.selected_app == "TradingView Charts":
    show_tradingview_charts()
elif st.session_state.selected_app == "India Market":
    show_india_market()
elif st.session_state.selected_app == "My Portfolio Tracker":
    show_my_portfolio_tracker()
elif st.session_state.selected_app == "Growth Tracker":
    show_growth_tracker()
elif st.session_state.selected_app == "Dhan Trading":
    show_dhan_trading()
elif st.session_state.selected_app == "Investment Portfolio":
    show_investment_portfolio()
elif st.session_state.selected_app == "Telegram Alerts":
    show_telegram_alerts()
else:
    # Default to stock analysis if no app selected
    show_stock_analysis()

# Footer
st.markdown("---")
st.markdown("Data source: Yahoo Finance via yfinance library")
#KRISHU IS GREATE KING YO YO YO YO