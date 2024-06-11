import uuid
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

# Get the current date and time in CEST and format it
actual_date = datetime.now(pytz.timezone('Europe/Berlin'))

# Global variables to store the balance and history
global_balance = {}
global_history = []
last_donation = None
donation_alert_sent = False
processed_donations = set()  # Set to keep track of processed donations
log_file_path = "donation_log.txt"
sent_donations_file = "sent_donation.txt"

# Load processed donations from log file
def load_processed_donations():
    if os.path.exists(log_file_path):
        with open(log_file_path, "r") as log_file:
            for line in log_file:
                if "status: sent" in line:
                    try:
                        donation_id = line.split(", status: sent")[0].split("id: ")[1]
                        processed_donations.add(donation_id)
                    except IndexError:
                        print(f"Error processing line in log file: {line}")

    if os.path.exists(sent_donations_file):
        with open(sent_donations_file, "r") as sent_file:
            for line in sent_file:
                processed_donations.add(line.strip())

load_processed_donations()

# Function to save processed donations to file
def save_processed_donation(donation_id):
    with open(sent_donations_file, "a") as sent_file:
        sent_file.write(f"{donation_id}\n")

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
    session.cookies.set("cf_clearance", "GAOZ51fCrPzqlPwfzXywmxCjXuKD8rf2.ckcp6tc96s-1718090007-1.0.1.1-mJJwThbnUqEMZNFtPl7hK3p97hFwemh9vzc8BquBn22Tau00vaVMZdadVsaDNxL3504_.6RutoFIr1oDoutGjQ")
    session.cookies.set("DM_LandingPage", "visited")
    session.cookies.set("DM_SessionID", "ee81d5aa703f6b66b911c008cb2628131718090002")
    session.cookies.set("SecureSessionID", "7Uu5ZnzAlfWt8RTtjHLLG6ueaOCzxn")
    session.cookies.set("SessionLastVisit", "1718090025")

    transaction_url = "https://www.tibia.com/account/?subtopic=accountmanagement&page=tibiacoinshistory"
    response = session.get(transaction_url)

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract Coins Balance
    tables = soup.find_all("table", {"class": "Table3"})
    if len(tables) > 0:
        balance_table = tables[0]
        if balance_table:
            balance_rows = balance_table.find_all("tr")[1:4]  # Adjust this if needed based on the actual number of rows
            balance = {}
            for row in balance_rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    balance[cells[0].text.strip()] = cells[1].text.strip()
            global_balance = balance

    # Extract Coins History
    if len(tables) > 1:
        history_table = tables[1]
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
                        donation_id = str(uuid.uuid4())  # Generate a unique ID for each donation
                        history.append({
                            "date": date,
                            "character": character,
                            "balance": balance,
                            "id": donation_id
                        })

            # Update global history with the new fetched history
            global_history = history

            # Check for new donations based on current CEST time
            current_time = datetime.now(pytz.timezone('Europe/Berlin'))
            new_donations = [donation for donation in history if donation["id"] not in processed_donations]
            if new_donations:
                for donation in new_donations:
                    donation_date = parser.parse(donation["date"])
                    if donation_date > current_time:
                        last_donation = donation
                        donation_alert_sent = False
                        processed_donations.add(last_donation["id"])
                        save_processed_donation(last_donation["id"])  # Save the processed donation ID to file
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"New donation: {last_donation['character']} donated {last_donation['balance']} on {last_donation['date']}, id: {last_donation['id']}, status: sent\n")
                        print(f"New donation detected: {last_donation}, actual_date: {current_time}")
                        break  # Exit the loop once a new donation is found

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
        
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Cinzel&family=MedievalSharp&family=Pirata+One&display=swap');

            body {
                font-family: 'Cinzel', 'MedievalSharp', 'Pirata One', Verdana, Arial, Times New Roman, sans-serif;
                background-color: #333; /* Dark background color */
                font-weight: bold;
                color: #3A342A;
            }

            h2 {
                color: #A5A5A5;
                text-align: center;
            }

            .table-container {
                width: 643px; /* Adjust to the width of bg.png */
                height: 182px; /* Adjust to the height of bg.png */
                margin: 20px auto;
                position: relative;
                background: url('{{ url_for('static', filename='bg.png') }}') no-repeat center center;
                background-size: contain;
                border: 0px solid #444; /* Border color to match the dark theme */
                padding: 10px;
                border-radius: 0px;
                overflow: hidden; /* Hide overflowing content */
            }

            table {
                width: 100%;
                border-collapse: collapse;
                color: #fff; /* White text color */
                font-size: 12px; /* Adjust font size */
            }

            th, td {
                padding: 1px; /* Reduced padding */
                text-align: left;
                border-bottom: 1px solid #444; /* Border color for rows */
                word-wrap: break-word; /* Allow text to wrap */
                white-space: nowrap; /* Prevent text from wrapping */
            }

            th {
                color: yellow;
                text-shadow: 2px 2px 4px #000000;
                padding-top: 5px;
                text-align: left;
                background-color: #444; /* Slightly lighter background for headers */
                color: #f2f2f2; /* Lighter text color for headers */
            }

            tr:hover {
                background-color: #555; /* Row hover effect */
            }

            .table-title {
                color: #ff69b4; /* Pink title color */
                font-size: 14px; /* Smaller font size */
                padding-bottom: 5px;
                display: block;
            }

            .glowing-green {
                color: green;
                text-shadow: 0 0 5px green, 0 0 10px green, 0 0 15px green;
            }

            .yellow-shadow {
                color: yellow;
                text-shadow: 2px 2px 4px #000000;
                font-family: Verdana, sans-serif;
                padding: 5px;       
            }

            .balance-cell-positive, .balance-cell-negative {
                font-weight: bold;
                color: #00FF00; /* Maya green color */
            }

            .character-cell {
                color: yellow;
                text-shadow: 2px 2px 4px #000000;
            }
        </style>
    </head>
