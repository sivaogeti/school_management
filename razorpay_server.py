from flask import Flask, request, jsonify
import razorpay
import os
import streamlit as st

OPENAI_API_KEY = st.secrets["api_keys"]["openai_api_key"]
RAZORPAY_KEY_ID = st.secrets["api_keys"]["razorpay_key_id"]
RAZORPAY_SECRET = st.secrets["api_keys"]["razorpay_key_secret"]

app = Flask(__name__)

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

@app.route("/create-order", methods=["POST"])
def create_order():
    data = request.get_json()

    try:
        amount = int(data.get("amount", 0)) * 100  # ₹ to paise
        currency = "INR"

        razorpay_order = client.order.create({
            "amount": amount,
            "currency": currency,
            "payment_capture": 1
        })

        return jsonify({
            "order_id": razorpay_order["id"],
            "amount": amount,
            "currency": currency,
            "key": RAZORPAY_KEY_ID
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(port=5001, debug=True)
