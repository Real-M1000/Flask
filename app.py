from flask import Flask, render_template
import yfinance as yf
import pandas as pd
from tabulate import tabulate

app = Flask(__name__)

# 3x GTAA Ticker mit Name und ISIN
tickers_3x = {
    "BTC-EUR": ("Bitcoin EUR", "N/A"),
    "XEON.DE": ("Cash", "LU1955962902"),
    "EUR=X": ("USD in EUR", "N/A"),
    "XNAS.DE": ("Nasdaq 100", "LU1681047309"),
    "4GLD.DE": ("Gold", "DE000A0N62G0"),
    "FCRU.MI": ("Öl", "IE00B6R51Z18"),
    "SXRM.DE": ("Treasury Bond", "LU1379946036"),
    "LYSX.DE": ("Euro Stoxx 50", "LU0274211217"),
    "AMEM.DE": ("EM", "IE00B5M4WH52"),
}

# 1x GTAA Ticker mit Name und ISIN
tickers_1x = {
    "XNAS.DE": ("NASDAQ 100", "LU1681047309"),
    "AW1T.DE": ("EMU Value", "DE000A1JXAF0"),
    "SPYX.DE": ("EM SC", "US78468R7476"),
    "UEQU.DE": ("Rohstoffe", "LU1399300455"),
    "SXRM.DE": ("Treasury Bond 7-10yr", "LU1379946036"),
    "FEDF.MI": ("USD Overnight Rate", "LU1659681400"),
    "4GLD.DE": ("Gold", "DE000A0N62G0"),
    "XEON.DE": ("Cash", "LU1955962902")
}



# Performance-Funktion mit Name + ISIN
def performance_berechnen(ticker, info_dict):
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

        performance_9m = berechne_performance(asset.history(period="9mo"))
        performance_6m = berechne_performance(asset.history(period="6mo"))
        performance_3m = berechne_performance(asset.history(period="3mo"))
        performance_1m = berechne_performance(asset.history(period="1mo"))

        momentum = (performance_1m + performance_3m + performance_6m + performance_9m) / 4
        sma_percent = ((letzter_schluss_150 / sma_150) - 1) * 100

        asset_name, isin = info_dict.get(ticker, (ticker, ""))
        return [asset_name, isin, performance_1m, performance_3m, performance_6m, performance_9m, momentum, sma_percent]

    except:
        return None

# Hilfsfunktion zur Berechnung und Sortierung
def berechne_dataframe(ticker_dict):
    performances = [p for t in ticker_dict if (p := performance_berechnen(t, ticker_dict)) is not None]
    df = pd.DataFrame(performances, columns=["Asset", "ISIN", "1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"])
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

# LETSGO Berechnung
def calculate_sma(ticker, period=175):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=f"{period}d")
        if data.empty:
            return None, None, None
        closing_prices = data["Close"]
        sma = closing_prices.mean()
        current = closing_prices.iloc[-1]
        percent = ((current / sma) - 1) * 100
        return sma, current, percent
    except:
        return None, None, None

@app.route('/')
def index():
    df_3x = berechne_dataframe(tickers_3x)
    df_3x_unlevered = berechne_dataframe(tickers_3x_unlevered)
    df_1x = berechne_dataframe(tickers_1x)

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

    return render_template('index.html', df_3x=df_3x.to_html(classes="table table-bordered", index=False),
                           df_1x=df_1x.to_html(classes="table table-bordered", index=False),
                           data_letsgo=data_letsgo, result=result)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=100)
