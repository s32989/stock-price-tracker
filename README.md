**Prerequesites**
- Python 3.9+
- Install Docker

1) Setup Flask using `pip`
2) Verify application runs using `python app.py`
3) Build Docker image: `docker build -t flask-app .`
4) Run container: `docker run -p 5000:5000 flask-app`
