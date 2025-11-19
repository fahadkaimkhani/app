# pages/utils/plotly_figure.py
import plotly.graph_objects as go
import pandas_ta as pta
import pandas as pd
import dateutil
import datetime
import streamlit as st
from typing import Optional

# Default accents (aligns with main)
DEFAULT_ACCENT = "#1f77b4"
POS_ACCENT = "#2ca02c"
NEG_ACCENT = "#d62728"
MUTED = "#6c757d"
PAPER_BG = None  # do not force a theme; charts will use transparent bg where possible

# --------------------------
# Cached fetch helper
# --------------------------
@st.cache_data(ttl=3600)
def fetch_and_cache_history(ticker: str, start: datetime.date, end: datetime.date) -> Optional[pd.DataFrame]:
    import yfinance as yf
    try:
        t = yf.Ticker(ticker)
        df = t.history(start=start, end=end)
        if df is None or df.empty:
            return df
        df.index.name = "Date"
        # Guarantee required cols
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna(how='all')
        return df
    except Exception:
        return None

# --------------------------
# Pretty table (plotly)
# --------------------------
def format_val(v):
    try:
        if isinstance(v, (int, float)):
            if abs(v) >= 1e12:
                return f"{v/1e12:.2f}T"
            if abs(v) >= 1e9:
                return f"{v/1e9:.2f}B"
            if abs(v) >= 1e6:
                return f"{v/1e6:.2f}M"
            return f"{v:.4g}"
        return str(v)
    except Exception:
        return str(v)

def plotly_table(dataframe: pd.DataFrame, accent: str = DEFAULT_ACCENT, bg_mode: str = "plain"):
    """
    Create a visually pleasing table. bg_mode: 'plain' or 'accented' (accent header)
    """
    df = dataframe.copy()
    labels = ["<b>" + str(i) + "</b>" for i in df.index]
    values = [format_val(v) for v in df.iloc[:, 0]]

    headerColor = accent if bg_mode == "accented" else "#f7f7f7"
    headerFontColor = "white" if bg_mode == "accented" else "black"
    rowEven = "#ffffff" if bg_mode == "plain" else "#0f1721"
    rowOdd = "#f8f9fa" if bg_mode == "plain" else "#0b0d11"

    fig = go.Figure(data=[go.Table(
        header=dict(values=["<b>Metric</b>", "<b>Value</b>"],
                    fill_color=headerColor,
                    font=dict(color=headerFontColor, size=13),
                    align='left',
                    height=36),
        cells=dict(values=[labels, values],
                   fill_color=[[rowOdd, rowEven] * ((len(df) + 1) // 2)],
                   align='left',
                   font=dict(color="black" if bg_mode == "plain" else "#e8e8e8", size=13),
                   height=32)
    )])
    # let Streamlit/Plotly choose the best background; don't force global CSS
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig

# --------------------------
# Filter helper
# --------------------------
def filter_data(dataframe: pd.DataFrame, num_period: str):
    df = dataframe.copy().reset_index()
    if 'Date' not in df.columns:
        df.rename(columns={'index': 'Date'}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    latest = df['Date'].iloc[-1]
    if num_period == '1mo':
        cutoff = latest - dateutil.relativedelta.relativedelta(months=1)
    elif num_period == '5d':
        cutoff = latest - dateutil.relativedelta.relativedelta(days=5)
    elif num_period == '6mo':
        cutoff = latest - dateutil.relativedelta.relativedelta(months=6)
    elif num_period == '1y':
        cutoff = latest - dateutil.relativedelta.relativedelta(years=1)
    elif num_period == '5y':
        cutoff = latest - dateutil.relativedelta.relativedelta(years=5)
    elif num_period == 'ytd':
        cutoff = datetime.datetime(latest.year, 1, 1)
    elif num_period == 'max' or num_period == '':
        cutoff = df['Date'].iloc[0]
    else:
        cutoff = df['Date'].iloc[0]
    return df[df['Date'] > cutoff]

# --------------------------
# Charts
# --------------------------
def close_chart(dataframe: pd.DataFrame, num_period: str = '', accent: str = DEFAULT_ACCENT):
    df = dataframe.copy().reset_index()
    df = filter_data(df, num_period)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines', name='Close', line=dict(width=2, color=accent)))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Open'], mode='lines', name='Open', line=dict(width=1, color="#999999")))
    fig.update_layout(height=520, xaxis=dict(rangeslider=dict(visible=True)))
    return fig

def candlestick(dataframe: pd.DataFrame, num_period: str, accent: str = DEFAULT_ACCENT):
    df = dataframe.copy().reset_index()
    df = filter_data(df, num_period)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing=dict(line=dict(color=accent), fillcolor=accent),
        decreasing=dict(line=dict(color=NEG_ACCENT), fillcolor=NEG_ACCENT)
    ))
    fig.update_layout(showlegend=False, height=520)
    return fig

def RSI(dataframe: pd.DataFrame, num_period: str, accent: str = DEFAULT_ACCENT, return_series: bool = False):
    df = dataframe.copy().reset_index()
    df['RSI'] = pta.rsi(df['Close'], length=14)
    if return_series:
        return df['RSI']
    df = filter_data(df, num_period)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], mode='lines', name='RSI', line=dict(width=2, color=accent)))
    fig.add_hline(y=70, line_dash="dash", line_color=NEG_ACCENT)
    fig.add_hline(y=30, line_dash="dash", line_color=POS_ACCENT)
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(height=220)
    return fig

def Moving_average(dataframe: pd.DataFrame, num_period: str, ma_period: int = 50, accent: str = DEFAULT_ACCENT):
    df = dataframe.copy().reset_index()
    df['SMA'] = pta.sma(df['Close'], length=ma_period)
    df = filter_data(df, num_period)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Close', mode='lines', line=dict(width=2, color=accent)))
    if 'SMA' in df.columns:
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA'], name=f'SMA {ma_period}', mode='lines', line=dict(width=2, color="#b36bff")))
    fig.update_layout(height=520)
    return fig

def MACD(dataframe: pd.DataFrame, num_period: str, accent: str = DEFAULT_ACCENT):
    df = dataframe.copy().reset_index()
    macd = pta.macd(df['Close'])
    macd_col = macd.columns[0]
    signal_col = macd.columns[1]
    hist_col = macd.columns[2]
    df['MACD'] = macd[macd_col]
    df['Signal'] = macd[signal_col]
    df['Hist'] = macd[hist_col]
    df = filter_data(df, num_period)
    colors = [POS_ACCENT if v >= 0 else NEG_ACCENT for v in df['Hist'].fillna(0)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], name='MACD', line=dict(color=accent, width=2)))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Signal'], name='Signal', line=dict(color="#ff7f0e", width=1, dash='dash')))
    fig.add_trace(go.Bar(x=df['Date'], y=df['Hist'], marker_color=colors, name='Histogram'))
    fig.update_layout(height=240)
    return fig

