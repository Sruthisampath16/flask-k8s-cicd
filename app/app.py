from flask import Flask, jsonify
import socket
import os
import psycopg2

app =  Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION","v1")

DB_HOST = os.environ.get("DB_HOST","postgres-service")
DB_NAME = os.environ.get("POSTGRES_DB","flaskdb")
DB_USER = os.environ.get("POSTGRES_USER","flaskuser")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD","")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=3,
    )
@app.route("/")
def home():
    return jsonify({
      "message": "Hello from flask on k8s",
      "version": APP_VERSION,
      "hostname": socket.gethostname(),
})

@app.route("/healthz")
def healthz():
    return jsonify({"status":"alive"}),200

@app.route("/readyz")
def route():
    try:
        conn = get_db_connection()
        conn.close()                 
        return jsonify({"status":"ready","database":"connection"}),200
    except Exception as e:
        return jsonify({"status":"not ready","database":"unreachable","error":
    str(e)}),503

if __name__== "__main__":
   app.run(host="0.0.0.0", port=5000)
