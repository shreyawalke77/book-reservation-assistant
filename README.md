# Book Reservation Assistant (AI Agent)
**CIE-3 Skill-Based Assignment: Generative AI, Large Language Models & Agentic AI**

---

## 📌 Project Overview
The **Book Reservation Assistant** is an autonomous conversational agent designed for academic libraries. It facilitates natural language book search, syllabus-aligned recommendations, real-time inventory checks, slot-filling reservation workflows, reservation tracking, and cancellations—without fabricating details or halluncinating inventory.

### Key Highlights
- **Palette Compliance:** Custom aesthetic using **Forest Green**, **Warm Amber**, **Sage**, and **Sandstone Parchment** (strictly **zero blue colors** used).
- **Agentic Architecture:** Explicit separation of intents, multi-turn state tracking, slot filling with validation, and autonomous tool calling (`search_books`, `check_availability`, `recommend_books`, `create_reservation`, `get_reservation_status`, `cancel_reservation`).
- **Real-Time Data Sync:** Dual SQLite relational tables (`books` and `reservations`) with instant UI updates on holds and cancellations.
- **Agent Telemetry:** Built-in collapsible reasoning drawer displaying agent thoughts and tool arguments/results in real-time.

---

## 🚀 How to Run the Working Prototype

### 1. Requirements
- Python 3.10+ (Python 3.12 verified)
- Flask

### 2. Launch the Application
Open PowerShell or your command prompt in this directory:
```powershell
python app.py
```

### 3. Open in Browser
Navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Quick Test Scenarios (CIE-3 Demonstration)

1. **Test 1 - Search & Availability:**
   - Type or click: `Is Clean Code available right now?`
   - *Observation:* Agent calls `check_availability`, returns Rack `B-04`, status `Available`.
2. **Test 2 - Recommendations:**
   - Type: `Recommend good books for learning Python`
   - *Observation:* Agent calls `recommend_books`, suggests *Python Crash Course* with shelf location.
3. **Test 3 - Reserve Book:**
   - Type: `I want to reserve Deep Learning. My name is Aarav Sharma, Student ID STU-4081, pickup tomorrow.`
   - *Observation:* Agent calls `check_availability` + `create_reservation`, generates unique `RES-2026-XXXX`, and updates the side panel catalogue.
4. **Test 4 - Unavailable Book (Safe Fallback):**
   - Type: `Please reserve Introduction to Algorithms for me.`
   - *Observation:* Book is currently reserved; agent refuses to book, provides location note and available alternatives in Computer Science.
5. **Test 5 - Status Tracking & Cancellation:**
   - Type: `Check status for reservation RES-2026-1030`
   - Type: `Cancel reservation RES-2026-1030`
   - *Observation:* Agent cancels reservation, restores book status to `Available`.
