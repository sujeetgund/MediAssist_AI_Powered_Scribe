import os
import time
import uuid
import csv
import json
import logging
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import google.generativeai as genai
from dotenv import load_dotenv
from functools import wraps

# --- CONFIGURATION ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_super_secret_key_change_in_production")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logging.warning("WARNING: GEMINI_API_KEY not found in .env")

genai.configure(api_key=api_key)

# --- IN-MEMORY DATABASES ---

# Doctor Database
DOCTOR_DB = {
    "dr_smith": {
        "id": "dr_smith",
        "name": "Dr. James Smith",
        "specialty": "General Medicine",
        "password": "smith123",
        "email": "smith@mediassist.com"
    },
    "dr_patel": {
        "id": "dr_patel",
        "name": "Dr. Rajesh Patel",
        "specialty": "Internal Medicine",
        "password": "patel123",
        "email": "patel@mediassist.com"
    },
    "dr_lee": {
        "id": "dr_lee",
        "name": "Dr. Sarah Lee",
        "specialty": "Infectious Diseases",
        "password": "lee123",
        "email": "lee@mediassist.com"
    }
}

# Patient Database
PATIENT_USER_DB = {
    "patient1": {
        "id": "patient1",
        "name": "John Doe",
        "password": "p123",
        "email": "john@example.com"
    }
}

# Case Database (stores all submissions)
CASE_DB = {}

# --- AI PROMPT (Dual-View JSON Architecture) ---
# This prompts the AI to act as both a patient educator and a clinical scribe.
SYSTEM_PROMPT = """
ACT AS: Senior Clinical Consultant & Medical Scribe.
TASK: Analyze patient intake data and generate a structured clinical case file.

LANGUAGE INSTRUCTION: 
- "patient_view" MUST be in {language}. (Translate concepts to be culturally relevant).
- "doctor_view" MUST be in ENGLISH (Standard Medical Terminology).

OUTPUT FORMAT: Return ONLY valid JSON matching this schema:
{{
  "patient_view": {{
    "summary": "Warm, reassuring explanation in {language}.",
    "pathophysiology": "Simple analogy explaining the mechanism in {language}.",
    "care_plan": ["Step 1 in {language}", "Step 2 in {language}"],
    "red_flags": ["Urgent sign 1 in {language}", "Urgent sign 2 in {language}"]
  }},
  "doctor_view": {{
    "subjective": "Professional medical terminology summary of HPI in ENGLISH.",
    "objective": "Concise summary of reported vitals in ENGLISH.",
    "assessment": "Differential diagnosis ranked by probability in ENGLISH.",
    "plan": "Suggested pharmacotherapy, diagnostics, and follow-up in ENGLISH."
  }},
  "safety": {{
    "is_safe": true,
    "warnings": []
  }}
}}

SAFETY RULES:
- Check for Drug-Allergy interactions (e.g., Penicillin allergy vs Amoxicillin).
- Check for Contraindications based on age/history.
- If unsafe, set "is_safe": false and add warnings (in English).
"""

# --- HELPER FUNCTIONS ---

def log_interaction(case_id, inputs, latency):
    """MLOps: Logs inference data for monitoring latency and drift."""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "case_id": case_id,
            "model": "gemini-2.5-flash",
            "latency_ms": round(latency * 1000, 2),
            "symptoms_snippet": inputs.get('symptoms', '')[:50]
        }
        logging.info(f"MLOPS LOG: {json.dumps(log_entry)}")
        
        csv_file = 'clinical_logs.csv'
        file_exists = os.path.isfile(csv_file)
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=log_entry.keys())
            if not file_exists: 
                writer.writeheader()
            writer.writerow(log_entry)
    except Exception as e:
        logging.error(f"Logging Error: {e}")

