# IT Admin Dashboard

A modern, real-time IT administration dashboard for monitoring devices, managing VPNs, Active Directory integration, printers, and network alerts.

Built with **FastAPI** (backend) + **React 19 + TypeScript + Vite** (frontend). Designed for IT admins who need SNMP monitoring, WebSocket real-time updates, Teams alerts, and easy self-hosting.

![Dashboard Screenshot](screenshot.png) <!-- Add your screenshot here later -->

## Features
- Real-time device monitoring (CPU, RAM, latency, status via SNMP)
- VPN user management, connection history & alerts
- Active Directory settings & integration
- Printer management
- Background monitoring tasks + WebSocket updates
- Alerting (Teams webhook ready)
- Responsive dashboard UI with charts

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy (async), Pydantic, python-jose (JWT), pysnmp, Alembic
- **Frontend**: React 19, TypeScript, Vite, TanStack Query, Recharts, Lucide icons, Axios
- **Database**: SQLite (dev) – Postgres supported in future
- **Deployment**: Docker Compose + Nginx (coming soon)

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### Backend
```bash
cd backend
cp .env.example .env          # edit JWT secret, paths, etc.
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000