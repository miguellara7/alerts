from flask import Flask, jsonify, redirect, render_template_string, send_from_directory
import requests
from bs4 import BeautifulSoup
import threading
import time
import os
from datetime import datetime
import pytz
from dateutil import parser

app = Flask(__name__)

# Global variables to store the balance and history
global_balance = {}
global_history = []
last_donation = None
donation_alert_sent = False
processed_donations = set()  # Set to keep track of processed donations

# Function to fetch data and update global variables
def fetch_transaction_history():
    global global_balance, global_history, last_donation, donation_alert_sent, processed_donations

    login_url = "https://www.tibia.com/account/?subtopic=accountmanagement"
    credentials = {
        "loginemail": "miguel.laramx9@outlook.com",
        "password": "Miguelshta21*"
    }

    session = requests.Session()
    session.post(login_url, data=credentials)

    # Manually set the cookies
    session.cookies.set("CookieConsentPreferences", "%7B%22consent%22%3Atrue%2C%22advertising%22%3Atrue%2C%22socialmedia%22%3Atrue%7D")
    session.cookies.set("cf_clearance", "qjtpvlwMfh7v3kHAN4LmBpiJgXYGG64T8lOG2f55dOk-1718058072-1.0.1.1-XYN9YZMdFpWGtssRLdwAIq4I4iko3O9JuKgxZim6bYI7h3eATdzxBenqDfEc5r2aGaGMPojtdUjRq4ZsGL15hQ")
    session.cookies.set("DM_LandingPage", "visited")
    session.cookies.set("DM_SessionID", "5cea21f88b1cf1983b8ac0a0ba74f8521718050409")
    session.cookies.set("SecureSessionID", "hl89qUJ3v8iHIUnD12xSwdzeFMtqYt")
    session.cookies.set("SessionLastVisit", "1718058075")

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
                    date = cells[1].text.strip().replace('\xa0', ' ')
                    description = cells[2].text.strip()
                    character = description.split("gifted to")[0].strip()
                    balance_element = cells[4].find("span", {"class": "ColorGreen"})
                    balance = balance_element.text.strip() if balance_element else cells[4].text.strip()
                    donation_id = f"{character}_{date.split(',')[0]}"
                    history.append({
                        "date": date,
                        "character": character,
                        "balance": balance,
                        "id": donation_id
                    })

        # Check for new donations based on current CEST time
        current_time = datetime.now(pytz.timezone('Europe/Berlin'))
        for donation in history:
            try:
                # Print the date string for debugging
                print(f"Parsing date: {donation['date']}")
                # Attempt to parse the date using dateutil.parser
                donation_time = parser.parse(donation["date"]).astimezone(pytz.timezone('Europe/Berlin'))
                if donation["id"] not in processed_donations and donation_time <= current_time:
                    last_donation = donation
                    processed_donations.add(donation["id"])
                    donation_alert_sent = False  # Reset alert sent flag for new donation
                    with open("donation_log.txt", "a") as log_file:
                        log_file.write(f"New donation: {last_donation['character']} donated {last_donation['balance']} on {last_donation['date']}, status: sent\n")
                    print(f"New donation detected: {last_donation}")
                    break  # Exit after processing the first new donation
            except ValueError:
                print(f"Error parsing date: {donation['date']}")

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
        <style>
            .table-container {
                max-width: 100%;
                overflow-x: auto;
            }
        </style>
    </head>
    <body>
        <h2>Donate Char:</h2>
        <h2>Magentatc</h2>
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

@app.route('/transactions/new_donation', methods=['GET'])
def new_donation():
    global last_donation, donation_alert_sent
    if not last_donation or donation_alert_sent:
        return jsonify({"new_donation": False})

    donation_alert_sent = True
    print(f"Sending donation alert: {last_donation}")
    return jsonify({
        "new_donation": True,
        "character": last_donation['character'],
        "balance": last_donation['balance']
    })

@app.route('/transactions/alert', methods=['GET'])
def alert():
    donation_alert_html = """
    <html>
    <head>
        <link rel="stylesheet" type="text/css" href="/static/style.css">
        <style>
            body {
                background-color: #00ff00;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .alert {
                position: relative;
                text-align: center;
                font-size: 2em;
                color: white;
                opacity: 0;
                transition: opacity 1s ease-in-out;
            }
            .alert.show {
                opacity: 1;
            }
            .alert img {
                width: 200px;
                height: auto;
                display: none;
            }
            .alert-label {
                font-weight: bold;
                display: none;
            }
            .character-name {
                color: yellow;
                text-shadow: 1px 1px 2px black;
                font-weight: bold;
            }
            .balance-amount {
                color: #0F0;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="alert" id="donation-alert">
            <img id="donate-image" src="/static/donate.png" alt="Donate">
            <div class="alert-label" id="alert-text"></div>
            <audio id="donation-sound">
                <source src="/static/donate.mp3" type="audio/mpeg">
            </audio>
        </div>
        <script>
            function checkNewDonation() {
                fetch('/transactions/new_donation')
                .then(response => response.json())
                .then(data => {
                    if (data.new_donation) {
                        console.log("New donation received: ", data);
                        document.getElementById('alert-text').innerHTML = `<span class="character-name">${data.character}</span> acaba de donar <span class="balance-amount">${data.balance} Tibia Coins!</span>`;
                        document.getElementById('donate-image').style.display = 'block';
                        document.getElementById('alert-text').style.display = 'block';
                        document.getElementById('donation-sound').play();
                        const alertElement = document.getElementById('donation-alert');
                        alertElement.classList.add('show');
                        setTimeout(() => {
                            alertElement.classList.remove('show');
                            document.getElementById('donate-image').style.display = 'none';
                            document.getElementById('alert-text').style.display = 'none';
                        }, 10000); // Hide the alert text after 10 seconds
                    }
                });
            }

            setInterval(checkNewDonation, 5000); // Check for new donations every 5 seconds
        </script>
    </body>
    </html>
    """
    return render_template_string(donation_alert_html)

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)
