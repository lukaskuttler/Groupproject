#Author: Diogo Terra Simões da Motta - 2nd Year BIE
#Course: Programming for Economists II
import yfinance as yf
import matplotlib.pyplot as plt


# ---------------------------
# MENU
# ---------------------------
def print_menu():
    """
    Prints the main portfolio menu
    :return: None
    """
    print("\n==== PORTFOLIO MANAGER ====")
    print("1) Manage holdings")
    print("2) Portfolio summary")
    print("3) Rebalance suggestions")
    print("4) View stock info from holdings")
    print("5) Trendline price chart (multiple timeframes)")
    print("0) Exit")


# ---------------------------
# BASIC TICKER INFO
# ---------------------------
def show_basic_ticker_info(ticker):
    """
    Fetches and prints basic info about a ticker and checks if it is valid
    :param ticker: stock symbol entered by the user
    :return: True if ticker is valid, False otherwise
    """
    try:
        tk = yf.Ticker(ticker)

        info = tk.info  # dict with company data
        exchange = info.get("exchange", "N/A")
        currency = info.get("currency", "N/A")

        hist = tk.history(period="1d") # fetching recent price history, only need 1d
        if hist.empty: # checking if yahoo returned any data
            print("\nWarning: No price data found.")
            print("Ticker may be invalid, delisted, or require a suffix (e.g., .SA, .L, .PA).")
            return False
        else:
            price = float(hist["Close"].iloc[-1]) # selecting close column, and returning the last ROW

        print("\n--- Ticker info ---")
        print("Exchange:", exchange)
        print("Currency:", currency)
        print(f"Current price: {price:.2f}")
        print("-------------------\n")
        return True

    except Exception: # fetching exceptions which are not user errors
        print("Could not fetch ticker info.")
        return False


# ---------------------------
# HOLDINGS
# portfolio = {"AAPL": {"shares": 5.0, "avg_cost": 150.0}, ...}
# ---------------------------
def manage_holdings(portfolio):
    """
    Lets the user add, update, remove and view holdings
    :param portfolio: dictionary with the current portfolio positions
    :return: None
    """
    while True:
        print("\n-- Manage holdings --")
        print("1) Add/Update holding")
        print("2) Remove holding")
        print("3) View holdings")
        print("0) Back")
        choice = input("Choose: ").strip()

        if choice == "1": # add or update/overwrite tickers
            ticker = input("Ticker (e.g., AAPL): ").strip().upper()
            if ticker == "":
                print("Ticker cannot be empty.")
                continue # restarts loop

            # show basic info after ticker is entered; if False, it skips saving and restarts while loop
            if show_basic_ticker_info(ticker) == False:
                continue #restarts loop if False

            try:
                shares = float(input("Shares: ").strip())
                avg_cost = float(input("Average cost per share: ").strip())
            except ValueError:
                print("Invalid number.")
                continue

            if shares <= 0 or avg_cost <= 0:
                print("Shares and avg_cost must be > 0.")
                continue

            portfolio[ticker] = {"shares": shares, "avg_cost": avg_cost}
            print("Saved:", ticker)

        elif choice == "2": # removing tickers
            ticker = input("Ticker to remove: ").strip().upper()
            if ticker in portfolio:
                del portfolio[ticker]
                print("Removed:", ticker)
            else:
                print("Not found.")

        elif choice == "3": # viewing tickers
            if len(portfolio) == 0:
                print("Portfolio is empty.")
            else:
                for t in portfolio:
                    info = portfolio[t]
                    print(f"{t}: {info['shares']} shares @ avg cost {info['avg_cost']}")

        elif choice == "0": # back option
            break
        else:
            print("Invalid option.")


# ---------------------------
# PRICES
# simplest possible: fetch each ticker one by one, if not, user inputs prices manually
# ---------------------------
def fetch_prices(tickers):
    """
    Fetches the latest price for each ticker from Yahoo Finance
    :param tickers: list of ticker symbols
    :return: dictionary mapping each ticker to its latest price (or None)
    """
    prices = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if hist.empty:
                prices[t] = None # if price cannot be found, None is assigned to the ticker's price, which will be altered later
            else:
                prices[t] = float(hist["Close"].iloc[-1]) # price was already found
        except Exception:
            prices[t] = None
    return prices


