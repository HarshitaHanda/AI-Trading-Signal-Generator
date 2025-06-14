import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from transformers import pipeline
import pandas_ta as ta
import yfinance as yf

# Page setup
st.set_page_config(page_title="AI Trading Signal Generator", layout="wide")
st.title("🚀 AI-Powered Trading Signal Generator")
st.caption("Real-time market analysis | Algorithmic Signal Generation")

# Initialize sentiment analyzer
@st.cache_resource
def load_model():
    return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# API Configuration
ALPHA_API_KEY = "THVYVB11QVK86DRS"  # Your Alpha Vantage key

# Sample financial news (fallback if no NewsAPI key)
SAMPLE_NEWS = [
    "Tech stocks rally as AI investments surge",
    "Fed holds interest rates steady amid inflation concerns",
    "Microsoft announces breakthrough in quantum computing",
    "Apple faces regulatory challenges in European markets",
    "Nvidia reports record data center revenue"
]

# Sidebar controls
st.sidebar.header("Configuration")
ticker = st.sidebar.text_input("Stock Ticker", "MSFT").upper()
news_api_key = st.sidebar.text_input("NewsAPI Key (Optional)", type="password", help="Get free key at newsapi.org")
sentiment_threshold = st.sidebar.slider("Bullish Threshold", 0.7, 1.0, 0.85)
rsi_threshold = st.sidebar.slider("Oversold RSI", 20, 40, 30)

if st.sidebar.button("🔃 Refresh Data", type="primary"):
    st.experimental_rerun()

# Real-time data fetching
def get_live_stock_data():
    """Get real-time stock data from Alpha Vantage"""
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={ALPHA_API_KEY}"
        response = requests.get(url, timeout=10).json()
        
        if 'Time Series (Daily)' not in response:
            st.warning(f"No data for {ticker}. Using Yahoo Finance as fallback.")
            stock = yf.Ticker(ticker)
            return stock.history(period="1mo")
        
        data = response['Time Series (Daily)']
        df = pd.DataFrame(data).T
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        df.columns = [col.split(" ")[1] for col in df.columns]
        return df.sort_index()
    except Exception as e:
        st.warning(f"Alpha Vantage error: {str(e)}. Using Yahoo Finance.")
        stock = yf.Ticker(ticker)
        return stock.history(period="1mo")

def get_live_news():
    """Get real-time financial news"""
    if not news_api_key:
        return SAMPLE_NEWS
    
    try:
        url = f"https://newsapi.org/v2/everything?q={ticker}&language=en&apiKey={news_api_key}"
        response = requests.get(url, timeout=10).json()
        
        return [
            article["title"]
            for article in response.get("articles", [])[:5]
        ]
    except:
        return SAMPLE_NEWS

# Main application
def main():
    sentiment_analyzer = load_model()
    
    # Get data
    stock_df = get_live_stock_data()
    
    if stock_df.empty:
        st.error("Failed to fetch stock data. Please try another ticker.")
        return
        
    # Technical analysis
    stock_df.ta.rsi(length=14, append=True)
    current_rsi = stock_df["RSI_14"].iloc[-1] if "RSI_14" in stock_df.columns else 50
    
    # Get news
    news_headlines = get_live_news()
    
    # Analyze sentiment
    sentiment_results = []
    for headline in news_headlines:
        try:
            result = sentiment_analyzer(headline)[0]
            sentiment_results.append({
                "headline": headline,
                "sentiment": result['label'],
                "confidence": result['score']
            })
        except:
            continue
    
    # Generate trading signal
    signal = "HOLD"
    signal_color = "gray"
    reason = "Market neutral"
    
    bullish_news = [n for n in sentiment_results if n['sentiment'] == 'POSITIVE' and n['confidence'] > sentiment_threshold]
    bearish_news = [n for n in sentiment_results if n['sentiment'] == 'NEGATIVE' and n['confidence'] > sentiment_threshold]
    
    if bullish_news:
        if current_rsi < rsi_threshold:
            signal = "STRONG BUY"
            signal_color = "green"
            reason = f"{len(bullish_news)} bullish news + Oversold (RSI: {current_rsi:.1f})"
        else:
            signal = "BUY"
            signal_color = "blue"
            reason = f"{len(bullish_news)} bullish news"
    elif bearish_news:
        if current_rsi > 70:
            signal = "SELL"
            signal_color = "red"
            reason = f"{len(bearish_news)} bearish news + Overbought (RSI: {current_rsi:.1f})"
        else:
            signal = "CAUTION"
            signal_color = "orange"
            reason = f"{len(bearish_news)} bearish news"
    
    # Dashboard layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Signal card
        st.subheader("Trading Signal")
        st.markdown(f"<h1 style='color:{signal_color};'>{signal}</h1>", unsafe_allow_html=True)
        st.caption(reason)
        
        # Price info
        current_price = stock_df["close"].iloc[-1] if "close" in stock_df.columns else stock_df["Close"].iloc[-1]
        prev_price = stock_df["close"].iloc[-2] if "close" in stock_df.columns else stock_df["Close"].iloc[-2]
        change_pct = ((current_price - prev_price) / prev_price) * 100
        st.metric(f"Current Price ({ticker})", f"${current_price:.2f}", 
                 f"{change_pct:+.2f}%", delta_color="normal")
        
        # Technical indicators
        st.subheader("Technical Indicators")
        st.progress(current_rsi/100)
        st.write(f"**RSI (14-period):** {current_rsi:.1f} {'(Oversold)' if current_rsi < 30 else '(Overbought)' if current_rsi > 70 else ''}")
        st.write(f"**Latest Change:** {change_pct:+.2f}%")
        
    with col2:
        # Price chart
        st.subheader(f"{ticker} Price Movement")
        price_col = "close" if "close" in stock_df.columns else "Close"
        fig, ax = plt.subplots(figsize=(10,4))
        stock_df[price_col].plot(ax=ax, label='Price', color='royalblue')
        ax.set_ylabel("Price ($)")
        ax.grid(alpha=0.3)
        st.pyplot(fig)
        
        # News sentiment
        st.subheader("Market Sentiment")
        if sentiment_results:
            for news in sentiment_results:
                icon = "📈" if news['sentiment'] == 'POSITIVE' else "📉"
                color = "#4CAF50" if news['sentiment'] == 'POSITIVE' else "#F44336"
                st.markdown(f"""
                <div style="border-left: 4px solid {color}; padding-left: 10px; margin: 10px 0;">
                    <b>{icon} {news['headline']}</b>
                    <div>Sentiment: <b style="color:{color}">{news['sentiment']}</b> ({news['confidence']*100:.0f}% confidence)</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No sentiment analysis available")

# Run app
if __name__ == "__main__":
    main()
