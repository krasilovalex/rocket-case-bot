from flask import Flask, request, jsonify, render_template
import json
from utils.db_manager import load_db, save_db

app = Flask(__name__)


@app.route("/api/user/<int:user_id>", methods=['GET'])
def api_get_user(user_id):
    data = load_db()
    user = data['users'].get(str(user_id))
    if not user:
        return jsonify({'error': "User not found"}), 404
    return jsonify