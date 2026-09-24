# HospitalFlow — Hospital Operations Intelligence

HospitalFlow is an operational decision-support web application designed to help hospital operations teams understand current pressure, anticipate near-term changes, identify bottlenecks, test operational scenarios, and evaluate possible actions.

The system follows a five-stage operational decision loop:

**MONITOR → PREDICT → EXPLAIN → SIMULATE → DECIDE**

HospitalFlow focuses on hospital operations such as waiting times, queues, resource utilization, departmental pressure, bed availability, and operational bottlenecks.

> **Scope:** HospitalFlow is an operational decision-support prototype. It is not a clinical diagnosis, treatment, patient-risk, or electronic medical-record system. The current demonstration dataset is synthetic and contains aggregate operational information rather than patient-level records.

---

# Features

## Monitor

### Overview
Provides a high-level operational view of the hospital, including:

- Overall hospital pressure
- Average waiting time
- Emergency waiting time
- Patients in the system
- Beds available
- Staff utilization
- Laboratory queue
- Radiology queue
- Discharges pending
- Live operational alerts
- Department-level operational status

### Hospital Flow

Visualizes operational flow across connected hospital departments and helps show how pressure can propagate through the system.

### Historical Trends

Provides historical operational analysis with:

- Department filtering
- Multiple time periods
- Pressure trends
- Average waiting-time trends
- Utilization trends
- Snapshot counts
- Peak pressure
- Current pressure
- Operational context

---

# Predict

## Forecast

Provides near-term operational forecasts for:

- Waiting times
- Queue pressure
- Department pressure
- Utilization
- Expected operational stress

The forecasting layer is intended to help operations teams understand what may happen next based on the current operational state.

---

# Explain

## Bottlenecks

Identifies operational factors contributing to pressure and bottlenecks.

The system connects operational conditions such as:

- Queue growth
- Waiting times
- Utilization
- Staffing
- Capacity
- Arrival pressure

to help explain why operational pressure is increasing.

---

# Simulate

## Simulation Lab

Allows users to test operational scenarios before applying an operational change.

Example scenario variables include:

- Arrival changes
- Staffing changes
- Processing capacity
- Department conditions

The system compares projected operational outcomes with the current state.

---

# Decide

## Insights

Provides operational insights based on the monitored, predicted, explained, and simulated state.

The purpose is to present operational trade-offs so that hospital operations teams can make informed decisions.

---

# Live Operational Feed

HospitalFlow includes a synthetic live operational simulator.

The simulator:

- Advances the hospital model automatically
- Advances one simulated 15-minute hospital interval per tick
- Runs automatically every 15 seconds by default
- Persists live operational snapshots in MongoDB
- Starts from the existing operational model state
- Supports manual ticks
- Supports start/stop controls
- Provides a future adapter boundary for external hospital systems

Live operational data is currently synthetic.

The application is **not connected to a real hospital system**.

---

# Real-Time Operational Alerts

HospitalFlow evaluates live operational snapshots against configurable operational thresholds.

Alerts can be generated for conditions including:

- Critical or high hospital pressure
- High waiting time
- High utilization
- Low bed availability
- High queue size

Alerts are stored in MongoDB.

A simulated-time cooldown prevents the same department and alert type from generating duplicate alerts on every live tick.

The application supports:

- Viewing open alerts
- Alert severity
- Alert timestamps
- Alert values and thresholds
- Alert acknowledgement

---

# WebSocket Live Dashboard

HospitalFlow uses WebSockets to connect the live operational feed to the dashboard.

The live UI provides:

- Live connection status
- Simulator status
- Hospital-time updates
- Automatic dashboard refresh after live ticks
- Live operational alerts
- Alert acknowledgement
- Live simulator status updates

WebSocket endpoint:

