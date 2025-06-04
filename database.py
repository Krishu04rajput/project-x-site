import os
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Table, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import json

# Get the database URL from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")

# Make sure we have a valid database URL
if not DATABASE_URL:
    # Use a default SQLite database if no PostgreSQL URL is provided
    DATABASE_URL = "sqlite:///projectx.db"
    print(f"Warning: No DATABASE_URL found, using SQLite: {DATABASE_URL}")
else:
    # Fix common issues with PostgreSQL URLs from environment variables
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create SQLAlchemy engine and session with proper SSL handling
if "postgresql" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"sslmode": "allow"}
    )
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define database models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    watchlists = relationship("Watchlist", back_populates="user")
    portfolios = relationship("Portfolio", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    company_name = Column(String)
    sector = Column(String)
    industry = Column(String)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    watchlist_items = relationship("WatchlistItem", back_populates="stock")
    portfolio_items = relationship("PortfolioItem", back_populates="stock")
    transactions = relationship("Transaction", back_populates="stock")

class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    items = relationship("WatchlistItem", back_populates="watchlist")

class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"))
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    added_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="items")
    stock = relationship("Stock", back_populates="watchlist_items")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    items = relationship("PortfolioItem", back_populates="portfolio")

class PortfolioItem(Base):
    __tablename__ = "portfolio_items"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    quantity = Column(Float)
    average_price = Column(Float)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="items")
    stock = relationship("Stock", back_populates="portfolio_items")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    transaction_type = Column(String)  # Buy or Sell
    quantity = Column(Float)
    price = Column(Float)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    stock = relationship("Stock", back_populates="transactions")

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    theme = Column(String, default="light")
    default_app = Column(String, default="Stock Analysis")
    favorite_symbols = Column(String)  # Stored as JSON string
    chart_preferences = Column(String)  # Stored as JSON string

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    alert_type = Column(String)  # Price Above, Price Below, % Change, etc.
    value = Column(Float)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Create all tables in the database
def create_tables():
    Base.metadata.create_all(bind=engine)

