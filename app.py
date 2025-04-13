from flask import Flask, render_template
import yfinance as yf
import pandas as pd

app = Flask(__name__)

# Ticker-Daten

# 3x GTAA Ticker







tickers_3x = {
    "BTC-EUR": "Bitcoin EUR",
    "XEON.DE": "Cash",
    "EUR=X": "USD in EUR",
    "XNAS.DE": "Nasdaq 100",
    "4GLD.DE": "Gold",
    "FCRU.MI": "Öl",
    "SXRM.DE": "Treasury Bond",
    "LYSX.DE": "Euro Stoxx 50",
    "AMEM.DE": "EM",
}

# 1x GTAA Ticker
tickers_1x = {
    "XNAS.DE": "NASDAQ 100",
    "AW1T.DE": "EMU Value",
    "SPYX.DE": "EM SC",
    "UEQU.DE": "Rohstoffe",
    "SXRM.DE": "Treasury Bond 7-10yr",
    "FEDF.MI": "USD Overnight Rate",
    "4GLD.DE": "Gold",
    "XEON.DE": "Cash"
}

def performance_berechnen(ticker):
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

        asset_name = tickers_3x.get(ticker) or tickers_1x.get(ticker) or ticker
        return [asset_name, performance_1m, performance_3m, performance_6m, performance_9m, momentum, sma_percent]
    except:
        return None

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

def berechne_alle_daten():
    performances_3x = [p for t in tickers_3x if (p := performance_berechnen(t)) is not None]
    df_3x = pd.DataFrame(performances_3x, columns=["Asset", "1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"])
    df_3x[["1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"]] = df_3x[["1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"]].round(2).astype(str) + '%'
    df_3x_above_sma = df_3x[df_3x['Jetzt über SMA in %'].str.rstrip('%').astype(float) > 0].copy()
    df_3x_above_sma['Momentum'] = df_3x_above_sma['Momentum'].str.rstrip('%').astype(float)
    df_3x_above_sma.sort_values(by='Momentum', ascending=False, inplace=True)
    df_3x_above_sma['Stellung'] = range(1, len(df_3x_above_sma) + 1)
    df_3x['Stellung'] = df_3x['Asset'].apply(lambda x: df_3x_above_sma.loc[df_3x_above_sma['Asset'] == x, 'Stellung'].values[0] if x in df_3x_above_sma['Asset'].values else  "Nein" )
    df_3x = df_3x[['Stellung'] + [col for col in df_3x.columns if col != 'Stellung']]

    performances_1x = [p for t in tickers_1x if (p := performance_berechnen(t)) is not None]
    df_1x = pd.DataFrame(performances_1x, columns=["Asset", "1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"])
    df_1x[["1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"]] = df_1x[["1mo", "3mo", "6mo", "9mo", "Momentum", "Jetzt über SMA in %"]].round(2).astype(str) + '%'
    df_1x_above_sma = df_1x[df_1x['Jetzt über SMA in %'].str.rstrip('%').astype(float) > 0].copy()
    df_1x_above_sma['Momentum'] = df_1x_above_sma['Momentum'].str.rstrip('%').astype(float)
    df_1x_above_sma.sort_values(by='Momentum', ascending=False, inplace=True)
    df_1x_above_sma['Stellung'] = range(1, len(df_1x_above_sma) + 1)
    df_1x['Stellung'] = df_1x['Asset'].apply(lambda x: df_1x_above_sma.loc[df_1x_above_sma['Asset'] == x, 'Stellung'].values[0] if x in df_1x_above_sma['Asset'].values else "Nein")
    df_1x = df_1x[['Stellung'] + [col for col in df_1x.columns if col != 'Stellung']]

    df_3x['Stellung'] = pd.to_numeric(df_3x['Stellung'], errors='coerce')
    df_3x.sort_values(by='Stellung', inplace=True)
    df_3x['Stellung'] = df_3x['Stellung'].apply(lambda x: str(int(x)) if pd.notnull(x) else 'Nein')

    df_1x['Stellung'] = pd.to_numeric(df_1x['Stellung'], errors='coerce')
    df_1x.sort_values(by='Stellung', inplace=True)
    df_1x['Stellung'] = df_1x['Stellung'].apply(lambda x: str(int(x)) if pd.notnull(x) else 'Nein')

    sma_sap, current_sap, percent_sap = calculate_sma("^GSPC")
    sma_tip, current_tip, percent_tip = calculate_sma("TIP")
    sma_gold, current_gold, percent_gold = calculate_sma("GC=F")

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

    return df_3x, df_1x, data_letsgo, result

@app.route("/")
def index():
    df_3x, df_1x, data_letsgo, result = berechne_alle_daten()
    gtaa_3x = df_3x.to_dict(orient="records")
    gtaa_1x = df_1x.to_dict(orient="records")
    return render_template("index.html", gtaa_3x=gtaa_3x, gtaa_1x=gtaa_1x, letsgo=data_letsgo, signal=result)

if __name__ == "__main__":
    app.run(debug=True)
