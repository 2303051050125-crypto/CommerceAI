from flask import Flask, jsonify
from flask_cors import CORS

from routes.chat_routes import chat_bp
from routes.purchase_routes import purchase_bp


# Create Flask application
app = Flask(__name__)

# Allow frontend to communicate with backend
CORS(app)

app.register_blueprint(chat_bp)
app.register_blueprint(purchase_bp)

# -----------------------------------------
# HOME / HEALTH CHECK
# -----------------------------------------

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "message": "AI Personal Commerce Manager API is running!",
        "status": "online"
    })


# -----------------------------------------
# TEST API
# -----------------------------------------

@app.route("/api/test")
def test_api():

    return jsonify({
        "success": True,
        "message": "Backend connection successful!"
    })


# -----------------------------------------
# RUN SERVER
# -----------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )