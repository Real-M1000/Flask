from flask import Flask, render_template, request, redirect, url_for, session, flash
import yfinance as yf
import pandas as pd
import time
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management

# User credentials
USERS = {
    "GTAA": "LETSGO!",
    "Noah Beyer": "idmuh137!",
    "Jonah Beyer": "Jonah13!"
}

# Cache für yfinance-Daten
cached_data = {}
cache_time = {}
CACHE_TIMEOUT = 60  # Sekunden

tickers_1x = {
    "XNAS.DE": ("Xtrackers Nasdaq 100 UCITS ETF 1C", "IE00BMFKG444"),
    "AW1T.DE": ("UBS ETF (LU) MSCI EMU Value UCITS ETF (EUR) A-acc", "LU0950669845"),
    "SPYX.DE": ("SPDR MSCI Emerging Markets Small Cap UCITS ETF", "IE00B48X4842"),
    "UEQU.DE": ("UBS ETF (IE) CMCI ex-Agriculture SF UCITS ETF (USD) A-acc", "IE00BZ2GV965"),
    "SXRM.DE": ("iShares USD Treasury Bond 7-10yr UCITS ETF (Acc)", "IE00B3VWN518"),
    "B8TC.DE": ("Amundi USD Fed Funds Rate UCITS ETF Acc", "LU1233598447"),
    "4GLD.DE": ("Xetra-Gold", "DE000A0S9GB0"),
    "XEON.DE": ("Euro-Geldmarkt", "N/A (LU0290358497)")
}


tickers_3x_unlevered = {
    "BTC-EUR": ("Bitcoin (1x)", "DE000A28M8D0"),
    "XNAS.DE": ("NASDAQ 100 (3x)", "IE00BLRPRL42"),
    "AMEM.DE": ("EM (3x)", "IE00BYTYHN28"),
    "FCRU.MI": ("WTI (2x)", "JE00BDD9Q840"),
    "SXRM.DE": ("Treasuries 7-10/20+ (5x)", "XS2595672036"),
    "EUR=X": ("USD long EUR short (5x)", "JE00BMM1XC77"),
    "4GLD.DE": ("Gold (3x)", "IE00B8HGT870"),
    "XEON.DE": ("Euro-Geldmarkt (1x)", "LU0290358497"),
    "LYSX.DE": ("Euro Stoxx 50 (3x)", "IE00B7SD4R47")
}


tickers_3x = {
    "VBTC.DE": ("Bitcoin", "N/A"),
    "QQQ3.L": ("NASDAQ 100", "IE00BMFKG444"),
    "3EML.MI": ("EM", "IE00B4L5YC18"),
    "LOIL.L": ("WTI", "GB00B15KXV33"),
    "TLT5.L": ("Treasuries 7-10/20+", "IE00B3VWN518"),
    "JE00BMM1XC77.SG": ("USD long EUR short", "N/A"),
    "3GOL.L": ("Gold", "N/A"),
    "XEON.DE": ("Euro-Geldmarkt", "N/A")
}


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Performance-Funktion mit Cache
def performance_berechnen(ticker, info_dict):
    now = time.time()
    # Wenn Daten im Cache und nicht älter als 60 Sek
    if ticker in cached_data and now - cache_time[ticker] < CACHE_TIMEOUT:
        return cached_data[ticker]

    try:
        asset = yf.Ticker(ticker)
        daten_150 = asset.history(period="150d")
        if daten_150.empty:
            return None

        schluss_preise_150 = daten_150["Close"]
        if schluss_preise_150.empty:
            return None

        sma_150 = schluss_preise_150.mean()
        letzter_schluss_150 = schluss_preise_150.tail(1).values[0]

        def berechne_performance(daten):
            if daten.empty or len(daten) < 2:
                return 0
            first = daten["Close"].head(1).values[0]
            last = daten["Close"].tail(1).values[0]
            return ((last / first) - 1) * 100 if first > 0 else 0

        # jeweils mit kleiner Pause, damit yfinance nicht dichtmacht
        time.sleep(0.2)
        performance_9m = berechne_performance(asset.history(period="9mo"))
        time.sleep(0.2)
        performance_6m = berechne_performance(asset.history(period="6mo"))
        time.sleep(0.2)
        performance_3m = berechne_performance(asset.history(period="3mo"))
        time.sleep(0.2)
        performance_1m = berechne_performance(asset.history(period="1mo"))

        momentum = (performance_1m + performance_3m + performance_6m + performance_9m) / 4
        sma_percent = ((letzter_schluss_150 / sma_150) - 1) * 100

        asset_name, isin = info_dict.get(ticker, (ticker, ""))
        daten = [asset_name, isin, performance_1m, performance_3m, performance_6m, performance_9m, momentum, sma_percent]

        cached_data[ticker] = daten
        cache_time[ticker] = now
        return daten

    except:
        return None

# Hilfsfunktion zur Berechnung und Sortierung
def berechne_dataframe(ticker_dict):
    performances = [p for t in ticker_dict if (p := performance_berechnen(t, ticker_dict)) is not None]
    df = pd.DataFrame(performances, columns=["Asset", "Ticker", "1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"])
    df[["1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"]] = df[["1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"]].round(2).astype(str) + '%'
    df_above_sma = df[df['Jetzt über SMA in %'].str.rstrip('%').astype(float) > 0].copy()
    df_above_sma['Momentum'] = df_above_sma['Momentum'].str.rstrip('%').astype(float)
    df_above_sma.sort_values(by='Momentum', ascending=False, inplace=True)
    df_above_sma['Stellung'] = range(1, len(df_above_sma) + 1)
    df['Stellung'] = df['Asset'].apply(lambda x: df_above_sma.loc[df_above_sma['Asset'] == x, 'Stellung'].values[0] if x in df_above_sma['Asset'].values else "Nein")
    df['Stellung'] = pd.to_numeric(df['Stellung'], errors='coerce')
    df.sort_values(by='Stellung', inplace=True)
    df['Stellung'] = df['Stellung'].apply(lambda x: str(int(x)) if pd.notnull(x) else 'Nein')
    df = df[['Stellung'] + [col for col in df.columns if col != 'Stellung']]
    return df

# LETSGO Berechnung (hier auch mit Cache sinnvoll, wenn's oft aufgerufen wird)
def calculate_sma(ticker, period=175):
    try:
        now = time.time()
        if ticker in cached_data and now - cache_time[ticker] < CACHE_TIMEOUT:
            return cached_data[ticker]
        stock = yf.Ticker(ticker)
        data = stock.history(period=f"{period}d")
        if data.empty:
            return None, None, None
        closing_prices = data["Close"]
        sma = closing_prices.mean()
        current = closing_prices.iloc[-1]
        percent = ((current / sma) - 1) * 100
        cached_data[ticker] = (sma, current, percent)
        cache_time[ticker] = now
        return sma, current, percent
    except:
        return None, None, None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and USERS[username] == password:
            session['user'] = username
            return redirect(url_for('index'))
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # alle DataFrames berechnen
    df_3x = berechne_dataframe(tickers_3x)
    df_3x_unlevered = berechne_dataframe(tickers_3x_unlevered)
    df_1x = berechne_dataframe(tickers_1x)

    # LETSGO Indikator
    tickersap = "^GSPC"
    tickertip = "TIP"
    tickergold = "GC=F"
    sma_sap, current_sap, percent_sap = calculate_sma(tickersap)
    sma_tip, current_tip, percent_tip = calculate_sma(tickertip)
    sma_gold, current_gold, percent_gold = calculate_sma(tickergold)

    if sma_sap is None or sma_tip is None or sma_gold is None:
        result = "Daten nicht verfügbar"
    else:
        if current_sap <= sma_sap or current_tip <= sma_tip:
            result = "Gold" if current_gold > sma_gold else "Cash"
        else:
            result = "Buy"

    data_letsgo = []
    if sma_sap is not None:
        data_letsgo.append(["S&P 500", f"{current_sap:.2f}", f"{sma_sap:.2f}", f"{percent_sap:.2f}%"])
    if sma_tip is not None:
        data_letsgo.append(["TIPS", f"{current_tip:.2f}", f"{sma_tip:.2f}", f"{percent_tip:.2f}%"])
    if sma_gold is not None:
        data_letsgo.append(["Gold", f"{current_gold:.2f}", f"{sma_gold:.2f}", f"{percent_gold:.2f}%"])

    return render_template('index.html',
                           df_3x=df_3x.to_html(classes="table table-bordered", index=False),
                           df_3x_unlevered=df_3x_unlevered.to_html(classes="table table-bordered", index=False),
                           df_1x=df_1x.to_html(classes="table table-bordered", index=False),
                           data_letsgo=data_letsgo,
                           result=result,
                           username=session['user'])

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=100)