def manual_fix_prices(prices):
    """
    Asks the user to manually input prices that could not be fetched, making sure that all tickers have prices
    :param prices: dictionary of ticker prices (some may be None)
    :return: updated dictionary with valid prices
    """
    fixed = {}
    for t in prices:
        p = prices[t]
        if p is not None: # these are the prices that were already found
            fixed[t] = p
        else:
            while True:
                try:
                    val = float(input(f"Couldn't fetch {t}. Enter price manually: ").strip())
                    if val <= 0:
                        print("Price must be > 0.")
                        continue
                    fixed[t] = val
                    break # leaves the while loop and moves onto the next ticker
                except ValueError:
                    print("Invalid number.")
    return fixed


# ---------------------------
# STOCK INFO
# ---------------------------
def view_stock_info_from_holdings(portfolio):
    """
    Shows detailed company information for a selected holding
    :param portfolio: dictionary of current holdings
    :return: None
    """
    if len(portfolio) == 0:
        print("\nPortfolio is empty. Add holdings first.")
        return

    tickers = list(portfolio.keys()) # extracting all tickers into one list

    print("\n-- Available holdings --")
    for i in range(len(tickers)):
        print(f"{i+1}) {tickers[i]}")
    print("0) Back")

    choice = input("Choose a stock number: ").strip()

    if choice == "0":
        return

    try:
        i_stock = int(choice) - 1
    except ValueError:
        print("Invalid option.")
        return

    if i_stock < 0 or i_stock >= len(tickers):
        print("Invalid option.")
        return
    else:
        ticker = tickers[i_stock]
        print(f"\nFetching info for {ticker}...")

    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        # price (also validates data exists)
        hist = tk.history(period="1d")
        if hist.empty:
            print("No price data found for this ticker right now.")
            return
        else:
            price = float(hist["Close"].iloc[-1])

        # company basics
        name = info.get("longName") or info.get("shortName") or "N/A" # first one that == True
        country = info.get("country", "N/A")
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        exchange = info.get("exchange", "N/A")
        currency = info.get("currency", "N/A")

        # financials
        market_cap = info.get("marketCap") # returns None if it doesn't exist
        revenue = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")

        # ratios / margins
        pe = info.get("trailingPE")
        pb = info.get("priceToBook")
        roe = info.get("returnOnEquity")
        gross_margin = info.get("grossMargins")
        op_margin = info.get("operatingMargins")
        profit_margin = info.get("profitMargins")

        print("\n===== STOCK INFO =====")
        print("Ticker:", ticker)
        print("Name:", name)
        print("Country:", country)
        print("Sector:", sector)
        print("Industry:", industry)
        print("Exchange:", exchange)
        print("Currency:", currency)
        print(f"Current price: {price:.2f}")

        print("\n--- Size & financials ---")

        if market_cap is not None:
            print("Market cap:", f"{market_cap:,.0f}")
        else:
            print("Market cap: N/A")

        if revenue is not None:
            print("Revenue (TTM):", f"{revenue:,.0f}")
        else:
            print("Revenue (TTM): N/A")

        if net_income is not None:
            print("Net income (TTM):", f"{net_income:,.0f}")
        else:
            print("Net income (TTM): N/A")

        print("\n--- Ratios & margins ---")

        if pe is not None:
            print("P/E (TTM):", f"{pe:.2f}")
        else:
            print("P/E (TTM): N/A")

        if pb is not None:
            print("P/B:", f"{pb:.2f}")
        else:
            print("P/B: N/A")

        if roe is not None:
            print("ROE:", f"{roe * 100:.2f}%")
        else:
            print("ROE: N/A")

        if gross_margin is not None:
            print("Gross margin:", f"{gross_margin * 100:.2f}%")
        else:
            print("Gross margin: N/A")

        if op_margin is not None:
            print("Operating margin:", f"{op_margin * 100:.2f}%")
        else:
            print("Operating margin: N/A")

        if profit_margin is not None:
            print("Profit margin:", f"{profit_margin * 100:.2f}%")
        else:
            print("Profit margin: N/A")

        print("======================\n")

    except Exception:
        print("Could not fetch company info right now.")


