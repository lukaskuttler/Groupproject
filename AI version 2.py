# ============================================
# PORTFOLIO MANAGER PRO - FULL VERSION
# Author: Diogo Terra Simões da Motta, Lukas Kuttler
# Course: Programming for Economists II
# ============================================

import yfinance as yf
import matplotlib.pyplot as plt
import json
import os
import datetime
import numpy as np

from reportlab.platypus i
mport (
    (SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image, PageBreak)
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


# ==========================================================
# ------------------ PORTFOLIO STORAGE ---------------------
# ==========================================================

PORTFOLIO_FILE = "portfolio.json"


def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f)


def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {}


# ==========================================================
# ---------------------- MENU ------------------------------
# ==========================================================

def print_menu():
    print("\n==== PORTFOLIO MANAGER PRO ====")
    print("1) Manage holdings")
    print("2) Portfolio summary")
    print("3) Rebalance suggestions")
    print("4) View stock info")
    print("5) Trendline chart")
    print("6) Portfolio vs S&P500")
    print("7) Download full PDF report")
    print("0) Exit")


# ==========================================================
# -------------------- DATA FETCHING -----------------------
# ==========================================================

def fetch_prices(tickers):
    prices = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if hist.empty:
                prices[t] = None
            else:
                prices[t] = float(hist["Close"].iloc[-1])
        except Exception:
            prices[t] = None
    return prices


def manual_fix_prices(prices):
    for t in prices:
        if prices[t] is None:
            while True:
                try:
                    val = float(input(f"Enter manual price for {t}: "))
                    if val > 0:
                        prices[t] = val
                        break
                except ValueError:
                    pass
    return prices


# ==========================================================
# -------------------- HOLDINGS ----------------------------
# ==========================================================

def manage_holdings(portfolio):
    while True:
        print("\n-- Manage Holdings --")
        print("1) Add/Update")
        print("2) Remove")
        print("3) View")
        print("0) Back")

        choice = input("Choose: ")

        if choice == "1":
            ticker = input("Ticker: ").upper()
            shares = float(input("Shares: "))
            avg_cost = float(input("Avg cost: "))
            portfolio[ticker] = {"shares": shares, "avg_cost": avg_cost}
            save_portfolio(portfolio)
            print("Saved.")

        elif choice == "2":
            ticker = input("Ticker to remove: ").upper()
            if ticker in portfolio:
                del portfolio[ticker]
                save_portfolio(portfolio)
                print("Removed.")

        elif choice == "3":
            print(portfolio)

        elif choice == "0":
            break


# ==========================================================
# ----------------- PORTFOLIO SUMMARY ----------------------
# ==========================================================

def portfolio_summary(portfolio):
    if not portfolio:
        print("Portfolio empty.")
        return

    tickers = list(portfolio.keys())
    prices = manual_fix_prices(fetch_prices(tickers))

    total_value = 0
    total_cost = 0

    print("\n===== SUMMARY =====")

    for t in tickers:
        shares = portfolio[t]["shares"]
        avg_cost = portfolio[t]["avg_cost"]
        price = prices[t]

        value = shares * price
        cost = shares * avg_cost
        unreal = value - cost

        total_value += value
        total_cost += cost

        print(f"{t} | Value: {value:.2f} | Unrealized: {unreal:.2f}")

    total_unreal = total_value - total_cost
    print("\nTotal Value:", round(total_value, 2))
    print("Total Unrealized:", round(total_unreal, 2))

    # Risk Metrics
    returns = get_portfolio_returns(portfolio)
    if returns is not None:
        vol = np.std(returns) * np.sqrt(252)
        sharpe = (np.mean(returns) * 252) / vol if vol != 0 else 0
        print("Annual Volatility:", round(vol, 4))
        print("Sharpe Ratio:", round(sharpe, 4))


# ==========================================================
# -------------------- RISK METRICS ------------------------
# ==========================================================

def get_portfolio_returns(portfolio):
    if not portfolio:
        return None

    tickers = list(portfolio.keys())
    data = yf.download(tickers, period="1y")["Close"]

    if isinstance(data, np.ndarray):
        return None

    data = data.dropna()
    returns = data.pct_change().dropna()

    weights = []
    total_value = 0

    prices = manual_fix_prices(fetch_prices(tickers))

    for t in tickers:
        total_value += portfolio[t]["shares"] * prices[t]

    for t in tickers:
        weight = (portfolio[t]["shares"] * prices[t]) / total_value
        weights.append(weight)

    weighted_returns = returns.dot(weights)

    return weighted_returns


# ==========================================================
# -------------------- REBALANCE ---------------------------
# ==========================================================

