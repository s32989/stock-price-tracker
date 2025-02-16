import psycopg2
from flask import Flask

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host="db",
        database="stock_tracker",
        user="user",
        password="password"
    )
    return conn

@app.route('/')
def home():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT version();')
    version = cur.fetchone()
    cur.close()
    conn.close()
    return f"Connected to PostgreSQL: {version[0]}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')