def plot_price_trend_from_holdings(portfolio):
    """
    Plots a simple trendline chart of a selected holding's price.
    :param portfolio: dictionary of holdings
    :return: None
    """
    if len(portfolio) == 0:
        print("\nPortfolio is empty. Add holdings first.")
        return

    tickers = list(portfolio.keys())

    print("\n-- Available holdings --")
    for i in range(len(tickers)):
        print(f"{i+1}) {tickers[i]}")
    print("0) Back")

    choice = input("Choose a stock number: ").strip()
    if choice == "0":
        return

    try:
        i_stock = int(choice) - 1
    except ValueError:
        print("Invalid option.")
        return

    if i_stock < 0 or i_stock >= len(tickers):
        print("Invalid option.")
        return

    ticker = tickers[i_stock]

    print("\nChoose a timeframe:")
    print("1) 1w")
    print("2) 1m")
    print("3) ytd")
    print("4) 1y")
    print("5) 2y")
    print("6) 5y")
    print("7) 10y")
    print("8) all")
    tf = input("Choose: ").strip()

    # timeframe mapping (simple and stable)
    if tf == "1":
        period = "5d"
        interval = "1h"
        title_tf = "1 Week"
    elif tf == "2":
        period = "1mo"
        interval = "1d"
        title_tf = "1 Month"
    elif tf == "3":
        period = "ytd"
        interval = "1d"
        title_tf = "YTD"
    elif tf == "4":
        period = "1y"
        interval = "1wk"
        title_tf = "1 Year"
    elif tf == "5":
        period = "2y"
        interval = "1wk"
        title_tf = "2 Years"
    elif tf == "6":
        period = "5y"
        interval = "1wk"
        title_tf = "5 Years"
    elif tf == "7":
        period = "10y"
        interval = "1mo"
        title_tf = "10 Years"
    elif tf == "8":
        period = "max"
        interval = "1mo"
        title_tf = "All Time"
    else:
        print("Invalid option.")
        return

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period, interval=interval)

        if hist.empty:
            print("No price data found for this timeframe.")
            return

        dates = hist.index
        closes = hist["Close"]

        plt.figure()
        plt.plot(dates, closes)
        plt.title(f"{ticker} Price Trend ({title_tf})")
        plt.xlabel("Date")
        plt.ylabel("Close Price")
        plt.xticks(rotation=30)
        plt.tight_layout()
        plt.show()

    except Exception:
        print("Could not fetch or plot price data right now.")


# ---------------------------
# SUMMARY
# ---------------------------
def portfolio_summary(portfolio):
    """
    Computes and prints the portfolio valuation and unrealized P/L
    :param portfolio: dictionary of holdings
    :return: None
    """
    if len(portfolio) == 0:
        print("\nPortfolio is empty. Add holdings first.")
        return

    tickers = []
    for t in portfolio:
        tickers.append(t)

    prices = fetch_prices(tickers)
    prices = manual_fix_prices(prices)

    total_value = 0.0
    total_cost = 0.0
    total_unreal = 0.0
    rows = []

    for t in tickers:
        shares = portfolio[t]["shares"]
        avg_cost = portfolio[t]["avg_cost"]
        price = prices[t]

        value = shares * price
        cost = shares * avg_cost
        unreal = (price - avg_cost) * shares

        # unrealized % for each position
        if avg_cost > 0:
            unreal_pct = ((price - avg_cost) / avg_cost) * 100
        else:
            unreal_pct = 0.0

        total_value = total_value + value
        total_cost = total_cost + cost
        total_unreal = total_unreal + unreal

        rows.append([t, shares, avg_cost, price, value, unreal, unreal_pct])

    # total unrealized % (based on total cost)
    if total_cost > 0:
        total_unreal_pct = (total_unreal / total_cost) * 100
    else:
        total_unreal_pct = 0.0

    print("\n===== PORTFOLIO SUMMARY =====")
    print(f"Total value: {total_value:.2f}")
    print(f"Total unrealized P/L: {total_unreal:.2f} ({total_unreal_pct:.2f}%)\n")

    print(f"{'Ticker':<8} {'Shares':>10} {'AvgCost':>10} {'Price':>10} {'Value':>12}"
          f" {'Unreal P/L':>12} {'Unreal P/L (%)':>10} {'Weight':>8}")
    print("-" * 96)

    best_t = None
    best_pl = None
    worst_t = None
    worst_pl = None

    for r in rows:
        t, shares, avg_cost, price, value, unreal, unreal_pct = r  # assigning name to each value

        if total_value > 0:
            weight = (value / total_value) * 100
        else:
            weight = 0

        print(f"{t:<8} {shares:>10.2f} {avg_cost:>10.2f} {price:>10.2f} {value:>12.2f}"
              f" {unreal:>12.2f} {unreal_pct:>9.2f}% {weight:>7.2f}%")

        if best_pl is None or unreal > best_pl:
            best_pl = unreal
            best_t = t
        if worst_pl is None or unreal < worst_pl:
            worst_pl = unreal
            worst_t = t

    print("\nBiggest winner (unrealized):", best_t, f"{best_pl:.2f}")
    print("Biggest loser  (unrealized):", worst_t, f"{worst_pl:.2f}")


