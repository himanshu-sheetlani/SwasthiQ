<p align="center">
<img src="https://hr.swasthiq.com/files/swasthiq-mark.png" alt="SwasthiQ Logo" width="120"/>
</p>

# SwasthiQ – Clinic Management System with LLM Narrative Layer

## Description
SwasthiQ processes billing logs, generates deterministic financial reports, and augments them with LLM‑produced narratives suitable for WhatsApp. All numbers in the narrative are traced to the deterministic report.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic
- **LLM**: Google Gemini API (generativeai) – configured via env vars
- **Frontend**: React 19, Vite, Recharts, Axios
- **Styling**: CSS, primary colour #175AD9
- **Testing**: Pytest (backend)

## Setup
1. Clone repo.
2. Backend: `pip install -r requirements.txt`
3. Frontend: `cd frontend && npm install && cd ..`
4. (Optional) Add `GEMINI_API_KEY` to `.env` (copy from `.env.example`).
5. Start backend: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
6. Start frontend: `cd frontend && npm run dev`
7. Open http://localhost:5173.

## API
POST `/api/v1/reports`  
- Input: JSON array of billing records (as per `BillingRecord` model).  
- Output:
  ```json
  {
    "report": {
      "reconciliation": { ... },
      "analytics": { ... }
    },
    "llm_narrative": {
      "narrative": "string",
      "traced_figures": [
        {"display_value":"string","report_field":"string","value":number}
      ],
      "source":"llm"|"fallback"
    },
    "validation_errors": [ ... ] // optional
  }
  ```
All monetary values are integer paise in `reconciliation` and `analytics`; `display_value` is formatted rupees.

## Architecture
- **Deterministic layer**: `repository.py` (in‑memory store), `reconciliation.py` (totals, payment‑mode breakdown), `analytics.py` (hourly revenue, peak hour, medicine rankings).
- **LLM layer**: `llm_narrative.py` – validates config, calls Gemini, validates response, falls back to template.
- **Route**: `api/v1/reports.py` – validation, calls services, returns JSON.
- **Frontend**: fetches JSON files from `public/sample_billing_dataset/` and posts to `/api/v1/reports`; displays narrative and traced figures; Analytics shows revenue chart (absolute bar height) and two‑column medicine tables.

## Testing
Run backend tests:
```bash
python -m pytest app/tests/ -v
```
Expected: 14 passed.

## Deployment
- Backend: run `uvicorn app.main:app --host 0.0.0.0 --port 8000` (without `--reload` for prod).
- Frontend: `npm run build` serves static assets from `frontend/dist/`.
- Ensure `GEMINI_API_KEY` env var is set if AI narratives desired; otherwise fallback narrative is used.
- No external database required for assignment (in‑memory repository).

## Notes
- All money handled as integer paise internally.
- LLM never alters deterministic data; traced figures are validated before return.