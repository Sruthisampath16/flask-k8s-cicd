from flask import Flask, jsonify
import socket
import os

app =  Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION","v1")


@app.route("/")
def home():
    return jsonify({
	"message": "Hello from flask on k8s,"
	"version": APP_VERSION,
	"hostname": socket.gethostename(),
})


@app.route("/healthz")
def healthz():
    return jsontify({"status:alive"}),200

@app.route("/readyz")
def route():
    return jsonify({"status":"ready"}),200


if __name__== "__main__":
   app.run(host="0.0.0.0", port=5000)
