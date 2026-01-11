from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash     # flask is used to create web application and jsonify is used to convert python into json format(for checking API)
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

# Frontend route for landing page 
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")



# Election Comission login once you click on login as election comission 
@app.route("/mslr/ec-login", methods=["GET", "POST"])
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



# Election Comission Dashboard once the election comission logins 
@app.route("/mslr/ec-dashboard")
def ec_dashboard():
    if not session.get("ec_logged_in"):
        return redirect(url_for("ec_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch referendums
    cursor.execute("""
        SELECT id, title, description, status
        FROM referendums
        ORDER BY id DESC
    """)
    referendums = cursor.fetchall()

    # For each referendum fetch options + votes
    for r in referendums:
        cursor.execute("""
            SELECT id, option_text, vote_count
            FROM referendum_options
            WHERE referendum_id = %s
        """, (r["id"],))
        options = cursor.fetchall()

        total_votes = sum(opt["vote_count"] for opt in options) or 1

        # Add percentage
        for opt in options:
            opt["percentage"] = round(
                (opt["vote_count"] / total_votes) * 100, 2
            )

        r["options"] = options
        r["total_votes"] = total_votes

    cursor.close()
    conn.close()

    return render_template(
        "ec_dashboard.html",
        referendums=referendums
    )


# List all referendums in election commission Dashboard
@app.route("/ec/referendums", methods=["GET"])
def ec_list_referendums():
    if not session.get("ec_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, title, description, status
            FROM referendums
            ORDER BY id DESC
        """)
        referendums = cursor.fetchall()

        return jsonify(referendums), 200

    except Error as e:
        print(e)
        return jsonify({"error": "Database error occurred."}), 500

    finally:
        cursor.close()
        conn.close()



# Create Referendum by elaction comission (UI + API)
@app.route("/mslr/referendum-create", methods=["GET", "POST"])
def create_referendum():
    if not session.get("ec_logged_in"):
        return redirect(url_for("ec_login"))

    if request.method == "GET":
        return render_template("create_referendum.html")

    data = request.get_json()

    title = data.get("title")
    description = data.get("description")
    status = data.get("status", "DRAFT")
    options = data.get("options", [])

    if not title or not description:
        return jsonify({"error": "Title and description are required"}), 400

    if status not in ["DRAFT", "OPEN"]:
        return jsonify({"error": "Invalid status"}), 400

    if len(options) < 2 or len(options) > 4:
        return jsonify({"error": "2–4 options required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insert referendum
        cursor.execute("""
            INSERT INTO referendums (title, description, status)
            VALUES (%s, %s, %s)
        """, (title, description, status))

        referendum_id = cursor.lastrowid

        # Insert options
        for opt in options:
            cursor.execute("""
                INSERT INTO referendum_options (referendum_id, option_text)
                VALUES (%s, %s)
            """, (referendum_id, opt))

        conn.commit()
        return jsonify({"message": "Referendum created"}), 201

    except Error as e:
        conn.rollback()
        return jsonify({"error": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()



# Update referendum status in ec-dashboard
@app.route("/mslr/ec/referendum/<int:ref_id>/status", methods=["POST"])
def update_referendum_status(ref_id):
    if not session.get("ec_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    new_status = request.form.get("status")

    if new_status not in ["OPEN", "CLOSED"]:
        return jsonify({"error": "Invalid status"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE referendums
        SET status = %s
        WHERE id = %s
    """, (new_status, ref_id))
    conn.commit()
    cursor.close()
    conn.close()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "message": f"Referendum {new_status.lower()}ed successfully"
        }), 200

    flash(f"Referendum {new_status.lower()}ed successfully", "success")
    return redirect(url_for("ec_dashboard"))

