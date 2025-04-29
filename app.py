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
    "XEON.DE": ("Euro-Geldmarkt", "LU0290358497")
}


tickers_3x_unlevered = {
    "VBTC.DE": ("VanEck Bitcoin ETN (1x)", "DE000A28M8D0"),
    "QQQ3.MI": ("WisdomTree NASDAQ 100 3x Daily Leveraged(3x)", "IE00BLRPRL42"),
    "3EML.MI": ("WisdomTree Emerging Markets 3x Daily Leveraged(3x)", "IE00BYTYHN28"),
    "LOIL.MI": ("WisdomTree WTI Crude Oil 2x Daily Leveraged", "JE00BDD9Q840"),
    "TLT5.DE": ("Leverage Shares PLC E (Treasuries 7-10/20+ (5x))", "XS2595672036"),
    "EUS5.MI": ("USD long EUR short (5x)", "JE00BMM1XC77"),
    "3GLD.DE": ("Gold (3x)", "IE00B8HGT870"),
    "XEON.DE": ("Euro-Geldmarkt (1x)", "LU0290358497"),
    "3EUL.MI": ("Euro Stoxx 50 (3x)", "IE00B7SD4R47")
}


tickers_3x = {
    "BTC-USD": ("Bitcoin", "N/A"),
    "XNAS.MI": ("NASDAQ 100", "IE00BMFKG444"),
    "EUNM.DE": ("EM", "IE00B4L5YC18"),
    "CRUD.MI": ("WTI", "GB00B15KXV33"),
    "SXRM.DE": ("Treasuries 7-10/20+", "IE00B3VWN518"),
    "EUR=X": ("USD long EUR short", "N/A"),
    "EURUSD=X": ("USD short EUR long", "N/A"),
    "GC=F": ("Gold", "N/A"),
    "XEON.DE": ("Euro-Geldmarkt", "N/A"),
    "EXW1.DE": ("iShares Core EURO STOXX 50 UCITS ETF (DE)", "DE0005933956"),
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
    cache_key = f"perf_{ticker}"
    # Wenn Daten im Cache und nicht älter als 60 Sek
    if cache_key in cached_data and now - cache_time.get(cache_key, 0) < CACHE_TIMEOUT:
        return cached_data[cache_key]

    try:
        asset = yf.Ticker(ticker)
        daten_150 = asset.history(period="150d")
        if daten_150.empty or len(daten_150) < 2:
            return None

        schluss_preise_150 = daten_150["Close"]
        if schluss_preise_150.empty or len(schluss_preise_150) < 2:
            return None

        sma_150 = schluss_preise_150.mean()
        letzter_schluss_150 = schluss_preise_150.tail(1).values[0]

        def berechne_performance(daten):
            if daten.empty or len(daten) < 2:
                return 0
            first = daten["Close"].head(1).values[0]
            last = daten["Close"].tail(1).values[0]
            return ((last / first) - 1) * 100 if first > 0 else 0

        # Effizienteres Daten holen - einmal alle Daten und dann filtern
        all_data = asset.history(period="9mo")
        if all_data.empty or len(all_data) < 2:
            return None
            
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

        cached_data[cache_key] = daten
        cache_time[cache_key] = now
        return daten

    except Exception as e:
        print(f"Fehler bei {ticker}: {str(e)}")
        return None

# Hilfsfunktion zur Berechnung und Sortierung
def berechne_dataframe(ticker_dict):
    performances = []
    for t in ticker_dict:
        p = performance_berechnen(t, ticker_dict)
        if p is not None:
            performances.append(p)
    
    if not performances:  # Wenn keine Daten verfügbar
        # Leeres DataFrame mit richtigen Spalten zurückgeben
        return pd.DataFrame(columns=["Stellung", "Asset", "Ticker", "1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"])
    
    df = pd.DataFrame(performances, columns=["Asset", "Ticker", "1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"])
    
    # Numerische Werte für Sortierung sichern
    df['Momentum_num'] = df['Momentum']
    df['SMA_num'] = df['Jetzt über SMA in %']
    
    # Formatierung für Anzeige
    df[["1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"]] = df[["1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"]].round(2).astype(str) + '%'
    
    # Assets über SMA finden
    df_above_sma = df[df['SMA_num'] > 0].copy()
    
    # Stellung berechnen
    if not df_above_sma.empty:
        df_above_sma = df_above_sma.sort_values(by='Momentum_num', ascending=False)
        df_above_sma['Stellung'] = range(1, len(df_above_sma) + 1)
        
        # Stellung in Hauptdataframe übertragen
        df['Stellung'] = 'Nein'
        for idx, row in df_above_sma.iterrows():
            df.loc[df['Asset'] == row['Asset'], 'Stellung'] = str(int(row['Stellung']))
    else:
        df['Stellung'] = 'Nein'
    
    # Hilfsspalten entfernen
    df = df.drop(['Momentum_num', 'SMA_num'], axis=1)
    
    # Sortierung nach Stellung (numerisch für die Zahlen)
    df['Stellung_sort'] = df['Stellung'].apply(lambda x: float('inf') if x == 'Nein' else int(x))
    df = df.sort_values('Stellung_sort')
    df = df.drop('Stellung_sort', axis=1)
    
    # Spalten neu anordnen
    df = df[['Stellung', 'Asset', 'Ticker', '1mo', '3mo', '6mo', '9mo', 'Momentum', 'Jetzt über SMA in %']]
    
    return df

# LETSGO Berechnung
def calculate_sma(ticker, period=175):
    try:
        now = time.time()
        cache_key = f"sma_{ticker}_{period}"
        if cache_key in cached_data and now - cache_time.get(cache_key, 0) < CACHE_TIMEOUT:
            return cached_data[cache_key]
            
        stock = yf.Ticker(ticker)
        data = stock.history(period=f"{period}d")
        if data.empty or len(data) < 2:
            return None, None, None
            
        closing_prices = data["Close"]
        sma = closing_prices.mean()
        current = closing_prices.iloc[-1]
        percent = ((current / sma) - 1) * 100
        
        result = (sma, current, percent)
        cached_data[cache_key] = result
        cache_time[cache_key] = now
        return result
    except Exception as e:
        print(f"Fehler bei SMA-Berechnung für {ticker}: {str(e)}")
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
    try:
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
    except Exception as e:
        # Fehlerbehandlung für die Hauptseite
        print(f"Fehler in index route: {str(e)}")
        return render_template('error.html', error=str(e))

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=100)
