# stock_analysis.py
import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import requests
import warnings
from utils.plotly_figure import (
    plotly_table,
    candlestick,
    RSI,
    MACD,
    close_chart,
    Moving_average,
    fetch_and_cache_history
)

# -------------------------
# Global warning filters
# -------------------------
warnings.filterwarnings("ignore", category=DeprecationWarning)

# -------------------------
# Accent colors (dark-theme palette but not forcing theme)
# -------------------------
ACCENT_BLUE = "#1f77b4"   # electric blue for technical elements
ACCENT_GREEN = "#2ca02c"  # emerald green for positive/ESG
ACCENT_RED = "#d62728"    # coral red for negatives
MUTED = "#6c757d"

# NewsAPI key (you provided)
NEWSAPI_KEY = "625c7256e5b4447da8cbe763b45dff47"

st.set_page_config(page_title="TradeWise — Stock Analysis", page_icon="📈", layout="wide")
st.title("TradeWise — Stock Analysis")
st.markdown("A focused stock analysis dashboard with indicators, fundamentals, news + sentiment, alerts, and CSV export.")

# -------------------------
# Sidebar controls
# -------------------------
with st.sidebar:
    st.header("Controls")
    ticker = st.text_input("Ticker symbol", value="TSLA").upper().strip()
    today = datetime.date.today()
    default_start = datetime.date(today.year - 1, today.month, today.day)
    start_date = st.date_input("Start date", value=default_start)
    end_date = st.date_input("End date", value=today)
    if start_date >= end_date:
        st.warning("Start date must be before end date. Resetting to defaults.")
        start_date = default_start
        end_date = today

    st.markdown("---")
    st.subheader("Chart & Indicator")
    chart_type = st.selectbox("Chart type", ["Candle", "Line"])
    indicator = st.selectbox("Indicator", ["None", "RSI", "MACD", "Moving Average"])
    ma_period = st.slider("SMA period (days)", 5, 200, 50) if indicator == "Moving Average" else 50

    st.markdown("---")
    st.subheader("Quick Range")
    quick = st.selectbox("", ['Custom', '5D', '1M', '6M', 'YTD', '1Y', '5Y', 'MAX'])
    quick_map = {"5D": "5d", "1M": "1mo", "6M": "6mo", "YTD": "ytd", "1Y": "1y", "5Y": "5y", "MAX": "max", "Custom": ""}
    num_period = quick_map.get(quick, "")

    st.markdown("---")
    st.subheader("Alerts")
    price_alert = st.number_input("Alert if price >= (0 to disable)", min_value=0.0, value=0.0, format="%.2f")
    rsi_alert = st.slider("Alert if RSI <= (0 to disable)", 0, 100, 0)

    st.markdown("---")
    st.subheader("News")
    st.write("Showing headline, short summary and sentiment.")
    use_newsapi = st.checkbox("Use NewsAPI (recommended)", value=True)
    # key shown or not (you already provided in code)
    if use_newsapi:
        st.caption("Using configured NewsAPI key (hidden in UI).")

# -------------------------
# Defensive ticker/info fetch
# -------------------------
try:
    ticker_obj = yf.Ticker(ticker)
    info = ticker_obj.info or {}
except Exception:
    info = {}

# Header overview
col1, col2 = st.columns([3, 2])
with col1:
    st.subheader(f"{ticker} — Overview")
    summary = info.get("longBusinessSummary", "No summary available for this ticker.")
    st.write(summary[:800] + ("..." if len(summary) > 800 else ""))
with col2:
    st.write("**Sector:**", info.get("sector", "N/A"))
    st.write("**Employees:**", info.get("fullTimeEmployees", "N/A"))
    st.write("**Website:**", info.get("website", "N/A"))

# Fundamentals table
fundamental_idx = ['Market Cap', 'Beta', 'EPS', 'PE Ratio', 'Quick Ratio', 'Revenue per share', 'Profit Margins',
                   'Debt to Equity', 'Return on Equity', 'Dividend Yield']
vals = [
    info.get("marketCap", "N/A"),
    info.get("beta", "N/A"),
    info.get("trailingEps", "N/A"),
    info.get("trailingPE", "N/A"),
    info.get("quickRatio", "N/A"),
    info.get("revenuePerShare", "N/A"),
    (round(info.get("profitMargins", 0), 4) if isinstance(info.get("profitMargins", None), (int, float)) else info.get("profitMargins", "N/A")),
    info.get("debtToEquity", "N/A"),
    info.get("returnOnEquity", "N/A"),
    info.get("dividendYield", "N/A")
]
fund_df = pd.DataFrame(index=fundamental_idx, data={"Value": vals})

colA, colB = st.columns(2)
with colA:
    st.plotly_chart(plotly_table(fund_df.iloc[:5], accent=ACCENT_BLUE, bg_mode="accented"), width="stretch")
with colB:
    st.plotly_chart(plotly_table(fund_df.iloc[5:], accent=ACCENT_GREEN, bg_mode="accented"), width="stretch")

# -------------------------
# Historical data (cached)
# -------------------------
hist = fetch_and_cache_history(ticker, start_date, end_date)
if hist is None or hist.empty:
    st.error("No historical data found for this ticker/date-range.")
    st.stop()

# Top metrics
try:
    last_close = hist['Close'].iloc[-1]
    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else last_close
    change = last_close - prev_close
    colm = st.columns(4)
    colm[0].metric("Price", f"{last_close:.2f}", f"{change:+.2f}")
    colm[1].metric("Open", f"{hist['Open'].iloc[-1]:.2f}")
    colm[2].metric("High", f"{hist['High'].iloc[-1]:.2f}")
    colm[3].metric("Low", f"{hist['Low'].iloc[-1]:.2f}")
except Exception:
    pass

# Tabs
tab_overview, tab_charts, tab_indicators, tab_news = st.tabs(["Overview", "Charts", "Indicators", "News & ESG"])

with tab_overview:
    st.subheader("Recent Historical Data")
    st.dataframe(hist.tail(10).round(4), width="stretch")

    st.subheader("Dividends & Actions")
    try:
        actions = ticker_obj.actions
        if actions is not None and not actions.empty:
            st.dataframe(actions.tail(10))
        else:
            st.info("No dividend/split actions available.")
    except Exception:
        st.info("Actions not available.")

    st.subheader("Earnings")
    st.info("Earnings view is temporarily disabled due to upstream API changes in yfinance.")

with tab_charts:
    st.subheader("Price Chart")
    plot_period = num_period if num_period != "" else "1y"
    if chart_type == "Candle":
        st.plotly_chart(candlestick(hist.reset_index(), plot_period, accent=ACCENT_BLUE), width="stretch")
    else:
        st.plotly_chart(close_chart(hist.reset_index(), plot_period, accent=ACCENT_BLUE), width="stretch")

    st.subheader("Volume (recent)")
    st.bar_chart(hist['Volume'].tail(180))

with tab_indicators:
    st.subheader("Selected Indicator")
    if indicator == "RSI":
        st.plotly_chart(RSI(hist.reset_index(), plot_period, accent=ACCENT_BLUE), width="stretch")
    elif indicator == "MACD":
        st.plotly_chart(MACD(hist.reset_index(), plot_period, accent=ACCENT_BLUE), width="stretch")
    elif indicator == "Moving Average":
        st.plotly_chart(Moving_average(hist.reset_index(), plot_period, ma_period, accent=ACCENT_BLUE), width="stretch")
    else:
        st.info("Choose an indicator from the sidebar to display.")

    st.subheader("Alerts")
    triggered = []
    if price_alert > 0 and last_close >= price_alert:
        triggered.append(f"Price alert: {ticker} >= {price_alert:.2f} (current: {last_close:.2f})")

    try:
        rsi_series = RSI(hist.reset_index(), plot_period, accent=ACCENT_BLUE, return_series=True)
        current_rsi = rsi_series.iloc[-1]
    except Exception:
        current_rsi = None

    if rsi_alert > 0 and current_rsi is not None and current_rsi <= rsi_alert:
        triggered.append(f"RSI alert: RSI <= {rsi_alert} (current RSI: {current_rsi:.2f})")

    if triggered:
        for t in triggered:
            st.warning(t)
    else:
        st.success("No alerts triggered.")

    st.download_button("Download historical CSV", hist.to_csv().encode('utf-8'), file_name=f"{ticker}_history.csv", mime="text/csv")

with tab_news:
    st.subheader("News & Sentiment (Headline + short summary + sentiment)")
    # sentiment helper (small lexicon + score)
    def sentiment_and_score(text: str):
        pos_words = {"gain","beat","up","strong","positive","record","surge","growth","raise","outperform","upgrade","profit"}
        neg_words = {"drop","fall","loss","miss","down","weak","decline","warning","cut","recall","lawsuit","downgrade","loss"}
        t = (text or "").lower()
        pos = sum(1 for w in pos_words if w in t)
        neg = sum(1 for w in neg_words if w in t)
        score = pos - neg
        if score > 0:
            label = "Positive"
        elif score < 0:
            label = "Negative"
        else:
            label = "Neutral"
        return label, score

    headlines = []
    if use_newsapi and NEWSAPI_KEY:
        try:
            params = {
                "q": ticker,
                "language": "en",
                "pageSize": 6,
                "sortBy": "publishedAt",
                "apiKey": NEWSAPI_KEY
            }
            resp = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
            if resp.ok:
                items = resp.json().get("articles", []) or []
                for it in items[:6]:
                    title = it.get("title", "")
                    desc = it.get("description") or it.get("content") or ""
                    url = it.get("url")
                    source = it.get("source", {}).get("name", "")
                    pub = it.get("publishedAt", "")
                    headlines.append({"title": title, "desc": desc, "url": url, "source": source, "publishedAt": pub})
            else:
                st.info("NewsAPI returned no results (or invalid key). Falling back to summary-based headline.")
        except Exception:
            st.info("External news fetch failed — falling back to summary-based headline.")

    # fallback if no headlines
    if not headlines:
        raw_news = info.get("news", None)
        if raw_news:
            for n in raw_news[:5]:
                headlines.append({"title": n.get("title", ""), "desc": n.get("summary", ""), "url": n.get("link", ""), "source": n.get("publisher", ""), "publishedAt": ""})
        else:
            headlines.append({"title": f"{ticker} — latest summary", "desc": summary[:300] if summary else "", "url": "", "source": "", "publishedAt": ""})

    # build df with sentiment
    rows = []
    for h in headlines:
        lab, score = sentiment_and_score(h.get("title","") + " " + h.get("desc",""))
        rows.append({"headline": h.get("title"), "summary": h.get("desc"), "source": h.get("source"), "publishedAt": h.get("publishedAt"), "sentiment": lab, "score": score, "url": h.get("url")})
    news_df = pd.DataFrame(rows)
    # display with clickable links where available
    def make_link(url, text):
        if url:
            return f'<a href="{url}" target="_blank">{text}</a>'
        return text

    # prepare display
    display_df = news_df.copy()
    display_df["headline"] = display_df.apply(lambda r: make_link(r["url"], r["headline"]), axis=1)
    display_df = display_df[["headline", "summary", "source", "publishedAt", "sentiment", "score"]]
    st.write("**Note:** Sentiment is a simple lexicon-based heuristic (for demo). Replace with a proper NLP model for production.")
    st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # ESG
    st.subheader("ESG / Sustainability (if available)")
    try:
        sustain = ticker_obj.sustainability
        if sustain is not None and not sustain.empty:
            st.dataframe(sustain)
        else:
            st.info("No ESG/sustainability metrics available via yfinance for this ticker.")
    except Exception:
        st.info("ESG data not available.")

st.caption("TradeWise — Stock Analysis. Accent colors chosen for dark-themed visuals (you can toggle Streamlit theme).")
