from flask import Flask, jsonify, redirect, render_template_string, send_from_directory
import requests
from bs4 import BeautifulSoup
import threading
import time

app = Flask(__name__)

# Global variables to store the balance and history
global_balance = {}
global_history = []

# Function to fetch data and update global variables
def fetch_transaction_history():
    global global_balance, global_history

    login_url = "https://www.tibia.com/account/?subtopic=accountmanagement"
    credentials = {
        "loginemail": "x",
        "password": "x*"
    }

    session = requests.Session()
    session.post(login_url, data=credentials)

    session.cookies.set("CookieConsentPreferences", "%7B%22consent%22%3Atrue%2C%22advertising%22%3Atrue%2C%22socialmedia%22%3Atrue%7D")
    session.cookies.set("cf_clearance", "e6mIptWLHp3Ah4XGOiC.KNFkVQrrmNFJSkiXNcY0sUM-1717735089-1.0.1.1-5OP_DrWRAPkUYalmghO7gZvnfMfwp8L2CSsIqHwKqDfuMKtHdhOgsnkZ2spFXQvHmVfFe8u3TehxhDz1te00HA")
    session.cookies.set("DM_LandingPage", "visited")
    session.cookies.set("DM_SessionID", "462a1c71f7c66da533f42792681325201717654591")
    session.cookies.set("SecureSessionID", "2tFAYgukmAvBObho2aZYFgMEvm40UV")
    session.cookies.set("SessionLastVisit", "1717735109")

    transaction_url = "https://www.tibia.com/account/?subtopic=accountmanagement&page=tibiacoinshistory"
    response = session.get(transaction_url)

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract Coins Balance
    balance_table = soup.find_all("table", {"class": "Table3"})[0]
    if balance_table:
        balance_rows = balance_table.find_all("tr")[1:4]  # Adjust this if needed based on the actual number of rows
        balance = {}
        for row in balance_rows:
            cells = row.find_all("td")
            if len(cells) >= 2:
                balance[cells[0].text.strip()] = cells[1].text.strip()
        global_balance = balance

    # Extract Coins History
    history_table = soup.find_all("table", {"class": "Table3"})[1]
    if history_table:
        history_rows = history_table.find_all("tr")[1:]  # Skip the header row
        history = []
        for row in history_rows:
            cells = row.find_all("td")
            if len(cells) >= 5:
                # Check if this row is a data row
                if cells[0].text.strip().isdigit():
                    date = cells[1].text.strip()
                    description = cells[2].text.strip()
                    character = description.split("gifted to")[0].strip()
                    balance_element = cells[4].find("span", {"class": "ColorGreen"})
                    balance = balance_element.text.strip() if balance_element else cells[4].text.strip()
                    history.append({
                        "date": date,
                        "character": character,
                        "balance": balance
                    })
        global_history = history

# Background thread to update data every minute
def update_data():
    while True:
        fetch_transaction_history()
        time.sleep(60)

threading.Thread(target=update_data, daemon=True).start()

@app.route('/', methods=['GET'])
def index():
    return redirect('/transactions')

@app.route('/transactions/balance', methods=['GET'])
def balance():
    return jsonify(global_balance)

@app.route('/transactions/history', methods=['GET'])
def history():
    return jsonify(global_history)

@app.route('/transactions/view/balance', methods=['GET'])
def view_balance():
    balance_html = """
    <html>
   
    <head>
        <link href='https://fonts.googleapis.com/css?family=MedievalSharp' rel='stylesheet'>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <h2>Coins Balance</h2>
        <table class="table">
            <tr>
                <th>Type</th>
                <th>Amount</th>
            </tr>
            {% for key, value in balance.items() %}
            <tr>
                <td>{{ key }}</td>
                <td>{{ value }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(balance_html, balance=global_balance)

@app.route('/transactions/view/history', methods=['GET'])
def view_history():
    history_html = """
    <html>
    <head>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
    </head>
    <body>
        <h2>Donate Char:</h2>
        <h2>Magenta Twitch</h2>
        <div class="table-container">
            <div class="left-border"></div>
            <div class="right-border"></div>
            <table class="table">
                <tr>
                    <th>Fecha</th>
                    <th>Character</th>
                    <th>Donated</th>
                </tr>
                {% for item in history %}
                <tr>
                    <td class="date-cell">{{ item.date.split(',')[0] }}</td>
                    <td class="character-cell">{{ item.character }}</td>
                    <td class="{% if '+' in item.balance %}balance-cell-positive{% else %}balance-cell-negative{% endif %}">{{ item.balance }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(history_html, history=global_history)







# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)
