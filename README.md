# FluxCloud Revenue Dashboard

A simple dashboard for tracking FluxCloud application deployments, including:
- Total number of apps
- Marketplace vs Custom app counts
- Top 5 most deployed Marketplace apps

This project uses:
- **Python + Flask** for the backend API
- **Static HTML/JS** frontend
- Designed to be deployed on **Orbit (RunOnFlux)**

---

## 📁 Project Structure

- backend/
  - app.py # Flask API exposing /stats
  - analyze_fluxcloud.py # Standalone analysis script
  - requirements.txt # Python dependencies

- frontend/
  - index.html # Basic dashboard UI
  - styles.css # Minimal styling
  - app.js # Fetches /stats and updates UI

---

## 🚀 Backend Setup

### Install dependencies
```bash
cd backend
pip install -r requirements.txt
