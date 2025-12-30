from flask import Flask, jsonify, request         # flask is used to create web application and jsonify is used to convert python into json format(for checking API)
import re                                         # Regular expression for checking the SCC format
from datetime import date, datetime               # for validating the age 

app = Flask(__name__)

# Health check of the application 
@app.route("/mslr/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "UP",
        "service": "MSLR Referendum Backend"
    })

# User registration API
@app.route("/mslr/register", methods=["POST"])
def register_user():
    data = request.get_json()

    email = data.get("email")
    full_name = data.get("full_name")
    dob = data.get("dob")
    password = data.get("password")
    scc = data.get("scc")

    # Validation: check required fields
    if not email or not full_name or not dob or not password or not scc:
        return jsonify({
            "error": "All fields are required"
        }), 400
    
    # DOB validation (must be YYYY-MM-DD)
    try:
        dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({
            "error": "Invalid date of birth format. Use YYYY-MM-DD."
        }), 400

    # Age validation (must be 18+)
    today = date.today()
    age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))

    if age < 18:
        return jsonify({
            "error": "Registration not allowed. Voter must be at least 18 years old."
        }), 400

    return jsonify({
        "message": "User registered successfully",
        "user": {
            "email": email,
            "full_name": full_name,
            "dob": dob,
            "scc": scc
        }
    }), 201
    # SCC format validation (10-character alphanumeric, uppercase)
    scc_pattern = r"^[A-Z0-9]{10}$"

    if not re.match(scc_pattern, scc):
        return jsonify({
            "error": "Invalid SCC format. SCC must be 10 uppercase alphanumeric characters."
        }), 400
    


if __name__ == "__main__":
    app.run(debug=True, port=9999)
