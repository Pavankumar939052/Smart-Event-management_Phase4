# SmartEvent – Event Discovery \& Ticket Booking System

## Project Overview

SmartEvent is a full-stack event discovery and ticket booking application built using **FastAPI** for the backend and **React + Vite** for the frontend. Users can discover events, book tickets, make simulated payments, apply coupons, submit reviews, receive notifications, and manage digital QR tickets.

## Technologies Used

**Backend**

* Python, FastAPI, SQLAlchemy, SQLite
* Pydantic, JWT Authentication, bcrypt
* Uvicorn, QRCode

**Frontend**

* React, Vite, JavaScript, Axios
* React Router DOM, CSS
* Framer Motion (optional)

## Features

### Phase 1 – Core Application

1. **User Authentication:** Registration, login, JWT authentication, and protected routes.
2. **Event Discovery:** Browse events, view details, and search by title.
3. **Ticket Booking:** Select ticket quantities, calculate booking totals, and view booking history.
4. **Digital Tickets:** Generate and display QR tickets for eligible bookings.
5. **Notifications:** View booking notifications and manage read status.
6. **React Frontend:** Responsive pages for login, registration, events, bookings, tickets, and notifications.

### Phase 2 – Advanced Features

**Module 12: Payment System**

* Simulated payments, transaction IDs, payment status, and booking updates.

**Module 13: Coupon \& Discount System**

* Percentage and fixed discounts, expiry validation, usage limits, and final amount calculation.

**Module 14: Event Reviews \& Ratings**

* Submit ratings and reviews, display event feedback, and enforce review permissions.

**Module 15: Notification System**

* Notification dropdown, history, unread counts, and read-status management where implemented.

**Module 16: Event Search, Filtering \& Sorting**

* Search by title, filter by category, location, and date, and sort by date, price, or popularity.

**Module 17: Professional UI/UX Improvements**

* Modern navbar, mobile navigation, responsive event cards, smooth transitions, improved booking flow, and loading/error states.

## Project Structure

```text
Smart\\\_Event/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py   
|   |   |── config.py
|   |   |── dependencies.py
│   │   ├── routes/
│   │   |── services/
|   |   |── static/
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.jsx
│   │   |── main.jsx
│   │   ├── api.js
│   │   ├── App.css
│   │   └── index.css
|   |
|   |
│   └── package.json
└── README.md
```

*Additional files and routes may exist in the local project.*

## Installation and Setup

### 1\. Start the Backend

From the project root in PowerShell:

```powershell
cd backend
..\\\\.venv\\\\Scripts\\\\Activate.ps1
python -m uvicorn app.main:app --reload
```

Backend: `http://127.0.0.1:8000`

Swagger UI: `http://127.0.0.1:8000/docs`

### 2\. Start the Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

### 3\. Test the Application

* Register and log in.
* Browse, search, filter, and sort events.
* Create a booking and test coupon validation.
* Test simulated payment success and failure.
* Verify bookings, tickets, QR codes, and notifications.
* Test reviews and permissions where implemented.
* Test mobile responsiveness.
* Run `npm run build` in the frontend directory.

## Security

* JWT-based authentication
* Password hashing
* Protected routes and role permissions where configured
* Booking and ticket ownership validation
* Backend validation of payments and discounts

## Important Notes

* Payments are simulated; real money is not processed.
* Keep secret keys and credentials out of public repositories.
* Preserve existing database records during development.
* Mark features as completed only after testing them.

## Conclusion

SmartEvent demonstrates full-stack development using FastAPI, React, SQLAlchemy, and SQLite. Modules 12–17 extend the core application with payments, discounts, reviews, notifications, advanced event discovery, and professional UI/UX improvements.

**Technology:** FastAPI + React + Vite + SQLAlchemy + SQLite + JWT