# Database helper functions
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Initialize database with demo data
def initialize_demo_data():
    db = get_db()
    
    # Check if we already have data
    existing_user = db.query(User).first()
    if existing_user:
        db.close()
        return
    
    # Create demo user
    demo_user = User(username="demo_user", email="demo@example.com")
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    
    # Add default watchlist
    default_watchlist = Watchlist(name="My Watchlist", user_id=demo_user.id)
    db.add(default_watchlist)
    db.commit()
    db.refresh(default_watchlist)
    
    # Add default portfolio
    default_portfolio = Portfolio(name="My Portfolio", user_id=demo_user.id)
    db.add(default_portfolio)
    db.commit()
    db.refresh(default_portfolio)
    
    # Add some stocks
    stock_data = [
        {"symbol": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
        {"symbol": "MSFT", "company_name": "Microsoft Corporation", "sector": "Technology", "industry": "Software"},
        {"symbol": "GOOGL", "company_name": "Alphabet Inc.", "sector": "Technology", "industry": "Internet Services"},
        {"symbol": "AMZN", "company_name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "industry": "Internet Retail"},
        {"symbol": "TSLA", "company_name": "Tesla, Inc.", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers"},
        {"symbol": "NVDA", "company_name": "NVIDIA Corporation", "sector": "Technology", "industry": "Semiconductors"},
        {"symbol": "META", "company_name": "Meta Platforms, Inc.", "sector": "Technology", "industry": "Internet Services"},
        {"symbol": "NFLX", "company_name": "Netflix, Inc.", "sector": "Communication Services", "industry": "Entertainment"},
    ]
    
    for stock_info in stock_data:
        stock = Stock(**stock_info)
        db.add(stock)
    
    db.commit()
    
    # Add stocks to watchlist
    for symbol in ["AAPL", "MSFT", "GOOGL", "AMZN"]:
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if stock:
            watchlist_item = WatchlistItem(watchlist_id=default_watchlist.id, stock_id=stock.id)
            db.add(watchlist_item)
    
    db.commit()
    
    # Add stocks to portfolio with sample holdings
    portfolio_data = [
        {"symbol": "AAPL", "quantity": 10, "average_price": 155.75},
        {"symbol": "MSFT", "quantity": 5, "average_price": 285.30},
        {"symbol": "GOOGL", "quantity": 3, "average_price": 125.50},
        {"symbol": "NVDA", "quantity": 8, "average_price": 212.80},
    ]
    
    for item in portfolio_data:
        stock = db.query(Stock).filter(Stock.symbol == item["symbol"]).first()
        if stock:
            portfolio_item = PortfolioItem(
                portfolio_id=default_portfolio.id,
                stock_id=stock.id,
                quantity=item["quantity"],
                average_price=item["average_price"]
            )
            db.add(portfolio_item)
            
            # Add a corresponding "buy" transaction
            transaction = Transaction(
                user_id=demo_user.id,
                stock_id=stock.id,
                transaction_type="Buy",
                quantity=item["quantity"],
                price=item["average_price"],
                date=datetime.datetime.now() - datetime.timedelta(days=30)
            )
            db.add(transaction)
    
    db.commit()
    
    # Add user preferences
    favorite_symbols = json.dumps(["AAPL", "MSFT", "GOOGL"])
    chart_preferences = json.dumps({
        "show_moving_averages": True,
        "default_ma_periods": [20, 50],
        "default_chart_type": "candlestick",
        "show_volume": True
    })
    
    user_prefs = UserPreference(
        user_id=demo_user.id,
        theme="light",
        default_app="Stock Analysis",
        favorite_symbols=favorite_symbols,
        chart_preferences=chart_preferences
    )
    db.add(user_prefs)
    
    # Add sample alerts
    alert_data = [
        {"symbol": "AAPL", "alert_type": "Price Above", "value": 180.0},
        {"symbol": "MSFT", "alert_type": "Price Below", "value": 260.0},
        {"symbol": "TSLA", "alert_type": "% Change", "value": 5.0},
    ]
    
    for alert_info in alert_data:
        stock = db.query(Stock).filter(Stock.symbol == alert_info["symbol"]).first()
        if stock:
            alert = Alert(
                user_id=demo_user.id,
                stock_id=stock.id,
                alert_type=alert_info["alert_type"],
                value=alert_info["value"]
            )
            db.add(alert)
    
    db.commit()
    db.close()

# Database utility functions
def get_user_watchlists(user_id):
    db = get_db()
    watchlists = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
    db.close()
    return watchlists

def get_watchlist_stocks(watchlist_id):
    db = get_db()
    items = db.query(
        Stock
    ).join(
        WatchlistItem, WatchlistItem.stock_id == Stock.id
    ).filter(
        WatchlistItem.watchlist_id == watchlist_id
    ).all()
    db.close()
    return items

def get_user_portfolios(user_id):
    db = get_db()
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    db.close()
    return portfolios

def get_portfolio_items(portfolio_id):
    db = get_db()
    items = db.query(
        Stock, PortfolioItem.quantity, PortfolioItem.average_price
    ).join(
        PortfolioItem, PortfolioItem.stock_id == Stock.id
    ).filter(
        PortfolioItem.portfolio_id == portfolio_id
    ).all()
    db.close()
    return items

def get_user_transactions(user_id, limit=20):
    db = get_db()
    transactions = db.query(
        Transaction, Stock.symbol
    ).join(
        Stock, Transaction.stock_id == Stock.id
    ).filter(
        Transaction.user_id == user_id
    ).order_by(
        Transaction.date.desc()
    ).limit(limit).all()
    db.close()
    return transactions

def get_user_alerts(user_id):
    db = get_db()
    alerts = db.query(
        Alert, Stock.symbol
    ).join(
        Stock, Alert.stock_id == Stock.id
    ).filter(
        Alert.user_id == user_id, 
        Alert.active == True
    ).all()
    db.close()
    return alerts

def add_stock_to_watchlist(watchlist_id, symbol):
    db = get_db()
    
    # Check if stock exists
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        # If not, create it
        stock = Stock(symbol=symbol, company_name=f"{symbol} Inc.")
        db.add(stock)
        db.commit()
        db.refresh(stock)
    
    # Check if stock is already in watchlist
    existing = db.query(WatchlistItem).filter(
        WatchlistItem.watchlist_id == watchlist_id,
        WatchlistItem.stock_id == stock.id
    ).first()
    
    if not existing:
        item = WatchlistItem(watchlist_id=watchlist_id, stock_id=stock.id)
        db.add(item)
        db.commit()
        result = True
    else:
        result = False
    
    db.close()
    return result

def remove_stock_from_watchlist(watchlist_id, symbol):
    db = get_db()
    
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if stock:
        item = db.query(WatchlistItem).filter(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.stock_id == stock.id
        ).first()
        
        if item:
            db.delete(item)
            db.commit()
            result = True
        else:
            result = False
    else:
        result = False
    
    db.close()
    return result

def add_stock_transaction(user_id, symbol, transaction_type, quantity, price):
    db = get_db()
    
    # Get or create stock
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        stock = Stock(symbol=symbol, company_name=f"{symbol} Inc.")
        db.add(stock)
        db.commit()
        db.refresh(stock)
    
    # Add transaction
    transaction = Transaction(
        user_id=user_id,
        stock_id=stock.id,
        transaction_type=transaction_type,
        quantity=quantity,
        price=price
    )
    db.add(transaction)
    db.commit()
    
    # Update portfolio
    # Get default portfolio
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not portfolio:
        portfolio = Portfolio(name="My Portfolio", user_id=user_id)
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
    
    # Check if stock is already in portfolio
    portfolio_item = db.query(PortfolioItem).filter(
        PortfolioItem.portfolio_id == portfolio.id,
        PortfolioItem.stock_id == stock.id
    ).first()
    
    if transaction_type == "Buy":
        if not portfolio_item:
            # Add new portfolio item
            portfolio_item = PortfolioItem(
                portfolio_id=portfolio.id,
                stock_id=stock.id,
                quantity=quantity,
                average_price=price
            )
            db.add(portfolio_item)
        else:
            # Update existing item with weighted average price
            total_value = (portfolio_item.quantity * portfolio_item.average_price) + (quantity * price)
            new_quantity = portfolio_item.quantity + quantity
            portfolio_item.average_price = total_value / new_quantity
            portfolio_item.quantity = new_quantity
    elif transaction_type == "Sell":
        if portfolio_item:
            # Reduce quantity
            portfolio_item.quantity -= quantity
            
            # Remove item if quantity becomes zero or negative
            if portfolio_item.quantity <= 0:
                db.delete(portfolio_item)
    
    db.commit()
    db.close()
    return True

def get_or_create_user(username, email):
    try:
        db = get_db()
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, email=email)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        db.close()
        return user
    except Exception as e:
        print(f"Error in get_or_create_user: {e}")
        # Create a dummy user object without touching the database
        dummy_user = User(id=1, username=username, email=email)
        return dummy_user

def get_user_preferences(user_id):
    try:
        db = get_db()
        
        prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if not prefs:
            # Create default preferences
            favorite_symbols = json.dumps(["AAPL", "MSFT", "GOOGL"])
            chart_preferences = json.dumps({
                "show_moving_averages": True,
                "default_ma_periods": [20, 50],
                "default_chart_type": "candlestick",
                "show_volume": True
            })
            
            prefs = UserPreference(
                user_id=user_id,
                theme="light",
                default_app="Stock Analysis",
                favorite_symbols=favorite_symbols,
                chart_preferences=chart_preferences
            )
            
            try:
                db.add(prefs)
                db.commit()
                db.refresh(prefs)
            except Exception as e:
                print(f"Error saving preferences: {e}")
                db.rollback()
                # Create a dummy preference object
                prefs = UserPreference(
                    user_id=user_id,
                    theme="light",
                    default_app="Stock Analysis",
                    favorite_symbols=favorite_symbols,
                    chart_preferences=chart_preferences
                )
        
        # Parse JSON fields
        favorite_symbols_list = []
        chart_preferences_dict = {
            "show_moving_averages": True,
            "default_ma_periods": [20, 50],
            "default_chart_type": "candlestick",
            "show_volume": True
        }
        
        try:
            if prefs.favorite_symbols:
                favorite_symbols_str = str(prefs.favorite_symbols)
                if favorite_symbols_str.startswith('[') and favorite_symbols_str.endswith(']'):
                    favorite_symbols_list = json.loads(favorite_symbols_str)
        except Exception as e:
            print(f"Error parsing favorite symbols: {e}")
        
        try:
            if prefs.chart_preferences:
                chart_preferences_str = str(prefs.chart_preferences)
                if chart_preferences_str.startswith('{') and chart_preferences_str.endswith('}'):
                    chart_preferences_dict = json.loads(chart_preferences_str)
        except Exception as e:
            print(f"Error parsing chart preferences: {e}")
        
        # Add the parsed data as attributes
        prefs.favorite_symbols_list = favorite_symbols_list
        prefs.chart_preferences_dict = chart_preferences_dict
        
        db.close()
        return prefs
    except Exception as e:
        print(f"Error in get_user_preferences: {e}")
        # Return a dummy preferences object
        dummy_prefs = UserPreference(
            id=1,
            user_id=user_id,
            theme="light",
            default_app="Stock Analysis"
        )
        dummy_prefs.favorite_symbols_list = ["AAPL", "MSFT", "GOOGL"]
        dummy_prefs.chart_preferences_dict = {
            "show_moving_averages": True,
            "default_ma_periods": [20, 50],
            "default_chart_type": "candlestick",
            "show_volume": True
        }
        return dummy_prefs

def update_user_preferences(user_id, theme=None, default_app=None, favorite_symbols=None, chart_preferences=None):
    db = get_db()
    
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not prefs:
        # Create default preferences first
        prefs = UserPreference(user_id=user_id)
        db.add(prefs)
    
    if theme:
        prefs.theme = theme
    
    if default_app:
        prefs.default_app = default_app
    
    if favorite_symbols:
        prefs.favorite_symbols = json.dumps(favorite_symbols)
    
    if chart_preferences:
        prefs.chart_preferences = json.dumps(chart_preferences)
    
    db.commit()
    db.close()
    return True

def add_alert(user_id, symbol, alert_type, value):
    db = get_db()
    
    # Get or create stock
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        stock = Stock(symbol=symbol, company_name=f"{symbol} Inc.")
        db.add(stock)
        db.commit()
        db.refresh(stock)
    
    # Add alert
    alert = Alert(
        user_id=user_id,
        stock_id=stock.id,
        alert_type=alert_type,
        value=value
    )
    db.add(alert)
    db.commit()
    db.close()
    return True

def delete_alert(alert_id):
    db = get_db()
    
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        db.delete(alert)
        db.commit()
        result = True
    else:
        result = False
    
    db.close()
    return result

# Initialize database
def init_db():
    create_tables()
    initialize_demo_data()

if __name__ == "__main__":
    init_db()