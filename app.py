from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import os

app = Flask(__name__)


@app.route('/')
def home():
    return render_template("index.html")

@app.route('/find_similar', methods=['POST'])
def find_similar():
    id = request.json.get('id')
    print(id)

    return jsonify({"message": "This is a placeholder response."})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)