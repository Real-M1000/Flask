from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# Definiere ein einfaches Passwort
PASSWORD = "geheim"  # Passworteinstellung

@app.route('/')
def index():
    return render_template_string("""
        <form method="POST" action="/login">
            Passwort: <input type="password" name="password">
            <input type="submit" value="Login">
        </form>
    """)

@app.route('/login', methods=['POST'])
def login():
    password = request.form['password']
    if password == PASSWORD:
        return redirect(url_for('secret'))  # Weiterleitung zur geheimen Seite
    else:
        return "Falsches Passwort. <a href='/'>Erneut versuchen</a>"

@app.route('/secret')
def secret():
    return "Willkommen auf der geheimen Seite! Du hast Zugriff."

if __name__ == '__main__':
    app.run(debug=True)
