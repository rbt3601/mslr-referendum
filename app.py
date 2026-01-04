from flask import Flask, jsonify, request, render_template,redirect, url_for, session      # flask is used to create web application and jsonify is used to convert python into json format(for checking API)
import re                                         # Regular expression for checking the SCC format
from datetime import date, datetime               # for validating the age 
from werkzeug.security import generate_password_hash, check_password_hash             #For password hashing 
import mysql.connector                                                                #MYSQL CONNECTOR
from mysql.connector import Error

EC_USERNAME = "ec@referendum.gov.sr"
EC_PASSWORD_HASH = generate_password_hash("Shangrilavote&2025@")

app = Flask(__name__)

# Sessions secret
app.secret_key = "mslr-secret-key-change-later"        

# Database connection 

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Ratha@27050903",   
        database="mslr_db"
    )
 
# Health check of the application

@app.route("/mslr/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "UP",
        "service": "MSLR Referendum Backend"
    })

# API for Register

@app.route("/mslr/register", methods=["POST"])
def register_user():
    data = request.get_json()

    email = data.get("email")
    full_name = data.get("full_name")
    dob = data.get("dob")
    raw_password = data.get("password")
    confirm_password = data.get("confirm_password")
    scc = data.get("scc")

    # Required fields
    if not email or not full_name or not dob or not raw_password or not confirm_password or not scc:
        return jsonify({"error": "All fields are required"}), 400


    # DOB format validation
    try:
        dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({
            "error": "Invalid date of birth format. Use YYYY-MM-DD."
        }), 400

    # Age validation (18+)
    today = date.today()
    age = today.year - dob_date.year - (
        (today.month, today.day) < (dob_date.month, dob_date.day)
    )

    if age < 18:
        return jsonify({
            "error": "Registration not allowed. Voter must be at least 18 years old."
        }), 400

    # SCC format validation
    if not re.fullmatch(r"[A-Z0-9]{10}", scc):
        return jsonify({
            "error": "Invalid SCC format. SCC must be 10 uppercase alphanumeric characters."
        }), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check SCC existence
        cursor.execute(
            "SELECT is_used FROM scc_codes WHERE scc_code = %s",
            (scc,)
        )
        scc_record = cursor.fetchone()

        if not scc_record:
            return jsonify({
                "error": "Invalid SCC. The code does not exist in the system."
            }), 400

        # Check SCC already used
        if scc_record["is_used"]:
            return jsonify({
                "error": "This SCC has already been used for registration."
            }), 409

        # Check email already registered
        cursor.execute(
            "SELECT id FROM voters WHERE email = %s",
            (email,)
        )
        if cursor.fetchone():
            return jsonify({
                "error": "This email address is already registered."
            }), 409

        if raw_password != confirm_password:
            return jsonify({
                "error": "Passwords do not match."
            }), 400

        # Hash password
        hashed_password = generate_password_hash(raw_password)

        # Insert voter
        cursor.execute(
            """
            INSERT INTO voters (full_name, email, dob, password_hash, scc_code)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (full_name, email, dob, hashed_password, scc)
        )

        # Mark SCC as used
        cursor.execute(
            "UPDATE scc_codes SET is_used = TRUE WHERE scc_code = %s",
            (scc,)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "User registered successfully"
        }), 201

    except Error as e:
        print(e)
        return jsonify({
            "error": "Database error occurred."
        }), 500



# Election Comission login 
@app.route("/ec/login", methods=["GET", "POST"])
def ec_login():
    if request.method == "GET":
        return render_template("ec_login.html")

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if username != EC_USERNAME or not check_password_hash(EC_PASSWORD_HASH, password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Login successful
    session["ec_logged_in"] = True
    return jsonify({"message": "Login successful"}), 200

# Election Comission Dashboard
@app.route("/ec/dashboard")
def ec_dashboard():
    if not session.get("ec_logged_in"):
        return redirect(url_for("ec_login"))

    return render_template("ec_dashboard.html")

@app.route("/ec/logout")
def ec_logout():
    session.clear()
    return redirect(url_for("ec_login"))


#  Voter Login API 
@app.route("/mslr/login", methods=["POST"])
def voter_login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required."
        }), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, full_name, password_hash FROM voters WHERE email = %s",
            (email,)
        )
        voter = cursor.fetchone()

        if not voter:
            return jsonify({
                "error": "Invalid email or password."
            }), 401

        if not check_password_hash(voter["password_hash"], password):
            return jsonify({
                "error": "Invalid email or password."
            }), 401

        # Login success → create session
        session["voter_logged_in"] = True
        session["voter_id"] = voter["id"]
        session["voter_name"] = voter["full_name"]

        return jsonify({
            "message": "Login successful"
        }), 200

    except Error as e:
        print(e)
        return jsonify({
            "error": "Database error occurred."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Frontend route for the register,login(both election comission and voter)
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

# Frontend route for Register
@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")

# Frontend route for voter Login 
@app.route("/login", methods=["GET"])
def voter_login_page():
    return render_template("login.html")


# Appplication running 
if __name__ == "__main__":
    app.run(debug=True, port=9999)