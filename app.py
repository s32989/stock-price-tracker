import psycopg2
import os
from flask import Flask, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@db:5432/stock_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url="https://oauth2.googleapis.com/token",
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    api_base_url="https://www.googleapis.com/oauth2/v1/",
    client_kwargs={"scope": "openid email profile"},
)



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
        user="user",
        password="password"
    )
    return conn


@app.route("/")
def home():
    return "Welcome to the OAuth Demo! <a href='/login'>Login with Google</a>"


@app.route("/login")
def login():
    return google.authorize_redirect(url_for("callback", _external=True))


@app.route("/login/callback")
def callback():
    token = google.authorize_access_token()
    user_info = google.get("userinfo").json()

    # Store user info in session
    session["user"] = user_info

    return redirect(url_for("profile"))


@app.route("/profile")
def profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    return f"Hello, {user['name']}! Your email is {user['email']}."

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')