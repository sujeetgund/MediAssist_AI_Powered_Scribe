# 🏥 MediAssist — AI-Powered Clinical Scribe & Patient Communication System

MediAssist is a full-stack, role-based medical documentation system that converts raw patient symptoms into **dual-purpose clinical intelligence**.
Using **Google Gemini**, it produces:

1. **Empathetic, localized patient summaries** (Hindi/English)
2. **Structured clinical SOAP notes** for physicians

This system bridges the communication gap between patients and doctors while preserving clinical accuracy, trust, and documentation efficiency.

---

## ❗ The Core Problem

Modern healthcare suffers from **documentation overload**. Physicians spend a significant portion of their day typing clinical notes, decreasing face-to-face time with patients. Meanwhile, patients may struggle to understand overly technical medical wording, especially in multilingual environments.

**Challenge:**
How do we augment clinical workflows with AI **without reducing patient trust or compromising medical accuracy**?

---

## 🚀 MediAssist — Engineering-Driven Solution

MediAssist introduces a **Dual-Agent Scribe Architecture**:

### 🔹 1. Dual-View Generation

Gemini generates *two* synchronized outputs from a single intake:

* **Patient View:** Plain-language, warm, localized summary (Hindi or English)
* **Doctor View:** Formal SOAP note (always English)

This separation preserves empathy for the patient while ensuring clinical rigor for physicians.

### 🔹 2. Persistent Case Storage (Local MLOps)

The application maintains historical case records using lightweight CSV databases:

* **users.csv** — Authentication + RBAC
* **cases.csv** — Case metadata, raw input, AI output

Structured fields allow doctors to revisit cases and enable reproducible AI behavior.
(Initialized automatically at first run.) 

### 🔹 3. Strict JSON Medical Prompting

A robust JSON-schema prompt enforces:

* Deterministic AI output
* Bilingual support
* Medical safety fields
* Full SOAP structure

This avoids hallucinations and formatting issues while keeping downstream parsing predictable.

### 🔹 4. Role-Based Access Control (RBAC)

* Patients submit cases
* Doctors only see cases **explicitly assigned** to them
* Flask sessions secure access boundaries

### 🔹 5. Multi-Language Communication (i18n)

The patient-facing output adapts to:

* **Hindi**
* **English**

Allowing culturally contextual care summaries and improved patient comprehension.

---

# 🧩 System Architecture Overview

```
Patient Intake → JSON Prompt → Gemini Model → AI Dual Output
       ↓                                   ↓
   Raw Data Saved                    SOAP Note + Summary
       ↓                                   ↓
 CSV Persistence                   Doctor Dashboard View
```

**Key Components (from code):**

* Flask backend with session-based auth
* Gemini 2.5 Flash model for real-time generation
* Automatic log creation (`clinical_logs.csv`) for latency + MLOps metadata
* UUID-based case tracking
* Secure password hashing with Werkzeug


---

# 🛠️ Features (Engineering Breakdown)

| Feature                       | Description                                    | Tech Keywords                             |
| ----------------------------- | ---------------------------------------------- | ----------------------------------------- |
| **Dual-Language Scribing**    | Patient summary (localized) + Doctor SOAP note | Prompt Engineering, NLP, Agentic Workflow |
| **CSV-Based Local DB**        | Cases + user accounts stored persistently      | MLOps Lite, CSV Persistence, Logging      |
| **RBAC System**               | Doctors only see their assigned cases          | Flask Auth, Secure Sessions               |
| **Case History & Versioning** | All AI outputs logged and reproducible         | Audit Trails, MLOps Logging               |
| **Localization**              | Hindi/English toggle                           | i18n, Cross-Cultural UX                   |
| **Fully Structured Output**   | JSON-schema ensures reliable downstream usage  | Structure Enforcement, Safety Fields      |

---

# ▶️ Running the Project Locally

## **1. Prerequisites**

* Python 3.9+
* Google Gemini API Key (from Google AI Studio)

---

## **2. Installation**

Clone and enter the project:

```bash
git clone https://github.com/garvit-010/MediAssist_AI_Powered_Scribe.git
cd MediAssist
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate     # Mac/Linux
venv\Scripts\activate        # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## **3. Environment Setup**

Create a `.env` file:

```
GEMINI_API_KEY="YOUR_KEY"
FLASK_SECRET_KEY="ANY_RANDOM_SECURE_KEY"
```

---

## **4. Initialize Data**

Run once to auto-create CSVs + demo accounts:

```bash
python app.py
```

Demo credentials (preloaded in CSVs) :

| Role    | Username | Password |
| ------- | -------- | -------- |
| Patient | patient1 | p123     |
| Doctor  | dr_smith | smith123 |
| Doctor  | dr_patel | patel123 |

---

# 🧪 Demo Workflow

### **1. Patient Login**

Visit `/patient/login` → login as **patient1 / p123**

### **2. Submit Symptoms**

Fill patient details and choose a doctor (e.g., *Dr. Patel*).

### **3. AI Processing**

System generates:

* Patient summary (Hindi or English)
* Doctor SOAP note

### **4. Doctor Review**

Logout → login as **dr_patel / patel123**

Doctor dashboard will show:

* Assigned case
* Timestamp
* AI-generated SOAP note

---

# 📸 UI Previews (Suggested Placement)

**Image 1 – Intake Form (Hindi Mode)**
*Dual-language form dynamically adapting UI text*

**Image 2 – Doctor Dashboard (Case Queue)**
*Case listing with timestamps and status*

**Image 3 – Clinical SOAP Note View**
*Structured Subjective, Objective, Assessment, Plan sections*

---

# 🛣️ Future Roadmap

### 🔧 1. Full MLOps Integration

* Replace CSV with MLflow/DVC
* Track prompts, outputs, latencies, model versions

### ⚡ 2. Asynchronous Tasks

Long-running Gemini calls → move to:

* Redis + Celery workers
* Non-blocking UI updates

### 🎨 3. Frontend Improvements

* Multi-language UI polish
* Better RTL/LTR handling
* Dynamic symptom suggestions

### 🗄️ 4. Database Migration

Move from CSV → PostgreSQL or Firebase for:

* Scalability
* Concurrent users
* Secure medical record storage

---

# 📜 License

MIT License — free for modification and commercial use.

---
