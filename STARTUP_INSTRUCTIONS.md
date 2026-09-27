# How to Start the SwasthiQ Website

## Prerequisites
1. Python 3.14+ installed
2. Node.js installed (for frontend)
3. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Setup (One-time)

1. **Clone/extract the project** to your local machine

2. **Install dependencies**:
   ```bash
   # Backend dependencies
   pip install -r requirements.txt
   
   # Frontend dependencies
   cd frontend
   npm install
   cd ..
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env file and add your Gemini API key:
   # GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

## Starting the Website

### Option 1: Recommended - Separate Terminals

**Terminal 1 - Start Backend API:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
You should see: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```
You should see: `VITE v5.2.0  ready in X ms` and `Local: http://localhost:5173`

### Option 2: Single Command (if you have concurrently installed)
```bash
# Install globally if needed: npm install -g concurrently
concurrently "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" "cd frontend && npm run dev"
```

## Using the Website

1. Open your browser to: `http://localhost:5173`
2. Use the date selector in the top-right to choose:
   - **July 25, 2026** (Refund Day)
   - **July 26, 2026** (Empty Day)
   - **July 27, 2026** (Normal Day)
3. View the AI-generated narrative in the "Generated Narrative" section
4. See the traced figures in the "Traced Figures" panel showing the source data points

## Troubleshooting

- **If you see "is not valid JSON" errors**: 
  - Make sure your `.env` file contains a valid `GEMINI_API_KEY`
  - Restart both servers after updating the .env file
  
- **If the backend fails to start**:
  - Check that port 8000 is available
  - Verify Python dependencies are installed: `pip install -r requirements.txt`
  
- **If the frontend fails to start**:
  - Check that Node.js is installed
  - Verify frontend dependencies: `cd frontend && npm install`

## API Endpoint
The backend API is available at: `http://localhost:8000/api/v1/reports`
Accepts POST requests with billing log data (JSON array).

## Features
- AI-generated clinic narratives suitable for WhatsApp sharing
- Traced figures showing exactly which data points were used
- Automatic validation error reporting
- Date selection for different sample datasets
- Responsive design

## Note on LLM Configuration
If you don't configure a Gemini API key, the system will use template-based narratives as a fallback. To use AI-generated narratives, you must provide a valid Gemini API key in the `.env` file.