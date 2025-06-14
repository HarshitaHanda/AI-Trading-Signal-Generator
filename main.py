from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import numpy as np
from datetime import datetime

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Lightweight sentiment analysis
def simple_sentiment_analysis(headline):
    positive_keywords = ['buy', 'strong', 'growth', 'beat', 'upgrade', 'bullish']
    negative_keywords = ['sell', 'cut', 'downgrade', 'bearish', 'warning', 'drop']
    
    score = 0
    for word in positive_keywords:
        if word in headline.lower():
            score += 1
    for word in negative_keywords:
        if word in headline.lower():
            score -= 1
            
    if score > 0:
        return 'POSITIVE', 0.7 + min(0.3, score*0.1)
    elif score < 0:
        return 'NEGATIVE', 0.7 + min(0.3, abs(score)*0.1)
    return 'NEUTRAL', 0.5

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, ticker: str = "MSFT"):
    # Fetch stock data
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo")
        
        # Technical analysis
        df.ta.rsi(length=14, append=True)
        current_rsi = df["RSI_14"].iloc[-1] if "RSI_14" in df.columns else 50
        
        # Predefined news
        financial_news = {
            "MSFT": ["Microsoft expands AI cloud partnerships", "Azure growth exceeds expectations"],
            "AAPL": ["Apple announces AI-powered iPhone features", "Supply chain improvements boost production"],
            "NVDA": ["Nvidia unveils next-gen AI chips", "Data center demand drives record revenue"],
            "DEFAULT": ["Tech stocks rally on AI optimism", "Fed maintains interest rates"]
        }
        news_headlines = financial_news.get(ticker, financial_news["DEFAULT"])
        
        # Analyze sentiment
        sentiment_results = []
        for headline in news_headlines:
            sentiment, confidence = simple_sentiment_analysis(headline)
            sentiment_results.append({
                "headline": headline,
                "sentiment": sentiment,
                "confidence": confidence
            })
        
        # Generate signal
        signal = "HOLD"
        signal_color = "gray"
        reason = "Market neutral"
        
        bullish_news = [n for n in sentiment_results if n['sentiment'] == 'POSITIVE' and n['confidence'] > 0.8]
        bearish_news = [n for n in sentiment_results if n['sentiment'] == 'NEGATIVE' and n['confidence'] > 0.8]
        
        if bullish_news and current_rsi < 35:
            signal = "STRONG BUY"
            signal_color = "green"
            reason = f"{len(bullish_news)} bullish signals + Oversold (RSI: {current_rsi:.1f})"
        elif bearish_news and current_rsi > 65:
            signal = "SELL"
            signal_color = "red"
            reason = f"{len(bearish_news)} bearish signals + Overbought (RSI: {current_rsi:.1f})"
        
        # Prepare chart data
        dates = df.index.strftime('%Y-%m-%d').tolist()
        prices = df["Close"].tolist()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "ticker": ticker,
            "signal": signal,
            "signal_color": signal_color,
            "reason": reason,
            "current_price": prices[-1],
            "prev_price": prices[-2] if len(prices) > 1 else prices[-1],
            "rsi": current_rsi,
            "dates": dates,
            "prices": prices,
            "news": sentiment_results
        })
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })
