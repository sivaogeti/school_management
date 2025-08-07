from flask import Flask, request, jsonify
import razorpay
import os

app = Flask(__name__)

# Use your Razorpay Test Key ID and Secret
RAZORPAY_KEY_ID = "rzp_test_BnzfYkXpMR8dWo"
RAZORPAY_SECRET = "7LpvmSJuK2JU3vbd5wRQO8th"

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
