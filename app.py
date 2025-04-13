from flask import Flask, render_template
import pandas as pd
# ← hier dein kompletter GTAA-Code reinpacken (leicht anpassen, siehe unten)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template(
        'index.html',
        df_3x=df_3x.to_dict(orient='records'),
        df_1x=df_1x.to_dict(orient='records'),
        letsgo=data_letsgo,
        letsgo_result=result
    )

if __name__ == '__main__':
    app.run(debug=True)