<body>
    <h2 class="glowing-green">Donate Char:</h2>
    <h2 class="yellow-shadow">Magentatc</h2>
    <div class="table-container">
        <span class="table-title">Tibia Coins Donations </span> 
        <table>
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Character</th>
                    <th>Donated</th>
                </tr>
            </thead>
            <tbody>
                {% for item in history[:7] %}
                    {% if item.character != 'Magentatc' and item.character != 'Charis Saro' and item.character != 'Nicole Huntington' %}
                    <tr>
                        <td>{{ item.date.split(',')[0] }}</td>
                        <td class="character-cell">{{ item.character }}</td>
                        <td class="{% if '+' in item.balance %}balance-cell-positive{% else %}balance-cell-negative{% endif %}">{{ item.balance }}</td>
                    </tr>
                    {% endif %}
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>

    </html>
    """
    return render_template_string(history_html, history=global_history)


@app.route('/transactions/new_donation', methods=['GET'])
def new_donation():
    global last_donation, donation_alert_sent
    if not last_donation:
        return jsonify({
            "new_donation": False,
            "last_donation_status": "No donations available",
            "donation_alert_sent": donation_alert_sent
        })

    if donation_alert_sent:
        return jsonify({
            "new_donation": False,
            "last_donation": last_donation,
            "last_donation_status": "Alert already sent",
            "donation_alert_sent": donation_alert_sent
        })

    donation_alert_sent = True
    save_processed_donation(last_donation["id"])  # Save the processed donation ID to file
    with open(log_file_path, "a") as log_file:
        log_file.write(f"Alert sent: {last_donation['character']} donated {last_donation['balance']} on {last_donation['date']}, id: {last_donation['id']}, status: sent\n")
    print(f"Sending donation alert: {last_donation}, actual_date: {actual_date}")
    return jsonify({
        "new_donation": True,
        "character": last_donation['character'],
        "balance": last_donation['balance'],
        "last_donation_status": "Alert sent",
        "donation_alert_sent": donation_alert_sent
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
                text-shadow: 2px 2px 4px #000000;
                font-family: Verdana, sans-serif;
                font-weight: bold;
                align-items: center;
            }
            .balance-amount {
                color: #0F0;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="alert" id="donation-alert">
            <img id="donate-image" align="center" src="/static/donate.png" alt="Donate">
            <div class="alert-label" id="alert-text"></div>
            <audio id="donation-sound">
                <source src="/static/donate.mp3" type="audio/mpeg">
            </audio>
        </div>
        <script>
            const actualDate = new Date('{{ actual_date|tojson }}'); // Actual date and time in CEST

            function checkNewDonation() {
                fetch('/transactions/new_donation')
                .then(response => response.json())
                .then(data => {
                    if (data.new_donation) {
                        const donationDate = new Date(data.last_donation.date);
                        if (donationDate > actualDate) {
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
                        } else {
                            console.log("Donation is before the actual date and time, no alert sent.");
                        }
                    } else {
                        console.log("No new donation: ", data);
                    }
                });
            }

            setInterval(checkNewDonation, 5000); // Check for new donations every 5 seconds
        </script>
    </body>
    </html>
    """
    return render_template_string(donation_alert_html, actual_date=actual_date.isoformat())

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0")