```text
/ws/live

REST APIs remain the source of truth for operational records and alerts.

Authentication

HospitalFlow includes a local authentication foundation using signed bearer tokens.

Users sign in with:

Username
Password

The authenticated application shell is protected from unauthenticated access.

Demo accounts

For local development:

Username	Password	Role
admin	admin123	Administrator
manager	manager123	Operations Manager
viewer	viewer123	Staff / Viewer

These are development/demo credentials only and must not be used for a real deployment.

Role-Based Access Control

HospitalFlow includes role-based access control.

Administrator

Administrator users have access to the full operational workspace and administrative capabilities.

This includes:

Monitor
Historical trends
Forecast
Bottlenecks
Simulation Lab
Insights
Live simulator controls
Alert acknowledgement
Administrative/external operational-data capabilities
Operations Manager

Operations Managers have access to the main operational decision-support workflow, including:

Monitor
Hospital Flow
Historical Trends
Forecast
Bottlenecks
Simulation Lab
Insights
Live simulator controls
Alert acknowledgement
Staff / Viewer

Staff / Viewer users receive a more restricted read-only operational view.

Access is focused on:

Overview
Hospital Flow
Historical Trends
Operational monitoring
Operational alerts

Restricted functionality is not exposed to users without the required permission.

Backend permission enforcement is used for protected functionality rather than relying only on hiding frontend navigation items.

Technology Stack
Frontend
React
Vite
React Router
JavaScript
CSS
Backend
Python
FastAPI
Uvicorn
Pydantic
PyJWT
Database
MongoDB
PyMongo
Development / Testing
Pytest
Git
GitHub
System Architecture
                         HospitalFlow
                              |
                              v
                +---------------------------+
                |      React Frontend       |
                +---------------------------+
                              |
                         REST / WebSocket
                              |
                              v
                +---------------------------+
                |       FastAPI Backend     |
                +---------------------------+
                    |        |        |
                    |        |        |
                    v        v        v
              Authentication  Live    Decision
                 + RBAC       Feed     Services
                    |          |          |
                    |          v          |
                    |      Alert Engine   |
                    |          |          |
                    +----------+----------+
                               |
                               v
                         MongoDB
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
      Operational History                 Live Snapshots
              |                                 |
              +----------------+----------------+
                               |
                               v
                         HospitalFlow
                               |
        MONITOR → PREDICT → EXPLAIN → SIMULATE → DECIDE
Operational Data Flow
Synthetic Hospital Model
          |
          v
   Live Feed Manager
          |
          +----------------------+
          |                      |
          v                      v
   Operational Data        Alert Evaluation
          |                      |
          v                      v
       MongoDB                Alerts
          |                      |
          +----------+-----------+
                     |
                     v
              FastAPI Backend
                     |
             REST / WebSocket
                     |
                     v
              React Dashboard
MongoDB

MongoDB is used as the persistence layer for operational history, live snapshots, and alerts.

Main database:

hospitalflow

Collections include:

hospitalflow
├── operational_snapshots
└── alerts

Operational snapshots contain aggregate information such as:

{
  "source": "live_simulator",
  "department_id": "emergency",
  "department_name": "Emergency",
  "timestamp": "...",
  "arrivals": 5,
  "served": 4,
  "queue_length": 6,
  "staff_planned": 8,
  "staff_on_duty": 8,
  "capacity": 5,
  "utilization": 0.8,
  "avg_wait_min": 42,
  "pressure": 0.23,
  "level": "LOW"
}

No patient identifiers are stored by the current prototype.

API
Authentication
POST /api/auth/login
GET  /api/auth/me
Dashboard
GET /api/dashboard
Live Operations
GET  /api/live/status
POST /api/live/start
POST /api/live/stop
POST /api/live/tick
POST /api/live/ingest
Historical Operations
GET /api/history/operational

Examples:

GET /api/history/operational?department_id=emergency
GET /api/history/operational?hours=48
GET /api/history/operational?source=live_simulator
Alerts
GET  /api/alerts
POST /api/alerts/{alert_id}/acknowledge
WebSocket
/ws/live
Future Hospital Data Integration

HospitalFlow has an ingestion boundary intended for future integration with real hospital systems.

Potential integration sources include:

Hospital Information Systems
Electronic Health Record operational feeds
Bed management systems
Laboratory systems
Radiology systems
Registration/queue systems
Workforce systems
Hospital APIs

Potential interoperability standards include:

FHIR
HL7 v2
Vendor APIs
Secure aggregate data feeds

The current implementation provides the adapter boundary through:

POST /api/live/ingest

A real deployment would require hospital-specific integration, authentication, authorization, security controls, data mapping, validation, monitoring, and operational approval.

Configuration

Default MongoDB configuration:

mongodb://localhost:27017

Optional environment variables:

HOSPITALFLOW_MONGODB_URI=mongodb://localhost:27017

HOSPITALFLOW_MONGODB_DATABASE=hospitalflow

HOSPITALFLOW_MONGODB_SERVER_SELECTION_TIMEOUT_MS=1500

HOSPITALFLOW_MONGODB_CONNECT_TIMEOUT_MS=1500

HOSPITALFLOW_LIVE_SIMULATOR_ENABLED=true

HOSPITALFLOW_LIVE_INTERVAL_SECONDS=15

HOSPITALFLOW_LIVE_HOSPITAL_INTERVAL_MIN=15

Authentication configuration:

HOSPITALFLOW_AUTH_SEED_DEMO=true

HOSPITALFLOW_AUTH_SECRET=<strong-secret>

For a real deployment:

HOSPITALFLOW_AUTH_SEED_DEMO=false

and a strong secret should be supplied through environment configuration.

Local Development
Requirements

Install:

Python 3.x
Node.js / npm
MongoDB Server
Git

MongoDB Compass can be used as the graphical interface for inspecting the database, but MongoDB Server must also be running.

1. Start the Backend

From the project root:

.\.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Start FastAPI:

python -m uvicorn backend.main:app --reload --port 8000

The API will be available at:

http://localhost:8000

API documentation:

http://localhost:8000/docs

Health check:

http://localhost:8000/api/health
2. Start the Frontend

Open another terminal:

cd frontend
npm install
npm run dev

The frontend will normally be available at:

http://localhost:5173
Project Structure
hospitalflow/
│
├── backend/
│   │
│   ├── api/
│   │   ├── alerts.py
│   │   ├── auth.py
│   │   ├── bottlenecks.py
│   │   ├── dashboard.py
│   │   ├── departments.py
│   │   ├── forecast.py
│   │   ├── history.py
│   │   ├── insights.py
│   │   ├── live.py
│   │   └── simulation.py
│   │
│   ├── db/
│   │   └── mongo.py
│   │
│   ├── data/
│   │
│   ├── models/
│   │   └── schemas.py
│   │
│   ├── services/
│   │   ├── alerts.py
│   │   ├── auth.py
│   │   ├── bottlenecks.py
│   │   ├── dashboard.py
│   │   ├── data_generator.py
│   │   ├── data_service.py
│   │   ├── forecast.py
│   │   ├── history.py
│   │   ├── hospital_model.py
│   │   ├── insights.py
│   │   ├── live_feed.py
│   │   ├── metrics.py
│   │   └── simulation.py
│   │
│   ├── config.py
│   ├── main.py
│   └── __init__.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── tests/
│
├── .gitignore
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── README.md
Development Roadmap
Phase 1–7
Core HospitalFlow decision-support experience
        |
        v
8A — MongoDB foundation
        |
        v
8B — Database-backed operational history
        |
        v
8C — Live operational feed / simulator
        |
        v
8D — Real-time operational alerts
        |
        v
8E — WebSocket live dashboard
        |
        v
8F — Historical trend analysis + UI polish
        |
        v
9A — Authentication foundation
        |
        v
9B — Role-based access control
        |
        v
10 — Real hospital / FHIR / HL7 integrations
        |
        v
11 — Production security, reliability and deployment hardening
Phase Status
Phase	Feature	Status
1–7	Core HospitalFlow experience	Completed
8A	MongoDB foundation	Completed
8B	Operational history	Completed
8C	Live operational feed	Completed
8D	Real-time alerts	Completed
8E	WebSocket live UI	Completed
8F	Historical trends + UI polish	Completed
9A	Authentication foundation	Completed
9B	Role-based access control	Completed
10	Real hospital integrations	Future
11	Production hardening	Future
Security and Scope

HospitalFlow is currently a prototype intended for demonstration and development.

The current project:

Uses synthetic operational data
Does not store patient-level identifiers
Does not perform clinical diagnosis
Does not recommend medical treatment
Does not replace an Electronic Health Record
Is not connected to a real hospital
Is not certified or approved for clinical use

Production deployment would require additional security and operational controls including:

Strong authentication configuration
Secure secret management
HTTPS/TLS
Production database configuration
Access control review
Audit logging
Monitoring
Backup and recovery
Hospital-specific integration controls
Data governance
Security testing
Deployment hardening
Hackathon Project

HospitalFlow demonstrates how hospital operations can be treated as a connected operational system rather than isolated departmental metrics.

The core decision loop is:

MONITOR
   ↓
What is happening now?
   ↓
PREDICT
   ↓
What is likely to happen next?
   ↓
EXPLAIN
   ↓
Why is it happening?
   ↓
SIMULATE
   ↓
What happens if we act?
   ↓
DECIDE
   ↓
Which operational action should be considered?

The goal is to give hospital operations teams a unified view of operational pressure and its potential consequences.

License

This project was developed as a hackathon/prototype project.

Add an appropriate open-source license here if the project is intended to be publicly reused.