def clean_medical_text(text):
    """Remove markdown brackets and format text for readability."""
    if not text:
        return ""
    
    text = re.sub(r'\[\*\*', '', text)
    text = re.sub(r'\*\*\]', '', text)
    text = re.sub(r'\[\*', '', text)
    text = re.sub(r'\*\]', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    
    return text.strip()

def extract_diagnosis(assessment_text):
    """Extract the most probable diagnosis from assessment text."""
    if not assessment_text:
        return "Pending clinical evaluation"
    
    parts = assessment_text.split('\n')
    for part in parts:
        part = part.strip()
        if part and not part.startswith('-'):
            part = re.sub(r'^[\d\.\-\*]+\s*', '', part).strip()
            if len(part) > 10:
                return part
    
    return assessment_text.split('\n')[0] if assessment_text else "Pending clinical evaluation"

def format_soap_as_list(text):
    """Convert paragraph text into a structured list format."""
    if not text:
        return []
    
    items = []
    numbered = re.split(r'\n\d+\.\s+', text)
    
    if len(numbered) > 1:
        for item in numbered[1:]:
            item = item.strip()
            items.append(item)
    else:
        bullets = re.split(r'\n[\-\*]\s+', text)
        if len(bullets) > 1:
            for item in bullets[1:]:
                item = item.strip()
                items.append(item)
        else:
            sentences = re.split(r'\n|(?<=[.!?])\s+', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:
                    items.append(sentence)
    
    return items if items else [text]

def login_required(f):
    """Decorator to check if user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'role' not in session:
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function

def patient_required(f):
    """Decorator to check if logged-in user is a patient."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'patient':
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    """Decorator to check if logged-in user is a doctor."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'doctor':
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def landing():
    """Landing page - role selection."""
    if 'user_id' in session:
        if session['role'] == 'patient':
            return redirect(url_for('patient_intake'))
        elif session['role'] == 'doctor':
            return redirect(url_for('doctor_dashboard'))
    return render_template('landing.html')

# --- PATIENT ROUTES ---

@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    """Patient login page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in PATIENT_USER_DB and PATIENT_USER_DB[username]['password'] == password:
            session['user_id'] = username
            session['role'] = 'patient'
            session['name'] = PATIENT_USER_DB[username]['name']
            return redirect(url_for('patient_intake'))
        else:
            flash("Invalid username or password", "danger")
    
    return render_template('patient_login.html')

@app.route('/patient/intake')
@login_required
@patient_required
def patient_intake():
    """Patient intake form."""
    doctors = [{"id": doc_id, "name": doc['name'], "specialty": doc['specialty']} 
               for doc_id, doc in DOCTOR_DB.items()]
    return render_template('intake.html', doctors=doctors)

@app.route('/patient/submit', methods=['POST'])
@login_required
@patient_required
def patient_submit():
    """Process patient intake submission."""
    start_time = time.time()
    try:
        case_id = str(uuid.uuid4())[:8].upper()
        selected_language = request.form.get('language', 'English')
        doctor_id = request.form.get('doctor_id')
        
        if not doctor_id or doctor_id not in DOCTOR_DB:
            return render_template('intake.html', 
                                 doctors=[{"id": doc_id, "name": doc['name'], "specialty": doc['specialty']} 
                                         for doc_id, doc in DOCTOR_DB.items()],
                                 error="Please select a doctor")
        
        raw_data = {
            "id": case_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "patient_id": session.get('user_id'),
            "patient_name": session.get('name'),
            "doctor_id": doctor_id,
            "doctor_name": DOCTOR_DB[doctor_id]['name'],
            "name": request.form.get('name'),
            "age": request.form.get('age'),
            "gender": request.form.get('gender'),
            "weight": request.form.get('weight'),
            "height": request.form.get('height'),
            "temp": request.form.get('temperature'),
            "bp": request.form.get('blood_pressure'),
            "duration": request.form.get('duration'),
            "allergies": request.form.get('allergies') or "None",
            "current_meds": request.form.get('current_medications') or "None",
            "history": request.form.get('medical_history') or "None",
            "severity": request.form.get('severity'),
            "symptoms": request.form.get('symptoms'),
            "notes": request.form.get('other_notes'),
            "language": selected_language
        }

        # 4. AI Processing (Single-Shot Agentic Call)
        model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
        formatted_prompt = SYSTEM_PROMPT.format(language=selected_language)
        
        prompt = f"""
        {formatted_prompt}
        
        PATIENT DATA:
        Name: {raw_data['name']} ({raw_data['age']}y {raw_data['gender']})
        Vitals: T:{raw_data['temp']} BP:{raw_data['bp']}
        Allergies: {raw_data['allergies']}
        Meds: {raw_data['current_meds']}
        History: {raw_data['history']}
        Chief Complaint: {raw_data['symptoms']} (Duration: {raw_data['duration']}, Severity: {raw_data['severity']})
        Notes: {raw_data['notes']}
        Original Language Input: {selected_language}
        """
        
        response = model.generate_content(prompt)
        ai_analysis = json.loads(response.text)

        # 5. Clean up AI response text (remove brackets and format)
        if 'patient_view' in ai_analysis:
            ai_analysis['patient_view']['summary'] = clean_medical_text(ai_analysis['patient_view']['summary'])
            ai_analysis['patient_view']['pathophysiology'] = clean_medical_text(ai_analysis['patient_view']['pathophysiology'])
            ai_analysis['patient_view']['care_plan'] = [clean_medical_text(item) for item in ai_analysis['patient_view'].get('care_plan', [])]
            ai_analysis['patient_view']['red_flags'] = [clean_medical_text(item) for item in ai_analysis['patient_view'].get('red_flags', [])]
            ai_analysis['patient_view']['primary_diagnosis'] = extract_diagnosis(ai_analysis['doctor_view'].get('assessment', ''))

        if 'doctor_view' in ai_analysis:
            ai_analysis['doctor_view']['subjective'] = clean_medical_text(ai_analysis['doctor_view']['subjective'])
            ai_analysis['doctor_view']['objective'] = clean_medical_text(ai_analysis['doctor_view']['objective'])
            ai_analysis['doctor_view']['assessment'] = clean_medical_text(ai_analysis['doctor_view']['assessment'])
            ai_analysis['doctor_view']['plan'] = clean_medical_text(ai_analysis['doctor_view']['plan'])
            ai_analysis['doctor_view']['subjective_list'] = format_soap_as_list(ai_analysis['doctor_view']['subjective'])
            ai_analysis['doctor_view']['objective_list'] = format_soap_as_list(ai_analysis['doctor_view']['objective'])
            ai_analysis['doctor_view']['assessment_list'] = format_soap_as_list(ai_analysis['doctor_view']['assessment'])
            ai_analysis['doctor_view']['plan_list'] = format_soap_as_list(ai_analysis['doctor_view']['plan'])

        CASE_DB[case_id] = {
            "raw_data": raw_data,
            "ai_analysis": ai_analysis
        }

        latency = time.time() - start_time
        log_interaction(case_id, raw_data, latency)
        
        return redirect(url_for('patient_result', case_id=case_id))

    except Exception as e:
        logging.error(f"Error processing case: {e}")
        doctors = [{"id": doc_id, "name": doc['name'], "specialty": doc['specialty']} 
                   for doc_id, doc in DOCTOR_DB.items()]
        return render_template('intake.html', doctors=doctors, error=f"System Error: {str(e)}")

@app.route('/patient/result/<case_id>')
@login_required
@patient_required
def patient_result(case_id):
    """Patient view of results."""
    case = CASE_DB.get(case_id)
    if not case:
        return "Case not found or expired.", 404
    return render_template('patient_result.html', case=case)

@app.route('/patient/logout')
def patient_logout():
    """Patient logout."""
    session.clear()
    flash("You have been logged out successfully", "success")
    return redirect(url_for('landing'))

# --- DOCTOR ROUTES ---

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    """Doctor login page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in DOCTOR_DB and DOCTOR_DB[username]['password'] == password:
            session['user_id'] = username
            session['role'] = 'doctor'
            session['name'] = DOCTOR_DB[username]['name']
            return redirect(url_for('doctor_dashboard'))
        else:
            flash("Invalid username or password", "danger")
    
    return render_template('doctor_login.html')

@app.route('/doctor/dashboard')
@login_required
@doctor_required
def doctor_dashboard():
    """Doctor dashboard - shows assigned cases only."""
    doctor_id = session.get('user_id')
    
    # Filter cases for this doctor
    doctor_cases = [case for case in CASE_DB.values() 
                    if case['raw_data']['doctor_id'] == doctor_id]
    
    # Sort by newest first
    sorted_cases = sorted(doctor_cases, key=lambda x: x['raw_data']['timestamp'], reverse=True)
    
    doctor_info = DOCTOR_DB.get(doctor_id)
    return render_template('doctor_dashboard.html', cases=sorted_cases, doctor=doctor_info)

@app.route('/doctor/view/<case_id>')
@login_required
@doctor_required
def doctor_view(case_id):
    """Doctor view of SOAP note."""
    doctor_id = session.get('user_id')
    case = CASE_DB.get(case_id)
    
    if not case:
        return "Case not found", 404
    
    # Verify doctor has access to this case
    if case['raw_data']['doctor_id'] != doctor_id:
        flash("You don't have access to this case", "danger")
        return redirect(url_for('doctor_dashboard'))
    
    return render_template('doctor_view.html', case=case)

@app.route('/doctor/logout')
def doctor_logout():
    """Doctor logout."""
    session.clear()
    flash("You have been logged out successfully", "success")
    return redirect(url_for('landing'))

if __name__ == '__main__':
    app.run(debug=True)