def rebalance_suggestions(portfolio):
    if not portfolio:
        print("Empty.")
        return

    tickers = list(portfolio.keys())
    prices = manual_fix_prices(fetch_prices(tickers))

    total_value = sum(portfolio[t]["shares"] * prices[t] for t in tickers)

    print("Enter target weights (%):")

    targets = {}
    for t in tickers:
        targets[t] = float(input(f"{t}: "))

    total_target = sum(targets.values())
    for t in targets:
        targets[t] = targets[t] / total_target

    print("\n--- Suggestions ---")

    for t in tickers:
        current_value = portfolio[t]["shares"] * prices[t]
        target_value = targets[t] * total_value
        diff = target_value - current_value

        if diff > 0:
            print(f"{t}: BUY {diff:.2f}")
        else:
            print(f"{t}: SELL {abs(diff):.2f}")


# ==========================================================
# ------------------- STOCK INFO ---------------------------
# ==========================================================

def view_stock_info(portfolio):
    ticker = input("Ticker: ").upper()
    tk = yf.Ticker(ticker)
    info = tk.info
    print("Name:", info.get("longName"))
    print("Sector:", info.get("sector"))
    print("Market Cap:", info.get("marketCap"))


# ==========================================================
# ----------------- TRENDLINE CHART ------------------------
# ==========================================================

def plot_trend():
    ticker = input("Ticker: ").upper()
    data = yf.Ticker(ticker).history(period="1y")

    plt.plot(data.index, data["Close"])
    plt.title(f"{ticker} - 1 Year")
    plt.xticks(rotation=30)
    plt.show()


# ==========================================================
# --------- PORTFOLIO VS S&P 500 COMPARISON ---------------
# ==========================================================

def portfolio_vs_sp500(portfolio):
    returns = get_portfolio_returns(portfolio)
    if returns is None:
        return

    sp = yf.download("^GSPC", period="1y")["Close"].pct_change().dropna()

    cumulative_port = (1 + returns).cumprod()
    cumulative_sp = (1 + sp).cumprod()

    plt.plot(cumulative_port, label="Portfolio")
    plt.plot(cumulative_sp, label="S&P 500")
    plt.legend()
    plt.title("Portfolio vs S&P500")
    plt.show()


# ==========================================================
# ---------------- PDF REPORT GENERATION -------------------
# ==========================================================

def generate_pdf_report(portfolio):
    if not portfolio:
        print("Portfolio empty.")
        return

    filename = "Portfolio_Report.pdf"
    doc = SimpleDocTemplate(filename)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("PORTFOLIO REPORT", styles["Heading1"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(str(datetime.date.today()), styles["Normal"]))
    elements.append(PageBreak())

    tickers = list(portfolio.keys())
    prices = manual_fix_prices(fetch_prices(tickers))

    table_data = [["Ticker", "Shares", "Price", "Value"]]
    total_value = 0

    for t in tickers:
        value = portfolio[t]["shares"] * prices[t]
        total_value += value
        table_data.append([
            t,
            str(portfolio[t]["shares"]),
            str(prices[t]),
            str(round(value, 2))
        ])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black)
    ]))

    elements.append(table)
    elements.append(PageBreak())

    # Pie Chart
    values = [portfolio[t]["shares"] * prices[t] for t in tickers]
    plt.figure()
    plt.pie(values, labels=tickers, autopct="%1.1f%%")
    plt.title("Allocation")
    plt.savefig("allocation.png")
    plt.close()

    elements.append(Image("allocation.png", width=5 * inch, height=5 * inch))
    elements.append(PageBreak())

    elements.append(Paragraph("Risk Disclaimer", styles["Heading2"]))
    elements.append(Paragraph(
        "This report is for informational purposes only. "
        "Past performance does not guarantee future results.",
        styles["Normal"]
    ))

    doc.build(elements)

    os.remove("allocation.png")

    print("PDF report generated.")


# ==========================================================
# ------------------------- MAIN ---------------------------
# ==========================================================

def main():
    portfolio = load_portfolio()

    while True:
        print_menu()
        choice = input("Choose: ")

        if choice == "1":
            manage_holdings(portfolio)
        elif choice == "2":
            portfolio_summary(portfolio)
        elif choice == "3":
            rebalance_suggestions(portfolio)
        elif choice == "4":
            view_stock_info(portfolio)
        elif choice == "5":
            plot_trend()
        elif choice == "6":
            portfolio_vs_sp500(portfolio)
        elif choice == "7":
            generate_pdf_report(portfolio)
        elif choice == "0":
            break


if __name__ == "__main__":
    main()