# Edit referendum  in ec-dashboard
@app.route("/mslr/ec/referendum/<int:ref_id>/edit", methods=["GET", "POST"])
def edit_referendum(ref_id):
    if not session.get("ec_logged_in"):
        return redirect(url_for("ec_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM referendums WHERE id = %s", (ref_id,))
    referendum = cursor.fetchone()

    if not referendum:
        return "Not found", 404

    if referendum["status"] != "DRAFT":
        return "Cannot edit after opening", 403

    # FETCH OPTIONS
    cursor.execute("""
        SELECT id, option_text
        FROM referendum_options
        WHERE referendum_id = %s
        ORDER BY id
    """, (ref_id,))
    options = cursor.fetchall()

    if request.method == "GET":
        cursor.close()
        conn.close()
        return render_template(
            "edit_referendum.html",
            referendum=referendum,
            options=options
        )

    # POST 
    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    options = data.get("options", [])

    if len(options) < 2 or len(options) > 4:
        return jsonify({"error": "2–4 options required"}), 400

    # Update referendum
    cursor.execute("""
        UPDATE referendums
        SET title = %s, description = %s
        WHERE id = %s
    """, (title, description, ref_id))

    # Delete old options
    cursor.execute("""
        DELETE FROM referendum_options
        WHERE referendum_id = %s
    """, (ref_id,))

    # Insert updated options
    for opt in options:
        cursor.execute("""
            INSERT INTO referendum_options (referendum_id, option_text)
            VALUES (%s, %s)
        """, (ref_id, opt["text"]))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Referendum updated"}), 200

# Delete referendum  in ec-dashboard
@app.route("/mslr/referendum/<int:ref_id>/delete", methods=["POST"])
def delete_referendum(ref_id):
    if not session.get("ec_logged_in"):
        return redirect(url_for("ec_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch referendum
    cursor.execute(
        "SELECT status FROM referendums WHERE id = %s",
        (ref_id,)
    )
    ref = cursor.fetchone()

    if not ref:
        cursor.close()
        conn.close()
        return redirect(url_for("ec_dashboard"))

    # Only DRAFT referendums can be deleted
    if ref["status"] != "DRAFT":
        cursor.close()
        conn.close()
        return redirect(url_for("ec_dashboard"))

    # Check if votes exist
    cursor.execute("""
        SELECT COUNT(*) AS vote_count
        FROM votes
        WHERE referendum_id = %s
    """, (ref_id,))
    vote_count = cursor.fetchone()["vote_count"]

    if vote_count > 0:
        cursor.close()
        conn.close()
        # Do NOT delete — preserve integrity
        return redirect(url_for("ec_dashboard"))

    # Safe to delete
    cursor.execute(
        "DELETE FROM referendums WHERE id = %s",
        (ref_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("ec_dashboard"))

#Results of referendum  in ec-dashboard
@app.route("/mslr/ec/results/<int:ref_id>")
def ec_view_referendum_results(ref_id):
    if not session.get("ec_logged_in"):
        return redirect(url_for("ec_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, description
        FROM referendums
        WHERE id = %s AND status = 'CLOSED'
    """, (ref_id,))
    referendum = cursor.fetchone()

    if not referendum:
        cursor.close()
        conn.close()
        return "Results not available", 404

    cursor.execute("""
        SELECT option_text, vote_count
        FROM referendum_options
        WHERE referendum_id = %s
    """, (ref_id,))
    options = cursor.fetchall()

    # Determine winner
    max_votes = max(opt["vote_count"] for opt in options) if options else 0
    for opt in options:
        opt["is_winner"] = opt["vote_count"] == max_votes and max_votes > 0

    cursor.close()
    conn.close()

    return render_template(
        "ec_results.html",
        referendum=referendum,
        options=options
    )

# Logout for EC-Dashboard
@app.route("/ec/logout")
def ec_logout():
    session.clear()
    return redirect(url_for("ec_login"))



#  ------------------------------------------------    VOTER   --------------------------------------------------------- #

# API + UI for Voter Registration
@app.route("/mslr/register", methods=["GET", "POST"])
def register_user():
    # If user opens the page in browser → show registration UI
    if request.method == "GET":
        return render_template("register.html")

    # If form submits via AJAX → handle registration logic
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
        return jsonify({"error": "Invalid date of birth format. Use YYYY-MM-DD."}), 400

    # Age validation (18+)
    today = date.today()
    age = today.year - dob_date.year - (
        (today.month, today.day) < (dob_date.month, dob_date.day)
    )
    if age < 18:
        return jsonify({"error": "Registration not allowed. Voter must be at least 18 years old."}), 400

    # SCC format validation
    if not re.fullmatch(r"[A-Z0-9]{10}", scc):
        return jsonify({"error": "Invalid SCC format. SCC must be 10 uppercase alphanumeric characters."}), 400

    # Confirm password validation
    if raw_password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

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
            return jsonify({"error": "Invalid SCC. The code does not exist in the system."}), 400

        # Check SCC already used
        if scc_record["is_used"]:
            return jsonify({"error": "This SCC has already been used for registration."}), 409

        # Check email already registered
        cursor.execute(
            "SELECT id FROM voters WHERE email = %s",
            (email,)
        )
        if cursor.fetchone():
            return jsonify({"error": "This email address is already registered."}), 409

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

        return jsonify({"message": "User registered successfully"}), 201

    except Error as e:
        print(e)
        return jsonify({"error": "Database error occurred."}), 500


# Voter Login (UI + API)
@app.route("/mslr/login", methods=["GET", "POST"])
def voter_login():
    if request.method == "GET":
        return render_template("login.html")

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, full_name, password_hash FROM voters WHERE email = %s",
            (email,)
        )
        voter = cursor.fetchone()

        if not voter or not check_password_hash(voter["password_hash"], password):
            return jsonify({"error": "Invalid email or password."}), 401

        # Login success → create session
        session["voter_logged_in"] = True
        session["voter_id"] = voter["id"]
        session["voter_name"] = voter["full_name"]

        return jsonify({"message": "Login successful"}), 200

    except Error as e:
        print(e)
        return jsonify({"error": "Database error occurred."}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Voter Dashboard 
@app.route("/mslr/dashboard")
def voter_dashboard():
    if not session.get("voter_logged_in"):
        return redirect(url_for("voter_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS closed_count
        FROM referendums
        WHERE status = 'CLOSED'
    """)
    result = cursor.fetchone()

    results_available = result["closed_count"] > 0

    cursor.close()
    conn.close()

    return render_template(
        "voter_dashboard.html",
        voter_name=session.get("voter_name"),
        results_available=results_available
    )

# List all referendums (Voter view)
@app.route("/mslr/referendums", methods=["GET"])
def list_referendums():
    status = request.args.get("status")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # API MODE
    # Triggered when ?status=OPEN or ?status=CLOSED is present
    if status:
        status = status.strip().upper()

        if status not in ["OPEN", "CLOSED"]:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid status value"}), 400

        cursor.execute("""
            SELECT id, title, description, status
            FROM referendums
            WHERE status = %s
            ORDER BY id
        """, (status,))
        referendums = cursor.fetchall()

        api_result = []

        for ref in referendums:
            cursor.execute("""
                SELECT id, option_text, vote_count
                FROM referendum_options
                WHERE referendum_id = %s
            """, (ref["id"],))
            options = cursor.fetchall()

            formatted_options = []
            counter = 1   # <-- MUST be inside the for-ref loop

            for opt in options:
                formatted_options.append({
                    str(counter): opt["option_text"],
                    "votes": str(opt["vote_count"])
                })
                counter += 1



            api_result.append({
                "referendum_id": str(ref["id"]),
                "status": ref["status"].lower(),
                "referendum_title": ref["title"],
                "referendum_desc": ref["description"],
                "referendum_options": {
                    "options": formatted_options
                }
            })

        cursor.close()
        conn.close()
        return jsonify({"Referendums": api_result}), 200

    # UI MODE
    if not session.get("voter_logged_in"):
        cursor.close()
        conn.close()
        return redirect(url_for("voter_login"))

    voter_id = session.get("voter_id")

    cursor.execute("""
        SELECT id, title, description, status
        FROM referendums
        ORDER BY id DESC
    """)
    referendums = cursor.fetchall()

    for ref in referendums:
        cursor.execute("""
            SELECT id, option_text
            FROM referendum_options
            WHERE referendum_id = %s
        """, (ref["id"],))
        ref["options"] = cursor.fetchall()

        cursor.execute("""
            SELECT id
            FROM votes
            WHERE referendum_id = %s AND voter_id = %s
        """, (ref["id"], voter_id))
        ref["already_voted"] = cursor.fetchone() is not None

    cursor.close()
    conn.close()

    return render_template(
        "referendums.html",
        referendums=referendums,
        voter_name=session.get("voter_name")
    )


#List referendums based on id 
@app.route("/mslr/referendum/<int:ref_id>", methods=["GET"])
def get_referendum_by_id(ref_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, description, status
        FROM referendums
        WHERE id = %s
    """, (ref_id,))
    ref = cursor.fetchone()

    if not ref:
        cursor.close()
        conn.close()
        return jsonify({"error": "Referendum not found"}), 404

    cursor.execute("""
        SELECT id, option_text, vote_count
        FROM referendum_options
        WHERE referendum_id = %s
    """, (ref_id,))
    options = cursor.fetchall()

    formatted_options = []
    counter = 1

    for opt in options:
        formatted_options.append({
            str(counter): opt["option_text"],
            "votes": str(opt["vote_count"])
        })
        counter += 1


    cursor.close()
    conn.close()

    return jsonify({
        "referendum_id": str(ref["id"]),
        "status": ref["status"],
        "referendum_title": ref["title"],
        "referendum_desc": ref["description"],
        "referendum_options": {
            "options": formatted_options
        }
    }), 200



# Voter votes for tehe referndum 
@app.route("/mslr/vote", methods=["POST"])
def cast_vote():
    if not session.get("voter_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    referendum_id = data.get("referendum_id")
    option_id = data.get("option_id")
    voter_id = session.get("voter_id")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Insert vote
        cursor.execute("""
            INSERT INTO votes (referendum_id, voter_id, option_id)
            VALUES (%s, %s, %s)
        """, (referendum_id, voter_id, option_id))

        # Increment option vote
        cursor.execute("""
            UPDATE referendum_options
            SET vote_count = vote_count + 1
            WHERE id = %s
        """, (option_id,))

        # Total registered voters
        cursor.execute("SELECT COUNT(*) AS total FROM voters")
        total_voters = cursor.fetchone()["total"]

        # Max votes for an option
        cursor.execute("""
            SELECT MAX(vote_count) AS max_votes
            FROM referendum_options
            WHERE referendum_id = %s
        """, (referendum_id,))
        max_votes = cursor.fetchone()["max_votes"]

        # Auto-close ONLY if 50% of ALL voters voted same option
        if max_votes >= (total_voters / 2):
            cursor.execute("""
                UPDATE referendums
                SET status = 'CLOSED'
                WHERE id = %s
            """, (referendum_id,))


        conn.commit()
        return jsonify({"message": "Vote recorded"}), 200

    except mysql.connector.IntegrityError:
        return jsonify({"error": "You already voted"}), 409

    finally:
        cursor.close()
        conn.close()


# Closed referendums results
@app.route("/mslr/results")
def view_results():
    if not session.get("voter_logged_in"):
        return redirect(url_for("voter_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get closed referendums
    cursor.execute("""
        SELECT id, title, description
        FROM referendums
        WHERE status = 'CLOSED'
        ORDER BY id DESC
    """)
    referendums = cursor.fetchall()

    for ref in referendums:
        cursor.execute("""
            SELECT option_text, vote_count
            FROM referendum_options
            WHERE referendum_id = %s
        """, (ref["id"],))
        options = cursor.fetchall()

        # Determine winner
        max_votes = max(opt["vote_count"] for opt in options) if options else 0
        for opt in options:
            opt["is_winner"] = opt["vote_count"] == max_votes and max_votes > 0

        ref["options"] = options

    cursor.close()
    conn.close()

    return render_template(
        "results_list.html",
        referendums=referendums,
        voter_name=session.get("voter_name")
    )

# View results of a specific referendum (Voter)
@app.route("/mslr/results/<int:ref_id>")
def view_referendum_results(ref_id):
    if not session.get("voter_logged_in"):
        return redirect(url_for("voter_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, description
        FROM referendums
        WHERE id = %s AND status = 'CLOSED'
    """, (ref_id,))
    referendum = cursor.fetchone()

    if not referendum:
        cursor.close()
        conn.close()
        return "Results not available", 404

    cursor.execute("""
        SELECT option_text, vote_count
        FROM referendum_options
        WHERE referendum_id = %s
    """, (ref_id,))
    options = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "referendum_results.html",
        referendum=referendum,
        options=options,
        voter_name=session.get("voter_name")
    )


# Voter logout
@app.route("/voter/logout")
def voter_logout():
    session.clear()
    return redirect(url_for("voter_login"))

# Appplication running 
if __name__ == "__main__":
    app.run(debug=True, port=9999)
