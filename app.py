import os
import requests
import secrets
from flask import Flask, render_template, jsonify, request, session, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models.predictor import predict_crypto_price
from flask_migrate import Migrate
from datetime import datetime, timezone
# ----------------- Flask App Setup -----------------#

app = Flask(__name__)


# Secure your app with a random secret key
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Set up the SQLite database URI and disable modification tracking
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database', 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy object
db = SQLAlchemy(app)

# ----------------- DB Model -----------------#
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=True) 
    mobile = db.Column(db.String(15), nullable=True)     
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

migrate = Migrate(app, db)

# ----------------- Binance Fetch Function -----------------#
def fetch_binance_data(symbol="BTCUSDT"):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=7'
    print(f"Requesting Binance API: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(f"Fetched data: {data}")  # Debug output
        return data
    else:
        print(f"Error fetching data: {response.status_code}")
    return []


# ----------------- Routes -----------------#
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/aboutus')
def about():
    return render_template('aboutus.html')



@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        username = session['user'] 

        user_data = {
            'coins': ['BTC', 'ETH', 'LTC'],
            'charts_seen': ['BTCUSDT', 'ETHUSDT'],
            'last_prediction': 'ETH will rise 3% in next 7 days'
        }

        return render_template('dashboard.html', user=username, **user_data)

    return redirect(url_for('login'))


@app.route('/dashboard/data')
def dashboard_data():
    # This would normally fetch live data from DB or API
    updated_data = {
        'last_prediction': 'BTC is expected to fall 1.5% soon',
        'coins': ['BTC', 'ETH', 'LTC'],
        'charts_seen': ['BTCUSDT', 'ETHUSDT']
    }
    return jsonify(updated_data)

# Chart page
@app.route('/chart')
def chart():
    return render_template('chart.html')

# Update user profile page
@app.route('/predicts')
def predicts():
    return render_template('predicts.html')


# Logout route
@app.route('/logout')
def logout():
    # Handle logout logic here (e.g., clearing session or redirecting to login)
    return redirect(url_for('login'))

@app.route('/live_chart', methods=['GET'])
def live_chart():
    crypto_symbol = request.args.get('crypto', 'BTCUSDT').upper()
    data = fetch_binance_data(crypto_symbol)

    if not data:
        return jsonify({'error': 'Failed to fetch data from Binance'}), 500

    # Extract closing prices and timestamps
    prices = [float(item[4]) for item in data]  # Close price
    timestamps = [datetime.fromtimestamp(item[0] / 1000, timezone.utc).strftime('%Y-%m-%d') for item in data]

    return jsonify({'prices': prices, 'timestamps': timestamps})



@app.route('/predict', methods=['GET'])
def predict():
    crypto = request.args.get('crypto', 'BTCUSDT')
    data = fetch_binance_data(crypto)
    if not data:
        return jsonify({'error': 'Unable to fetch data from Binance'})

    # Extract closing prices
    prices = [float(item[4]) for item in data]  # item[4] = close price

    # Latest real price
    current_price = prices[-1] if prices else 0.0

    # Predict using your model
    prediction = predict_crypto_price(prices)

    return jsonify({
        'current_price': current_price,
        'predictions': prediction
    })


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists by email
        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already exists", "warning")
            return redirect('/signup')
        
        # Hash the password before storing
        hashed_password = generate_password_hash(password)
        
        # Create a new user instance and add to the session
        new_user = User(username=username, mobile=mobile, email=email, password=hashed_password) #type: ignore
        db.session.add(new_user)
        db.session.commit()

        flash("Signup successful! Please log in.", "success")
        return redirect('/login')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password): #type: ignore
            session['user'] = user.username  # Store username instead of email
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))

        flash("Invalid credentials!", "danger")

    return render_template('login.html')


# ----------------- Run Server -----------------#

if __name__ == '__main__':
    # Ensure the database directory exists
    if not os.path.exists('database'):
        os.makedirs('database')
    
    # Create tables if they don't already exist
    with app.app_context():
        db.create_all()

    app.run(debug=True)