# ---------------------------
# REBALANCE
# ---------------------------
def rebalance_suggestions(portfolio):
    """
    Suggests buy/sell amounts to reach target portfolio weights
    :param portfolio: dictionary of holdings
    :return: None
    """
    if len(portfolio) == 0:
        print("Portfolio is empty.")
        return

    tickers = []
    for t in portfolio:
        tickers.append(t)

    prices = fetch_prices(tickers)
    prices = manual_fix_prices(prices)

    total_value = 0.0
    values = {}
    for t in tickers:
        v = portfolio[t]["shares"] * prices[t]
        values[t] = v
        total_value += v

    print("\nEnter target weights in % for each ticker.")
    print("Example: if you want 50%, type 50")

    targets = {}
    total_w = 0.0

    for t in tickers:
        while True:
            try:
                w = float(input(f"Target weight for {t} (in %): ").strip())
                if w < 0:
                    print("Weight must be >= 0.")
                    continue
                targets[t] = w
                total_w += w
                break
            except ValueError:
                print("Invalid number.")

    if total_w == 0: # error handling, because total weight (denominator) cannot be zero
        print("All weights are 0. Nothing to do.")
        return

    # normalize to sum to 100
    for t in targets:
        targets[t] = (targets[t] / total_w) * 100

    print("\n===== REBALANCE SUGGESTIONS =====")
    print(f"Total portfolio value: {total_value:.2f}")
    print("Targets normalized to sum to 100%.\n")

    for t in tickers:
        current_val = values[t]
        target_val = (targets[t] / 100) * total_value
        gap = target_val - current_val

        price = prices[t]

        if gap > 0:
            if price > 0:
                shares_to_buy = gap / price
            else:
                shares_to_buy = 0
            print(f"{t}: BUY about {gap:.2f} worth (about {shares_to_buy:.2f} shares)")
        elif gap < 0:
            sell_amount = abs(gap)
            if price > 0:
                shares_to_sell = sell_amount / price
            else:
                shares_to_sell = 0
            print(f"{t}: SELL about {sell_amount:.2f} worth (about {shares_to_sell:.2f} shares)")
        else:
            print(f"{t}: already on target")


# ---------------------------
# MAIN
# ---------------------------
def main():
    """
    Runs the main portfolio manager loop
    :return: None
    """
    portfolio = {}

    while True:
        print_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            manage_holdings(portfolio)
        elif choice == "2":
            portfolio_summary(portfolio)
        elif choice == "3":
            rebalance_suggestions(portfolio)
        elif choice == "4":
            view_stock_info_from_holdings(portfolio)
        elif choice == "5":
            plot_price_trend_from_holdings(portfolio)
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__": #ChatGPT recommended this instead of just main()
    main()

    #so far so good, lets make sure that the code is connected to the data source correctly and that any stock appears. 3
