from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import requests
import os
import time

app = FastAPI()

# Get absolute path to templates
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_path = os.path.join(current_dir, '../templates')
templates = Jinja2Templates(directory=templates_path)

# API Configuration
ALPHA_VANTAGE_API_KEY = "THVYVB11QVK86DRS"
FMP_API_KEY = "S9vfnBUUjQXJ0d56BXO0s4EtEG3k909o"

def get_stock_data(ticker):
    """Get stock data with multiple fallback sources"""
    # Attempt 1: Alpha Vantage (primary)
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url, timeout=5).json()
        
        if 'Time Series (Daily)' in response:
            data = response['Time Series (Daily)']
            df = pd.DataFrame(data).T
            df.index = pd.to_datetime(df.index)
            df = df.astype(float)
            df.columns = [col.split(" ")[1] for col in df.columns]
            return df.sort_index()
    except Exception as e:
        print(f"Alpha Vantage error: {str(e)}")
    
    # Attempt 2: Financial Modeling Prep (secondary)
    try:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?apikey={FMP_API_KEY}"
        response = requests.get(url, timeout=5).json()
        
        if 'historical' in response:
            df = pd.DataFrame(response['historical'])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.rename(columns={'close': 'Close'}, inplace=True)
            return df[['Close']].iloc[::-1]  # Reverse to chronological order
    except Exception as e:
        print(f"FMP error: {str(e)}")
    
    # Fallback: Static sample data
    print("Using fallback data")
    return pd.DataFrame({
        'Close': [420.69, 419.32, 418.75, 417.80, 418.25, 419.50, 420.10, 421.30],
        'date': pd.date_range(end=pd.Timestamp.today(), periods=8, freq='D')
    }).set_index('date')

def get_rsi(prices):
    """Simplified RSI calculation"""
    try:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    except:
        return pd.Series([50] * len(prices))

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, ticker: str = "MSFT"):
    try:
        # Get stock data with retries
        df = get_stock_data(ticker)
        
        # Calculate RSI
        df['RSI'] = get_rsi(df['Close'])
        current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().all() else 50
        
        # Prepare chart data
        dates = df.index.strftime('%Y-%m-%d').tolist()
        prices = df["Close"].tolist()
        current_price = prices[-1]
        prev_price = prices[-2] if len(prices) > 1 else current_price
        
        # Generate signal
        signal = "HOLD"
        signal_color = "gray"
        if current_rsi < 30:
            signal = "BUY"
            signal_color = "green"
        elif current_rsi > 70:
            signal = "SELL"
            signal_color = "red"
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "ticker": ticker,
            "signal": signal,
            "signal_color": signal_color,
            "current_price": current_price,
            "prev_price": prev_price,
            "rsi": current_rsi,
            "dates": dates,
            "prices": prices
        })
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })
