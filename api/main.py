from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import yfinance as yf
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="../templates")

def get_rsi(prices, window=14):
    """Calculate RSI without pandas_ta dependency"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, ticker: str = "MSFT"):
    try:
        # Get stock data
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo")
        
        # Calculate RSI
        df['RSI'] = get_rsi(df['Close'])
        current_rsi = df['RSI'].iloc[-1]
        
        # Predefined news
        news_headlines = [
            "Market shows positive trend in tech sector",
            f"{ticker} announces strategic partnerships",
            "Global markets respond to economic indicators"
        ]
        
        # Prepare chart data
        dates = df.index.strftime('%Y-%m-%d').tolist()
        prices = df["Close"].tolist()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "ticker": ticker,
            "current_price": prices[-1],
            "prev_price": prices[-2] if len(prices) > 1 else prices[-1],
            "rsi": current_rsi,
            "dates": dates,
            "prices": prices,
            "news": news_headlines
        })
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })
