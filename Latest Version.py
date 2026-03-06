
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

# Main local data source where portfolio holdings are persisted between runs.
DATA_FILE = Path(__file__).with_name("portfolio_data.json")

# Grouped market symbols used for the live tape and market intelligence panel.
MARKET_GROUPS = {
    "Global Equity Indices": ["^GSPC", "^IXIC", "^DJI", "^RUT", "^FTSE", "^N225"],
    "Rates": ["^TNX", "^FVX", "^IRX"],
    "Commodities": ["GC=F", "SI=F", "CL=F", "NG=F"],
    "FX": ["EURUSD=X", "JPY=X", "GBPUSD=X", "BRL=X", "CNY=X"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD"],
}

# News topic proxies (ETF/ticker symbols) used to fetch context headlines.
REPORT_TOPICS = {
    "US Broad Market": "SPY",
    "Nasdaq Growth": "QQQ",
    "Semiconductors": "SOXX",
    "Energy": "XLE",
    "Financials": "XLF",
    "Emerging Markets": "EEM",
    "Commodities": "DBC",
    "Crypto": "BTC-USD",
}

# UI timeframe to yfinance period/interval translation table.
TIMEFRAME_MAP = {
    "1w": ("5d", "1h"),
    "1m": ("1mo", "1d"),
    "3m": ("3mo", "1d"),
    "6m": ("6mo", "1d"),
    "ytd": ("ytd", "1d"),
    "1y": ("1y", "1d"),
    "2y": ("2y", "1wk"),
    "5y": ("5y", "1wk"),
    "10y": ("10y", "1mo"),
    "all": ("max", "1mo"),
}

# Fundamental fields pulled from yfinance info dict for ratio analytics.
VALUATION_COLUMNS = [
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "returnOnEquity",
    "grossMargins",
    "operatingMargins",
    "profitMargins",
    "dividendYield",
    "beta",
]


# Global page/bootstrap styling and Plotly theme defaults.
def init_page() -> None:
    st.set_page_config(page_title="Portfolio Command Center", layout="wide")
    template = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Avenir Next, SF Pro Text, Helvetica Neue, sans-serif", color="#1f2637"),
            margin=dict(t=34, l=8, r=8, b=8),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=True, gridcolor="rgba(110,130,160,0.16)", zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(110,130,160,0.16)", zeroline=False),
        )
    )
    px.defaults.template = template
    px.defaults.color_discrete_sequence = ["#0B3B66", "#2F855A", "#D69E2E", "#C53030", "#4A5568", "#2B6CB0"]
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(1000px 420px at 8% -12%, #edf5ef 0%, rgba(237, 245, 239, 0) 62%),
                    radial-gradient(920px 420px at 92% -10%, #edf1f8 0%, rgba(237, 241, 248, 0) 62%),
                    #f7f9fc;
            }
            .main .block-container {
                max-width: 1480px;
                padding-top: 1.05rem;
                padding-bottom: 2.2rem;
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #f5f7fb 0%, #f1f4f9 100%);
                border-right: 1px solid #e3e9f2;
            }
            [data-testid="stSidebar"] .stRadio > div {
                border: 1px solid #e5eaf2;
                border-radius: 12px;
                padding: 8px;
                background: rgba(255,255,255,0.72);
            }
            .hero-title {
                font-size: 2.1rem;
                font-weight: 700;
                color: #111827;
                margin-bottom: 0.2rem;
                letter-spacing: 0.1px;
            }
            .hero-sub {
                color: #4b5568;
                margin-bottom: 0.7rem;
            }
            [data-testid="stMetric"] {
                border: 1px solid #e5eaf2;
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.88);
                padding: 8px 10px;
            }
            [data-testid="stDataFrame"] > div {
                border: 1px solid #e5eaf2;
                border-radius: 12px;
                overflow: hidden;
            }
            [data-testid="stPlotlyChart"] > div {
                border: 1px solid #e5eaf2;
                border-radius: 12px;
                background: rgba(255,255,255,0.75);
                padding: 4px;
            }
            [data-testid="stMetricLabel"] {
                font-weight: 500;
                letter-spacing: 0.01em;
            }
            [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {
                margin-top: 0.2rem;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
            }
            [data-baseweb="select"] > div,
            .stNumberInput > div > div > input,
            .stTextInput > div > div > input {
                border-radius: 10px !important;
                border-color: #d9e2ef !important;
            }
            .section-label {
                font-size: 0.76rem;
                letter-spacing: 0.08em;
                font-weight: 700;
                color: #6b7280;
                text-transform: uppercase;
                margin-top: 0.3rem;
                margin-bottom: 0.2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Centralized chart renderer so visual polish is consistent across all pages.
def chart(fig: go.Figure) -> None:
    for tr in fig.data:
        if tr.type == "scatter" and getattr(tr, "mode", None) and "lines" in tr.mode:
            if tr.line is None:
                tr.line = {}
            if tr.line.width is None:
                tr.line.width = 1.9
            if tr.line.shape is None:
                tr.line.shape = "linear"
        if tr.type == "bar":
            if tr.marker is None:
                tr.marker = {}
            if tr.marker.line is None:
                tr.marker.line = {}
            tr.marker.line.width = 0
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=14, color="#17202f"),
        hoverlabel=dict(bgcolor="#0f172a", font_size=12, font_color="white"),
        modebar=dict(bgcolor="rgba(255,255,255,0.75)"),
    )
    fig.update_xaxes(showline=True, linewidth=1, linecolor="rgba(120,140,170,0.45)", ticks="outside")
    fig.update_yaxes(showline=True, linewidth=1, linecolor="rgba(120,140,170,0.45)", ticks="outside")
    st.plotly_chart(fig, use_container_width=True)


# Small top strip with near-live market index changes.
def render_live_ticker_strip() -> None:
    snap = get_market_snapshot(tuple(MARKET_GROUPS["Global Equity Indices"]))
    if snap.empty:
        return
    snap = snap.sort_values("Symbol")
    chips = []
    for _, row in snap.iterrows():
        sign = "+" if row["1D %"] >= 0 else ""
        color = "#1f7a4f" if row["1D %"] >= 0 else "#b91c1c"
        chips.append(
            f"<span style='display:inline-block;padding:4px 10px;margin:2px 6px 2px 0;border:1px solid #e5eaf2;border-radius:999px;background:#ffffff;'>"
            f"<span style='font-weight:600;color:#0f172a'>{row['Symbol']}</span> "
            f"<span style='color:{color};font-weight:600'>{sign}{row['1D %']:.2f}%</span></span>"
        )
    st.markdown("<div class='section-label'>Live Market Tape</div>", unsafe_allow_html=True)
    st.markdown("".join(chips), unsafe_allow_html=True)


# Browser-side periodic reload for near-live dashboard behavior.
def enable_auto_refresh(seconds: int) -> None:
    components.html(
        f"""
        <script>
          setTimeout(function() {{
            window.parent.location.reload();
          }}, {int(seconds * 1000)});
        </script>
        """,
        height=0,
        width=0,
    )


# Pulls metadata/fundamental dictionary for a ticker.
@st.cache_data(ttl=60)
def get_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


# Latest close price helper with short cache to reduce API calls.
@st.cache_data(ttl=90)
def get_latest_price(ticker: str):
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


# Fetches historical OHLCV time series for plotting and indicators.
@st.cache_data(ttl=180)
def get_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        return hist if isinstance(hist, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# Multi-ticker return matrix builder used across risk/optimizer modules.
@st.cache_data(ttl=300)
def get_returns_data(tickers: tuple, period: str = "1y") -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    try:
        close = yf.download(
            tickers=list(tickers),
            period=period,
            auto_adjust=True,
            progress=False,
            group_by="column",
        )["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(list(tickers)[0])
        returns = close.pct_change().replace([np.inf, -np.inf], np.nan).dropna(how="all")
        return returns.dropna(axis=1, how="all")
    except Exception:
        return pd.DataFrame()


# Fast snapshot of current market symbols and daily percentage moves.
@st.cache_data(ttl=180)
def get_market_snapshot(symbols: tuple) -> pd.DataFrame:
    rows = []
    for s in symbols:
        try:
            hist = yf.Ticker(s).history(period="5d")
            if hist.empty:
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            d1 = ((last / prev) - 1) * 100 if prev else 0.0
            rows.append({"Symbol": s, "Last": last, "1D %": d1})
        except Exception:
            continue
    return pd.DataFrame(rows)


# Headline feed per symbol (best-effort, depends on provider availability).
@st.cache_data(ttl=240)
def get_news(symbol: str):
    try:
        return yf.Ticker(symbol).news or []
    except Exception:
        return []


# Loads saved portfolio positions from local JSON file.
def load_portfolio(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text()).get("portfolio", {})
    except Exception:
        return {}


# Persists portfolio positions to local JSON file.
def save_portfolio(path: Path, portfolio: dict) -> None:
    path.write_text(json.dumps({"portfolio": portfolio}, indent=4))


# Converts raw portfolio dict into analytics-ready holdings dataframe.
def build_holdings_df(portfolio: dict) -> pd.DataFrame:
    rows = []
    for ticker, pos in portfolio.items():
        shares = float(pos.get("shares", 0))
        avg_cost = float(pos.get("avg_cost", 0))
        if shares <= 0 or avg_cost <= 0:
            continue

        price = get_latest_price(ticker)
        if price is None:
            continue

        info = get_info(ticker)
        value = shares * price
        cost = shares * avg_cost
        pnl = value - cost
        ret = ((price / avg_cost) - 1) * 100 if avg_cost > 0 else 0.0

        row = {
            "Ticker": ticker,
            "Name": info.get("longName") or info.get("shortName") or ticker,
            "Sector": info.get("sector", "Unknown"),
            "Industry": info.get("industry", "Unknown"),
            "Country": info.get("country", "Unknown"),
            "Currency": pos.get("currency") or info.get("currency", "N/A"),
            "Shares": shares,
            "Avg Cost": avg_cost,
            "Price": price,
            "Cost": cost,
            "Value": value,
            "Unrealized P/L": pnl,
            "Return %": ret,
            "Market Cap": info.get("marketCap", np.nan),
        }

        for c in VALUATION_COLUMNS:
            row[c] = info.get(c, np.nan)

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    total_value = df["Value"].sum()
    df["Weight %"] = (df["Value"] / total_value * 100).round(3) if total_value > 0 else 0
    return df.sort_values("Value", ascending=False).reset_index(drop=True)


# Weighted average utility that safely ignores missing/invalid values.
def weighted_average(series: pd.Series, weights: pd.Series):
    valid = series.notna() & np.isfinite(series)
    if not valid.any():
        return np.nan
    s = series[valid].astype(float)
    w = weights[valid].astype(float)
    if w.sum() == 0:
        return np.nan
    return float(np.average(s, weights=w))


# Computes portfolio-level weighted valuation and quality ratios.
def valuation_summary(holdings: pd.DataFrame) -> dict:
    w = holdings["Value"] / holdings["Value"].sum()
    return {
        "Weighted Trailing P/E": weighted_average(holdings["trailingPE"], w),
        "Weighted Forward P/E": weighted_average(holdings["forwardPE"], w),
        "Weighted P/B": weighted_average(holdings["priceToBook"], w),
        "Weighted ROE %": weighted_average(holdings["returnOnEquity"] * 100, w),
        "Weighted Gross Margin %": weighted_average(holdings["grossMargins"] * 100, w),
        "Weighted Op Margin %": weighted_average(holdings["operatingMargins"] * 100, w),
        "Weighted Profit Margin %": weighted_average(holdings["profitMargins"] * 100, w),
        "Weighted Dividend Yield %": weighted_average(holdings["dividendYield"] * 100, w),
        "Weighted Beta (Ticker-level)": weighted_average(holdings["beta"], w),
    }


# Concentration diagnostics (Top-N weights, HHI, effective diversification count).
def concentration_metrics(holdings: pd.DataFrame) -> dict:
    w = holdings["Weight %"] / 100
    hhi = float((w.pow(2)).sum())
    effective_n = float(1 / hhi) if hhi > 0 else np.nan
    return {
        "Top 1 %": float(holdings["Weight %"].head(1).sum()),
        "Top 3 %": float(holdings["Weight %"].head(3).sum()),
        "Top 5 %": float(holdings["Weight %"].head(5).sum()),
        "HHI": hhi,
        "Effective N": effective_n,
    }


# Builds weighted portfolio return stream from constituent asset returns.
def portfolio_return_series(holdings: pd.DataFrame, lookback: str) -> pd.Series:
    returns_df = get_returns_data(tuple(holdings["Ticker"].tolist()), period=lookback)
    if returns_df.empty:
        return pd.Series(dtype=float)

    weights = holdings.set_index("Ticker")["Value"] / holdings["Value"].sum()
    cols = [c for c in returns_df.columns if c in weights.index]
    if not cols:
        return pd.Series(dtype=float)

    weighted = returns_df[cols].mul(weights[cols], axis=1).sum(axis=1)
    return weighted.dropna()


# Core risk engine: return/vol metrics, drawdown, VaR/CVaR, beta/alpha, tracking stats.
def compute_risk_metrics(port: pd.Series, bench: pd.Series, rf: float) -> dict | None:
    if port.empty:
        return None

    # Annualized return and volatility from daily return stream.
    ann_factor = 252
    ann_ret = port.mean() * ann_factor
    ann_vol = port.std() * np.sqrt(ann_factor)

    # Downside-only volatility for Sortino ratio.
    downside = port[port < 0]
    downside_vol = downside.std() * np.sqrt(ann_factor) if not downside.empty else np.nan

    # Core risk-adjusted performance ratios.
    sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else np.nan
    sortino = (ann_ret - rf) / downside_vol if pd.notna(downside_vol) and downside_vol > 0 else np.nan

    # Equity curve and drawdown path.
    eq = (1 + port).cumprod()
    cum_ret = float(eq.iloc[-1] - 1) if not eq.empty else np.nan
    dd = eq / eq.cummax() - 1
    max_dd = float(dd.min()) if not dd.empty else np.nan
    calmar = ann_ret / abs(max_dd) if pd.notna(max_dd) and max_dd < 0 else np.nan

    # Historical tail-loss metrics (daily VaR/CVaR).
    var95 = float(port.quantile(0.05))
    var99 = float(port.quantile(0.01))
    cvar95 = float(port[port <= var95].mean()) if (port <= var95).any() else np.nan
    cvar99 = float(port[port <= var99].mean()) if (port <= var99).any() else np.nan

    # Distribution shape diagnostics.
    skew = float(port.skew())
    kurt = float(port.kurt())

    beta = np.nan
    alpha = np.nan
    tracking_error = np.nan
    info_ratio = np.nan

    if not bench.empty:
        aligned = pd.concat([port, bench], axis=1).dropna()
        if len(aligned) > 2:
            p = aligned.iloc[:, 0]
            b = aligned.iloc[:, 1]
            b_var = b.var()
            if b_var > 0:
                # CAPM-style market sensitivity and alpha estimate.
                beta = p.cov(b) / b_var
                bench_ann = b.mean() * ann_factor
                alpha = ann_ret - (rf + beta * (bench_ann - rf))
            # Active risk/return vs benchmark.
            active = p - b
            tracking_error = active.std() * np.sqrt(ann_factor) if active.std() > 0 else np.nan
            info_ratio = (active.mean() * ann_factor) / tracking_error if pd.notna(tracking_error) and tracking_error > 0 else np.nan

    return {
        "Cumulative Return %": cum_ret * 100,
        "Annual Return %": ann_ret * 100,
        "Annual Volatility %": ann_vol * 100,
        "Downside Volatility %": downside_vol * 100 if pd.notna(downside_vol) else np.nan,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Calmar Ratio": calmar,
        "Max Drawdown %": max_dd * 100,
        "Daily VaR 95% %": var95 * 100,
        "Daily CVaR 95% %": cvar95 * 100,
        "Daily VaR 99% %": var99 * 100,
        "Daily CVaR 99% %": cvar99 * 100,
        "Skewness": skew,
        "Excess Kurtosis": kurt,
        "Beta vs Benchmark": beta,
        "Jensen Alpha %": alpha * 100 if pd.notna(alpha) else np.nan,
        "Tracking Error %": tracking_error * 100 if pd.notna(tracking_error) else np.nan,
        "Information Ratio": info_ratio,
        "Drawdown Series": dd,
        "Equity Curve": eq,
    }


# Monte Carlo efficient frontier approximation for educational optimization visuals.
def optimize_random_frontier(returns_df: pd.DataFrame, n_portfolios: int = 4000, rf: float = 0.04):
    if returns_df.empty or returns_df.shape[1] < 2:
        return pd.DataFrame(), None, None

    # Expected annual returns and covariance matrix.
    mu = returns_df.mean().values * 252
    cov = returns_df.cov().values * 252
    n = returns_df.shape[1]

    # Randomly sample valid weight vectors and compute (return, vol, Sharpe).
    results = []
    for _ in range(n_portfolios):
        w = np.random.random(n)
        w = w / w.sum()
        r = float(np.dot(w, mu))
        v = float(np.sqrt(np.dot(w.T, np.dot(cov, w))))
        s = (r - rf) / v if v > 0 else np.nan
        results.append({"Return": r, "Volatility": v, "Sharpe": s, "Weights": w})

    df = pd.DataFrame(results)
    if df.empty:
        return df, None, None

    # Pick representative frontier candidates.
    max_sharpe = df.loc[df["Sharpe"].idxmax()]
    min_vol = df.loc[df["Volatility"].idxmin()]
    return df, max_sharpe, min_vol


# Rolling Sharpe time series used for risk regime visualization.
def rolling_sharpe(series: pd.Series, window: int, rf: float) -> pd.Series:
    ann = 252
    roll_mean = series.rolling(window).mean() * ann
    roll_vol = series.rolling(window).std() * np.sqrt(ann)
    return (roll_mean - rf) / roll_vol


# RSI momentum oscillator for the performance page ticker focus panel.
def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.rolling(window).mean()
    ma_down = down.rolling(window).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))


# Sidebar state controller: navigation, risk settings, refresh controls, CRUD forms.
def sidebar_controls() -> tuple[Path, dict, str, str, str, float, bool, int]:
    with st.sidebar:
        st.header("Portfolio Controls")
        file_path = Path(st.text_input("Portfolio JSON", str(DATA_FILE))).expanduser()
        portfolio = load_portfolio(file_path)
        st.caption(f"Positions loaded: {len(portfolio)}")

        st.divider()
        page = st.radio(
            "Workspace",
            [
                "Executive",
                "Exposure",
                "Performance",
                "Risk",
                "Optimizer",
                "Rebalance",
                "Market Intelligence",
            ],
        )

        lookback = st.selectbox("Risk/Return Lookback", ["6mo", "1y", "2y", "5y"], index=1)
        benchmark = st.text_input("Benchmark Symbol", "^GSPC")
        rf = st.number_input("Risk-free rate (annual)", min_value=0.0, max_value=0.25, value=0.04, step=0.005)
        st.markdown("#### Live Data")
        live_refresh = st.toggle("Auto-refresh", value=True, help="Reload dashboard periodically for near-live updates.")
        refresh_sec = int(st.slider("Refresh every (sec)", min_value=10, max_value=180, value=30, step=5))
        if st.button("Refresh now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        with st.expander("Add / Update Position"):
            t = st.text_input("Ticker", key="edit_ticker").strip().upper()
            s = st.number_input("Shares", min_value=0.0, step=1.0, key="edit_shares")
            c = st.number_input("Average Cost", min_value=0.0, step=1.0, key="edit_cost")
            if st.button("Save Position", use_container_width=True):
                if not t or s <= 0 or c <= 0:
                    st.error("Invalid input.")
                else:
                    info = get_info(t)
                    portfolio[t] = {
                        "shares": s,
                        "avg_cost": c,
                        "currency": info.get("currency", "N/A"),
                    }
                    save_portfolio(file_path, portfolio)
                    st.cache_data.clear()
                    st.success(f"Saved {t}")
                    st.rerun()

        with st.expander("Remove Position"):
            if portfolio:
                rem = st.selectbox("Ticker", list(portfolio.keys()), key="remove_ticker")
                if st.button("Remove", use_container_width=True):
                    portfolio.pop(rem, None)
                    save_portfolio(file_path, portfolio)
                    st.cache_data.clear()
                    st.success(f"Removed {rem}")
                    st.rerun()
            else:
                st.info("No positions to remove.")

    return file_path, portfolio, page, lookback, benchmark, rf, live_refresh, refresh_sec


# Top-of-page summary cards and live tape, shared across all workspaces.
def render_header(holdings: pd.DataFrame) -> None:
    total_value = holdings["Value"].sum()
    total_cost = holdings["Cost"].sum()
    total_pl = holdings["Unrealized P/L"].sum()
    total_ret = (total_pl / total_cost * 100) if total_cost > 0 else 0.0

    st.markdown('<div class="hero-title">Portfolio Command Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Full-stack portfolio analytics: risk, volatility, exposures, ratios, optimization, rebalancing, and market intelligence.</div>', unsafe_allow_html=True)
    st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    render_live_ticker_strip()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio Value", f"{total_value:,.2f}")
    c2.metric("Total Cost", f"{total_cost:,.2f}")
    c3.metric("Unrealized P/L", f"{total_pl:,.2f}", f"{total_ret:.2f}%")
    c4.metric("Positions", f"{len(holdings)}")


# Executive workspace: KPI snapshot, allocation map, valuation block.
def render_executive(holdings: pd.DataFrame) -> None:
    st.subheader("Executive Dashboard")

    conc = concentration_metrics(holdings)
    vals = valuation_summary(holdings)

    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Top 1 Weight", f"{conc['Top 1 %']:.2f}%")
    a2.metric("Top 3 Weight", f"{conc['Top 3 %']:.2f}%")
    a3.metric("HHI", f"{conc['HHI']:.3f}")
    a4.metric("Effective N", f"{conc['Effective N']:.2f}")
    a5.metric("Weighted Beta", f"{vals['Weighted Beta (Ticker-level)']:.2f}" if pd.notna(vals['Weighted Beta (Ticker-level)']) else "N/A")

    l1, l2 = st.columns([1.1, 1.0])
    with l1:
        st.dataframe(
            holdings[
                [
                    "Ticker",
                    "Name",
                    "Sector",
                    "Industry",
                    "Value",
                    "Weight %",
                    "Unrealized P/L",
                    "Return %",
                    "Currency",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    with l2:
        tree = px.treemap(
            holdings,
            path=["Sector", "Industry", "Ticker"],
            values="Value",
            color="Weight %",
            color_continuous_scale="Blues",
            title="Capital Allocation Tree",
        )
        tree.update_layout(margin=dict(t=35, l=0, r=0, b=0))
        chart(tree)

    st.markdown("### Portfolio Valuation and Quality Ratios")
    r1, r2, r3, r4 = st.columns(4)
    r5, r6, r7, r8 = st.columns(4)
    r1.metric("Weighted Trailing P/E", f"{vals['Weighted Trailing P/E']:.2f}" if pd.notna(vals['Weighted Trailing P/E']) else "N/A")
    r2.metric("Weighted Forward P/E", f"{vals['Weighted Forward P/E']:.2f}" if pd.notna(vals['Weighted Forward P/E']) else "N/A")
    r3.metric("Weighted P/B", f"{vals['Weighted P/B']:.2f}" if pd.notna(vals['Weighted P/B']) else "N/A")
    r4.metric("Weighted ROE", f"{vals['Weighted ROE %']:.2f}%" if pd.notna(vals['Weighted ROE %']) else "N/A")
    r5.metric("Gross Margin", f"{vals['Weighted Gross Margin %']:.2f}%" if pd.notna(vals['Weighted Gross Margin %']) else "N/A")
    r6.metric("Operating Margin", f"{vals['Weighted Op Margin %']:.2f}%" if pd.notna(vals['Weighted Op Margin %']) else "N/A")
    r7.metric("Profit Margin", f"{vals['Weighted Profit Margin %']:.2f}%" if pd.notna(vals['Weighted Profit Margin %']) else "N/A")
    r8.metric("Dividend Yield", f"{vals['Weighted Dividend Yield %']:.2f}%" if pd.notna(vals['Weighted Dividend Yield %']) else "N/A")


# Exposure workspace: sector/industry/country/currency composition drilldown.
def render_exposure(holdings: pd.DataFrame) -> None:
    st.subheader("Exposure Analytics")

    f1, f2, f3 = st.columns(3)
    sectors = sorted(holdings["Sector"].dropna().unique().tolist())
    pick_sectors = f1.multiselect("Sector", sectors, default=sectors)
    filtered = holdings[holdings["Sector"].isin(pick_sectors)] if pick_sectors else holdings.copy()

    industries = sorted(filtered["Industry"].dropna().unique().tolist())
    pick_ind = f2.multiselect("Sub-industry", industries, default=industries)
    filtered = filtered[filtered["Industry"].isin(pick_ind)] if pick_ind else filtered

    countries = sorted(filtered["Country"].dropna().unique().tolist())
    pick_c = f3.multiselect("Country", countries, default=countries)
    filtered = filtered[filtered["Country"].isin(pick_c)] if pick_c else filtered

    if filtered.empty:
        st.warning("No exposures after filters.")
        return

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.dataframe(
            filtered[
                ["Ticker", "Sector", "Industry", "Country", "Currency", "Weight %", "Value", "Return %"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        sun = px.sunburst(filtered, path=["Sector", "Industry", "Ticker"], values="Value", color="Weight %", color_continuous_scale="Blues")
        sun.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        chart(sun)

    e1, e2, e3 = st.columns(3)
    with e1:
        sec = filtered.groupby("Sector", as_index=False)["Value"].sum()
        sec["Weight %"] = sec["Value"] / sec["Value"].sum() * 100
        fig = px.bar(sec.sort_values("Weight %", ascending=False), x="Sector", y="Weight %", title="Sector Exposure")
        chart(fig)
    with e2:
        ind = filtered.groupby("Industry", as_index=False)["Value"].sum()
        ind["Weight %"] = ind["Value"] / ind["Value"].sum() * 100
        fig = px.bar(ind.sort_values("Weight %", ascending=False).head(15), x="Industry", y="Weight %", title="Top Industry Exposure")
        chart(fig)
    with e3:
        cur = filtered.groupby("Currency", as_index=False)["Value"].sum()
        cur["Weight %"] = cur["Value"] / cur["Value"].sum() * 100
        fig = px.pie(cur, names="Currency", values="Weight %", title="Currency Exposure")
        chart(fig)


# Performance workspace: relative trends + focused ticker technical panel.
def render_performance(holdings: pd.DataFrame) -> None:
    st.subheader("Performance and Trend Analytics")

    p1, p2 = st.columns([1, 1])
    tf = p1.selectbox("Timeframe", list(TIMEFRAME_MAP.keys()), index=5)
    ticker_focus = p2.selectbox("Ticker Focus", holdings["Ticker"].tolist())
    period, interval = TIMEFRAME_MAP[tf]

    series = []
    for t in holdings["Ticker"].tolist():
        hist = get_history(t, period, interval)
        if hist.empty:
            continue
        close = hist["Close"].copy()
        if close.empty or close.iloc[0] == 0:
            continue
        idx = close / close.iloc[0] * 100
        series.append(pd.DataFrame({"Date": idx.index, "Indexed": idx.values, "Ticker": t}))

    if series:
        trend = pd.concat(series, ignore_index=True)
        fig = px.line(trend, x="Date", y="Indexed", color="Ticker", title="Relative Performance (Indexed=100)")
        fig.update_traces(line=dict(width=2.0), line_shape="linear")
        fig.update_layout(margin=dict(t=35, l=0, r=0, b=0))
        chart(fig)

    hf = get_history(ticker_focus, period, interval)
    if hf.empty:
        st.info("No trend/candle data for selected ticker.")
        return

    hf = hf.copy()
    hf["MA20"] = hf["Close"].rolling(20).mean()
    hf["MA50"] = hf["Close"].rolling(50).mean()
    hf["RSI14"] = compute_rsi(hf["Close"], 14)

    c1, c2 = st.columns([1.3, 1])
    with c1:
        cand = go.Figure(
            data=[
                go.Candlestick(
                    x=hf.index,
                    open=hf["Open"],
                    high=hf["High"],
                    low=hf["Low"],
                    close=hf["Close"],
                    name=ticker_focus,
                ),
                go.Scatter(x=hf.index, y=hf["MA20"], mode="lines", name="MA20"),
                go.Scatter(x=hf.index, y=hf["MA50"], mode="lines", name="MA50"),
            ]
        )
        cand.update_traces(selector=dict(type="scatter"), line=dict(width=1.6, shape="linear"))
        cand.update_layout(title=f"{ticker_focus} Price + Moving Averages", margin=dict(t=35, l=0, r=0, b=0), xaxis_rangeslider_visible=False)
        chart(cand)

    with c2:
        rsi = px.line(pd.DataFrame({"Date": hf.index, "RSI": hf["RSI14"]}), x="Date", y="RSI", title="RSI (14)")
        rsi.add_hline(y=70, line_dash="dash")
        rsi.add_hline(y=30, line_dash="dash")
        rsi.update_layout(margin=dict(t=35, l=0, r=0, b=0))
        chart(rsi)


# Risk workspace: full metric panel, rolling diagnostics, correlation and tail events.
def render_risk(holdings: pd.DataFrame, lookback: str, benchmark: str, rf: float) -> None:
    st.subheader("Risk and Volatility Lab")

    p_series = portfolio_return_series(holdings, lookback)
    b_df = get_returns_data((benchmark,), period=lookback)
    b_series = b_df[benchmark] if benchmark in b_df.columns else pd.Series(dtype=float)

    risk = compute_risk_metrics(p_series, b_series, rf)
    if risk is None:
        st.warning("Insufficient return data for risk calculations.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m5, m6, m7, m8 = st.columns(4)
    m9, m10, m11, m12 = st.columns(4)
    m13, m14, m15, m16 = st.columns(4)

    m1.metric("Cumulative Return", f"{risk['Cumulative Return %']:.2f}%")
    m2.metric("Annual Return", f"{risk['Annual Return %']:.2f}%")
    m3.metric("Annual Volatility", f"{risk['Annual Volatility %']:.2f}%")
    m4.metric("Downside Volatility", f"{risk['Downside Volatility %']:.2f}%" if pd.notna(risk['Downside Volatility %']) else "N/A")

    m5.metric("Sharpe", f"{risk['Sharpe Ratio']:.2f}" if pd.notna(risk['Sharpe Ratio']) else "N/A")
    m6.metric("Sortino", f"{risk['Sortino Ratio']:.2f}" if pd.notna(risk['Sortino Ratio']) else "N/A")
    m7.metric("Calmar", f"{risk['Calmar Ratio']:.2f}" if pd.notna(risk['Calmar Ratio']) else "N/A")
    m8.metric("Max Drawdown", f"{risk['Max Drawdown %']:.2f}%")

    m9.metric("VaR 95% (1D)", f"{risk['Daily VaR 95% %']:.2f}%")
    m10.metric("CVaR 95% (1D)", f"{risk['Daily CVaR 95% %']:.2f}%" if pd.notna(risk['Daily CVaR 95% %']) else "N/A")
    m11.metric("VaR 99% (1D)", f"{risk['Daily VaR 99% %']:.2f}%")
    m12.metric("CVaR 99% (1D)", f"{risk['Daily CVaR 99% %']:.2f}%" if pd.notna(risk['Daily CVaR 99% %']) else "N/A")

    m13.metric("Beta vs Benchmark", f"{risk['Beta vs Benchmark']:.2f}" if pd.notna(risk['Beta vs Benchmark']) else "N/A")
    m14.metric("Jensen Alpha", f"{risk['Jensen Alpha %']:.2f}%" if pd.notna(risk['Jensen Alpha %']) else "N/A")
    m15.metric("Tracking Error", f"{risk['Tracking Error %']:.2f}%" if pd.notna(risk['Tracking Error %']) else "N/A")
    m16.metric("Information Ratio", f"{risk['Information Ratio']:.2f}" if pd.notna(risk['Information Ratio']) else "N/A")

    c1, c2 = st.columns([1.2, 1])
    with c1:
        roll_vol = p_series.rolling(21).std() * np.sqrt(252) * 100
        roll_sh = rolling_sharpe(p_series, 63, rf)
        fig1 = px.line(pd.DataFrame({"Date": roll_vol.index, "Vol": roll_vol.values}), x="Date", y="Vol", title="21D Rolling Annualized Volatility")
        fig1.update_layout(margin=dict(t=35, l=0, r=0, b=0))
        chart(fig1)

        fig2 = px.line(pd.DataFrame({"Date": roll_sh.index, "Sharpe": roll_sh.values}), x="Date", y="Sharpe", title="63D Rolling Sharpe")
        fig2.add_hline(y=0, line_dash="dash")
        fig2.update_layout(margin=dict(t=35, l=0, r=0, b=0))
        chart(fig2)

        dd = risk["Drawdown Series"] * 100
        fig3 = px.area(pd.DataFrame({"Date": dd.index, "Drawdown": dd.values}), x="Date", y="Drawdown", title="Drawdown Curve")
        fig3.update_layout(margin=dict(t=35, l=0, r=0, b=0))
        chart(fig3)

    with c2:
        ret_df = get_returns_data(tuple(holdings["Ticker"].tolist()), period=lookback)
        if ret_df.empty or ret_df.shape[1] < 2:
            st.info("Need at least 2 return series for correlation map.")
        else:
            corr = ret_df.corr().round(2)
            heat = px.imshow(corr, text_auto=True, zmin=-1, zmax=1, color_continuous_scale="RdBu", title="Asset Correlation")
            heat.update_layout(margin=dict(t=35, l=0, r=0, b=0))
            chart(heat)

        worst_days = p_series.sort_values().head(10) * 100
        wdf = pd.DataFrame({"Date": worst_days.index, "Portfolio Return %": worst_days.values})
        st.markdown("### Worst 10 Days")
        st.dataframe(wdf, use_container_width=True, hide_index=True)

        st.metric("Skewness", f"{risk['Skewness']:.3f}")
        st.metric("Excess Kurtosis", f"{risk['Excess Kurtosis']:.3f}")


# Optimizer workspace: simulated frontier and candidate weight suggestions.
def render_optimizer(holdings: pd.DataFrame, lookback: str, rf: float) -> None:
    st.subheader("Portfolio Optimizer")

    base_returns = get_returns_data(tuple(holdings["Ticker"].tolist()), period=lookback)
    if base_returns.empty or base_returns.shape[1] < 2:
        st.warning("Need at least 2 assets with return history for optimization.")
        return

    col1, col2 = st.columns([1, 1])
    n_sim = int(col1.slider("Simulation count", min_value=1000, max_value=20000, step=1000, value=5000))
    include = col2.multiselect("Assets in optimization", base_returns.columns.tolist(), default=base_returns.columns.tolist())

    if len(include) < 2:
        st.warning("Select at least 2 assets.")
        return

    ret = base_returns[include].dropna(how="any")
    frontier, max_sharpe, min_vol = optimize_random_frontier(ret, n_portfolios=n_sim, rf=rf)
    if frontier.empty:
        st.warning("Frontier simulation failed.")
        return

    frontier_fig = px.scatter(
        frontier,
        x="Volatility",
        y="Return",
        color="Sharpe",
        color_continuous_scale="Viridis",
        title="Simulated Efficient Frontier",
        labels={"Volatility": "Annual Volatility", "Return": "Annual Return"},
    )

    if max_sharpe is not None:
        frontier_fig.add_trace(go.Scatter(x=[max_sharpe["Volatility"]], y=[max_sharpe["Return"]], mode="markers", marker=dict(size=12), name="Max Sharpe"))
    if min_vol is not None:
        frontier_fig.add_trace(go.Scatter(x=[min_vol["Volatility"]], y=[min_vol["Return"]], mode="markers", marker=dict(size=12), name="Min Vol"))

    frontier_fig.update_layout(margin=dict(t=35, l=0, r=0, b=0))
    chart(frontier_fig)

    w1, w2 = st.columns(2)
    if max_sharpe is not None:
        ms = pd.DataFrame({"Ticker": include, "Weight %": np.array(max_sharpe["Weights"]) * 100})
        ms = ms.sort_values("Weight %", ascending=False)
        with w1:
            st.markdown("### Max Sharpe Weights")
            st.dataframe(ms, use_container_width=True, hide_index=True)
            st.metric("Expected Return", f"{max_sharpe['Return']*100:.2f}%")
            st.metric("Expected Volatility", f"{max_sharpe['Volatility']*100:.2f}%")
            st.metric("Expected Sharpe", f"{max_sharpe['Sharpe']:.2f}")

    if min_vol is not None:
        mv = pd.DataFrame({"Ticker": include, "Weight %": np.array(min_vol["Weights"]) * 100})
        mv = mv.sort_values("Weight %", ascending=False)
        with w2:
            st.markdown("### Min Volatility Weights")
            st.dataframe(mv, use_container_width=True, hide_index=True)
            st.metric("Expected Return", f"{min_vol['Return']*100:.2f}%")
            st.metric("Expected Volatility", f"{min_vol['Volatility']*100:.2f}%")
            st.metric("Expected Sharpe", f"{min_vol['Sharpe']:.2f}")


# Rebalance workspace: target modes, trade plan, turnover and transaction cost estimate.
def render_rebalance(holdings: pd.DataFrame, lookback: str) -> None:
    st.subheader("Rebalance Engine")

    total_val = holdings["Value"].sum()
    cur = holdings[["Ticker", "Sector", "Industry", "Value", "Price", "Weight %"]].copy()

    method = st.radio("Targeting mode", ["Manual", "Equal Weight", "Inverse Volatility"], horizontal=True)
    targets = {}

    if method == "Equal Weight":
        # Naive baseline: all positions equal.
        eq = 100 / len(cur)
        targets = {t: eq for t in cur["Ticker"]}
    elif method == "Inverse Volatility":
        # Risk parity lite: lower-vol assets receive higher target weight.
        ret = get_returns_data(tuple(cur["Ticker"].tolist()), period=lookback)
        if ret.empty:
            st.warning("Cannot compute volatility targets; falling back to equal weight.")
            eq = 100 / len(cur)
            targets = {t: eq for t in cur["Ticker"]}
        else:
            vols = ret.std() * np.sqrt(252)
            inv = 1 / vols.replace(0, np.nan)
            inv = inv.dropna()
            if inv.empty:
                eq = 100 / len(cur)
                targets = {t: eq for t in cur["Ticker"]}
            else:
                inv_w = inv / inv.sum() * 100
                targets = {t: float(inv_w.get(t, 0.0)) for t in cur["Ticker"]}
    else:
        cols = st.columns(min(4, len(cur)))
        for i, row in cur.iterrows():
            with cols[i % len(cols)]:
                targets[row["Ticker"]] = st.slider(
                    f"{row['Ticker']} target %",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.5,
                    value=float(round(row["Weight %"], 2)),
                    key=f"target_{row['Ticker']}",
                )

    s = sum(targets.values())
    st.write(f"Target sum before normalization: **{s:.2f}%**")
    if s == 0:
        st.error("All targets are zero.")
        return

    norm = {k: v / s * 100 for k, v in targets.items()}
    tx_cost_bps = st.slider("Estimated transaction cost (bps)", min_value=0, max_value=100, value=5)

    rows = []
    gross_turnover = 0.0
    est_cost = 0.0
    for _, row in cur.iterrows():
        t = row["Ticker"]
        # Convert normalized target weights into target position value and trade gap.
        target_val = total_val * norm[t] / 100
        gap = target_val - row["Value"]
        shares = gap / row["Price"] if row["Price"] > 0 else 0
        action = "BUY" if gap > 0 else "SELL" if gap < 0 else "HOLD"
        gross_turnover += abs(gap)
        est_cost += abs(gap) * tx_cost_bps / 10000

        rows.append(
            {
                "Ticker": t,
                "Sector": row["Sector"],
                "Industry": row["Industry"],
                "Current %": row["Weight %"],
                "Target %": norm[t],
                "Action": action,
                "Trade Value": gap,
                "Approx Shares": shares,
            }
        )

    reb = pd.DataFrame(rows).sort_values("Trade Value")
    st.dataframe(reb, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Gross Turnover", f"{gross_turnover:,.2f}")
    c2.metric("Estimated Transaction Cost", f"{est_cost:,.2f}")
    c3.metric("Net Trade Budget", f"{(gross_turnover - est_cost):,.2f}")

    b1, b2 = st.columns(2)
    with b1:
        fig = px.bar(reb, x="Ticker", y="Trade Value", color="Action", title="Trade Plan by Position")
        chart(fig)
    with b2:
        fig = px.bar(reb.groupby("Sector", as_index=False)["Trade Value"].sum(), x="Sector", y="Trade Value", title="Trade Flow by Sector")
        chart(fig)


# Market intelligence workspace: grouped market monitor + live headline stream.
def render_market_intelligence(holdings: pd.DataFrame) -> None:
    st.subheader("Market Intelligence")

    l, r = st.columns([1, 1.2])
    with l:
        g = st.selectbox("Market report group", list(MARKET_GROUPS.keys()))
        snap = get_market_snapshot(tuple(MARKET_GROUPS[g]))
        if snap.empty:
            st.warning("No market snapshot data available.")
        else:
            snap = snap.sort_values("1D %", ascending=False)
            st.dataframe(snap, use_container_width=True, hide_index=True)
            fig = px.bar(snap, x="Symbol", y="1D %", color="1D %", color_continuous_scale="RdYlGn", title=f"{g} Daily Moves")
            chart(fig)

    with r:
        topic = st.selectbox("News topic", list(REPORT_TOPICS.keys()))
        source_mode = st.radio("Source", ["Topic proxy", "Portfolio ticker"], horizontal=True)
        if source_mode == "Portfolio ticker":
            sym = st.selectbox("Ticker", holdings["Ticker"].tolist())
        else:
            sym = REPORT_TOPICS[topic]

        st.markdown(f"### Live Headlines ({sym})")
        items = get_news(sym)
        if not items:
            st.info("No headlines available.")
        else:
            for it in items[:10]:
                title = it.get("title", "Untitled")
                pub = it.get("publisher", "Unknown")
                link = it.get("link", "")
                ts = it.get("providerPublishTime")
                dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""
                st.markdown(f"**{title}**")
                st.caption(f"{pub} | {dt}")
                if link:
                    st.markdown(f"[Open article]({link})")
                summary = it.get("summary", "")
                if summary:
                    st.write(summary)
                st.divider()


# Main app orchestrator: initialize UI, load state, route to selected workspace.
def main() -> None:
    init_page()
    _, portfolio, page, lookback, benchmark, rf, live_refresh, refresh_sec = sidebar_controls()
    if live_refresh:
        enable_auto_refresh(refresh_sec)

    holdings = build_holdings_df(portfolio)
    if holdings.empty:
        st.warning("No valid holdings/prices found. Add positions in the sidebar.")
        return

    render_header(holdings)

    if page == "Executive":
        render_executive(holdings)
    elif page == "Exposure":
        render_exposure(holdings)
    elif page == "Performance":
        render_performance(holdings)
    elif page == "Risk":
        render_risk(holdings, lookback, benchmark, rf)
    elif page == "Optimizer":
        render_optimizer(holdings, lookback, rf)
    elif page == "Rebalance":
        render_rebalance(holdings, lookback)
    elif page == "Market Intelligence":
        render_market_intelligence(holdings)


if __name__ == "__main__":
    main()
