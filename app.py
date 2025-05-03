from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/get_3x_gtaa')
def get_3x_gtaa():
    data = [
        {"asset": "Asset 1", "jetzt": "100", "sma": "95", "über_sma": "5"},
        {"asset": "Asset 2", "jetzt": "110", "sma": "100", "über_sma": "10"},
    ]
    return jsonify(data)

@app.route('/get_3x_gtaa_leveraged')
def get_3x_gtaa_leveraged():
    data = [
        {"asset": "Asset 1", "jetzt": "150", "sma": "140", "über_sma": "10"},
        {"asset": "Asset 2", "jetzt": "160", "sma": "155", "über_sma": "5"},
    ]
    return jsonify(data)

@app.route('/get_1x_gtaa')
def get_1x_gtaa():
    data = [
        {"asset": "Asset 1", "jetzt": "50", "sma": "48", "über_sma": "2"},
        {"asset": "Asset 2", "jetzt": "55", "sma": "52", "über_sma": "3"},
    ]
    return jsonify(data)

@app.route('/get_letsgo')
def get_letsgo():
    data = [
        {"asset": "Asset A", "jetzt": "75", "sma": "70", "über_sma": "5"},
        {"asset": "Asset B", "jetzt": "80", "sma": "75", "über_sma": "5"},
    ]
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
