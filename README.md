**Stock Price Tracker API
A backend API for tracking stock prices, built with Flask, PostgreSQL and Docker.**

🔹 Prerequisites
Docker installed (Get Docker)
Python 3.9+ installed (only needed for running locally)
🔹 How to Set Up the Project (First-Time Setup)
If setting up for the first time:

Clone the repository:
`git clone <repo_url>
cd stock-price-tracker
`
Build and start the application:
`docker-compose up --build`
Apply migrations inside the Flask container:
`winpty docker exec -it <flask_container_id> flask db upgrade`
***Replace <flask_container_id> with the actual container name from docker ps.
This ensures that all tables are created in PostgreSQL.


**How to Restart Development After Stopping**
If you’ve previously set up the project and want to continue working:

Start Docker services:
`docker-compose up`
This starts both the Flask app (app) and PostgreSQL (db).
Run database migrations (if needed):
`winpty docker exec -it <flask_container_id> flask db upgrade`
View running containers (to find container IDs if needed):
`docker ps`
Enter the PostgreSQL shell (for debugging or querying):
`docker exec -it <db_container_id> psql -U user -d stock_tracker`
