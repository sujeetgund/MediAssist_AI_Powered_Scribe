# MediAssist — AI Medical Assistant (College Project)

A small Flask web app that demonstrates a medical expert-style AI assistant using Google's Generative AI (Gemini).
Designed for education and prototyping — not for clinical use.

## Key highlights
- Uses Google Gemini via `google.generativeai`.
- System-level prompt produces structured HTML for patient assessments and conservative treatment suggestions.
- Web UI with a simple POST /diagnose endpoint; returns HTML or JSON (for AJAX).

## Quick setup
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate (Windows) or source venv/bin/activate (macOS/Linux)
   pip install flask python-dotenv google-generativeai markdown
   ```

2. Add a `.env` file in the project root with:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash        # optional
   FLASK_RUN_HOST=127.0.0.1            # optional
   FLASK_RUN_PORT=5000                 # optional
   FLASK_DEBUG=True                    # optional
   ```

## Run
- Start the app:
  ```bash
  python app.py
  ```
- Open http://127.0.0.1:5000 in your browser.

## Endpoints
- **GET /** — show the UI (index.html).
- **POST /diagnose** — submit patient info. Accepts form-data or JSON and returns either rendered HTML or JSON payload.

## Example (form):
```bash
curl -X POST http://127.0.0.1:5000/diagnose \
  -F "name=John Doe" \
  -F "age=35" \
  -F "gender=Male" \
  -F "symptoms=Fever and sore throat for 3 days" \
  -F "allergies=None" \
  -F "current_medications=None" \
  -F "confirm=on"
```

## Example (JSON):
```bash
curl -X POST http://127.0.0.1:5000/diagnose \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane","symptoms":"Cough and sore throat","allergies":"None","current_medications":"None","confirm":true}'
```

## Security & privacy
- This app may collect personal health information. Use responsibly and do not deploy without proper data protections.
- The AI suggestions are NOT a medical diagnosis. Always consult a licensed healthcare professional for clinical decision-making.

## Disclaimer
- Educational / prototype project — not intended to replace medical professionals. For emergencies, call your local emergency services.

## Contributing
- Small, focused project. Fixes and improvements welcome — please open issues or PRs.

## License
- MIT License — see LICENSE (add one if needed).

