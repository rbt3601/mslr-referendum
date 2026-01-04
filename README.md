# Shangri-La National Referendum – Voter Registration System

This project implements a **Voter Registration Portal** for the Shangri-La National Referendum.  
It is developed using **Python (Flask)** for the backend and **HTML, CSS, and JavaScript** for the frontend.

The system allows eligible citizens to register securely using a unique **Shangri-La Citizen Code (SCC)**, with both manual entry and QR-based input options.

---

## Features Implemented

### Backend (Flask API)
- Health check endpoint to verify backend availability
- User registration endpoint
- Server-side validation of input fields
- JSON-based REST API design
- Prepared structure for database integration (future work)

### Frontend (HTML, CSS, JavaScript)
- Responsive voter registration form
- Modern UI with background image and blurred overlay
- Real-time client-side validation
- Visual feedback for errors (red) and success (green)
- SCC auto-converted to uppercase
- Date of Birth restriction (18+ eligibility)
- QR Code support:
  - Scan QR using device camera
  - Upload QR image file
- Professional styling aligned with government portals

---

##  Technology Stack

- **Backend:** Python 3.13, Flask
- **Frontend:** HTML5, CSS3, JavaScript (ES6)
- **QR Support:** html5-qrcode library
- **API Testing:** Postman
- **Version Control:** Git (dev & main branches)

---

##  Project Structure

```
mslr-referendum/
│
├── app.py
├── venv/
├── static/
│   ├── css/
│   │   └── style.css
│   ├── logo.png
│   └── bg.jpg
│
├── templates/
│   └── register.html
│
└── README.md
```

---

##  API Endpoints

### Health Check
```
GET /mslr/health
```

**Response**
```json
{
  "status": "UP",
  "service": "MSLR Referendum Backend"
}
```

---

### User Registration
```
POST /mslr/register
```

**Request Body**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "dob": "2000-05-10",
  "password": "securePassword",
  "scc": "A1B2C3D4E5"
}
```

---

##  Registration Rules

- Email must be valid
- Date of birth must indicate **18 years or older**
- SCC must be exactly **10 uppercase alphanumeric characters**
- Password handling prepared for hashing

---

##  Running the Application

```bash
venv\Scripts\activate
pip install flask html5-qrcode
python app.py
```

Access at:
```
http://127.0.0.1:9999/register
```

---

##  Testing

- APIs tested using Postman
- Frontend tested in browser
- QR scan and upload tested

---

##  Future Enhancements

- MySQL database integration
- Password hashing
- Login functionality
- Admin dashboard
- Cloud deployment

---

##  Academic Context

Developed for **Mobile and Web Applications Coursework** demonstrating:
- REST APIs
- Client-server interaction
- Secure input handling
- UI/UX best practices

---

##  Status

Backend working  
Frontend complete  
QR features implemented  
Ready for DB integration  
