import psycopg2
import os
import logging
import requests
from flask import Flask, session, redirect, url_for, jsonify, request
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from functools import wraps
from dotenv import load_dotenv
import datetime

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url="https://oauth2.googleapis.com/token",
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    api_base_url="https://www.googleapis.com/oauth2/v1/",
    client_kwargs={
        "scope": "openid email profile",
        "prompt": "select_account"
    },
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs"
)

# Database Initialize
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    name = db.Column(db.String(255))
    oauth_provider = db.Column(db.String(50))
    oauth_id = db.Column(db.String(255), unique=True)
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class TrackedStock(db.Model):
    __tablename__ = 'tracked_stocks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    ticker = db.Column(db.String(10), nullable=False)
    added_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class StockPrice(db.Model):
    __tablename__ = 'stock_prices'
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

def get_db_connection():
    conn = psycopg2.connect(
        host="db",
        database="stock_tracker",
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized access"}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    return "Welcome to the OAuth Demo! <a href='/login'>Login with Google</a>"

@app.route("/login")
def login():
    return google.authorize_redirect(url_for("callback", _external=True))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/login/callback")
def callback():
    token = google.authorize_access_token()
    user_info = google.get("userinfo").json()

    existing_user = User.query.filter_by(oauth_id=user_info["id"]).first()

    if not existing_user:
        new_user = User(
            email=user_info["email"],
            name=user_info["name"],
            oauth_provider="google",
            oauth_id=user_info["id"],
        )
        db.session.add(new_user)
        db.session.commit()
        session["user_id"] = new_user.id  # Store user ID in session
    else:
        session["user_id"] = existing_user.id  # Store existing user ID

    print(f"Stored user in session:", session["user_id"])  # Debugging

    return redirect(url_for("profile"))

@app.route("/debug-session")
def debug_session():
    return jsonify({"session": dict(session)})


@app.route("/profile")
@login_required
def profile():
    app.logger.info(session)  # Debugging
    user_id = session.get("user_id")

    if not user_id:
        app.logger.info("User ID is missing from session!")  # Debugging
        return jsonify({"error": "Unauthorized access"}), 401

    user = User.query.get(user_id)

    if not user:
        app.logger.info(f"User not found for ID: {user_id}")  # Debugging
        return jsonify({"error": "User not found"}), 404

    return jsonify({"message": f"Hello, {user.name}!", "email": user.email})

@app.route("/stock/<symbol>", methods=["GET"])
@login_required
def get_stock_price(symbol):

    user_id = session.get("user_id")
    print(user_id)

    if not user_id:
        return jsonify({"error": "Unauthorized access"}), 401

    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol.upper(),
        "apikey": ALPHA_VANTAGE_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "Global Quote" in data:
        stock_data = {
            "symbol": data["Global Quote"]["01. symbol"],
            "price": data["Global Quote"]["05. price"],
            "change": data["Global Quote"]["09. change"],
            "last_updated": data["Global Quote"]["07. latest trading day"]
        }
        return jsonify(stock_data)
    else:
        return jsonify({"error": "Stock not found"}), 404


@app.route("/track-stock", methods=["POST"])
@login_required
def track_stock():

    data = request.get_json()
    ticker = data.get("ticker")

    if not ticker:
        return jsonify({"error": "Stock ticker is required"}), 400

    # Get user ID from session
    user_id = session.get("user_id")

    # Check if stock is already being tracked
    existing_entry = TrackedStock.query.filter_by(user_id=user_id, ticker=ticker.upper()).first()
    if existing_entry:
        return jsonify({"message": "Stock is already being tracked"}), 409

    # Add stock to tracked list
    new_tracked_stock = TrackedStock(user_id=user_id, ticker=ticker.upper(), added_at=datetime.datetime.utcnow())
    db.session.add(new_tracked_stock)
    db.session.commit()

    return jsonify({"message": f"Tracking {ticker.upper()} successfully!"}), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')