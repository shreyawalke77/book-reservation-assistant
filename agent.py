"""
Book Reservation Assistant - Agent Engine
Implements an agentic AI architecture with tool calling, context memory,
slot validation, and responsible AI guardrails.
"""

import random
import re
from datetime import datetime
from database import (
    query_books,
    get_book_by_id_or_title,
    get_all_books,
    insert_reservation,
    get_reservation,
    cancel_reservation_record
)

# System Prompt specification for the agent
SYSTEM_PROMPT = """
You are the "Book Reservation Assistant", an intelligent, friendly, and student-focused AI library agent.
Your primary role is to assist students, researchers, and library members with searching books, checking availability,
recommending academic and literature titles, and processing book reservations.

Core Instructions & Behavioral Guardrails:
1. Tone & Persona: Courteous, encouraging, academic, and student-friendly.
2. Grounded Truth: Only answer based on actual book catalogue data. NEVER hallucinate books, shelf locations, or availability.
3. Distinction of States:
   - SUGGESTING: When a user asks what to read, recommend suitable titles from the catalogue based on their interests.
   - CHECKING AVAILABILITY: Inspect database status (Available, Reserved, Issued). State exact rack/shelf location if available.
   - REQUESTING RESERVATION: Actively collect required details (Full Name, Student ID, Preferred Date, Book Title).
   - CONFIRMING RESERVATION: ONLY generate a reservation ID after the record has been verified and saved in the database.
4. Responsible AI & Privacy: Keep student details strictly within the session context. Never fabricate a reservation reference.
5. Error Handling & Fallback: If a book is unavailable, explain politely and suggest similar alternative books from the catalogue.
"""

# Tool Definitions (Function Calling schema)
TOOLS_SCHEMA = [
    {
        "name": "search_books",
        "description": "Searches the library catalogue by title, author, genre, or keyword.",
        "parameters": {"query": "string", "category": "optional string"}
    },
    {
        "name": "check_availability",
        "description": "Checks the live inventory status and shelf location of a specific book.",
        "parameters": {"book_identifier": "string (book_id or title)"}
    },
    {
        "name": "recommend_books",
        "description": "Recommends books based on student interest, genre, or reading level.",
        "parameters": {"genre_or_topic": "string"}
    },
    {
        "name": "create_reservation",
        "description": "Validates availability and reserves a book for a registered student.",
        "parameters": {
            "book_title": "string",
            "user_name": "string",
            "student_id": "string",
            "reservation_date": "string"
        }
    },
    {
        "name": "get_reservation_status",
        "description": "Retrieves current status of an existing reservation reference ID.",
        "parameters": {"reservation_id": "string"}
    },
    {
        "name": "cancel_reservation",
        "description": "Cancels an active reservation and restores book availability.",
        "parameters": {"reservation_id": "string"}
    }
]

class BookReservationAgent:
    def __init__(self):
        # Conversation state per session: { session_id: { ... } }
        self.sessions = {}

    def get_or_create_session(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "last_mentioned_book": None,
                "reservation_draft": {
                    "book_title": None,
                    "book_id": None,
                    "user_name": None,
                    "student_id": None,
                    "reservation_date": None
                },
                "pending_intent": None
            }
        return self.sessions[session_id]

    def reset_reservation_draft(self, session):
        session["reservation_draft"] = {
            "book_title": None,
            "book_id": None,
            "user_name": None,
            "student_id": None,
            "reservation_date": None
        }
        session["pending_intent"] = None

    # TOOL IMPLEMENTATIONS
    def tool_search_books(self, query=None, category=None):
        results = query_books(search_text=query, category=category)
        return {
            "tool": "search_books",
            "input": {"query": query, "category": category},
            "count": len(results),
            "results": results
        }

    def tool_check_availability(self, identifier):
        book = get_book_by_id_or_title(identifier)
        return {
            "tool": "check_availability",
            "input": {"identifier": identifier},
            "found": book is not None,
            "book": book
        }

    def tool_recommend_books(self, topic):
        results = query_books(search_text=topic)
        if not results:
            # Fallback to general catalogue if topic not specific
            results = get_all_books()[:3]
        return {
            "tool": "recommend_books",
            "input": {"topic": topic},
            "recommendations": results[:4]
        }

    def tool_create_reservation(self, user_name, student_id, book_title, res_date):
        book = get_book_by_id_or_title(book_title)
        if not book:
            return {
                "tool": "create_reservation",
                "success": False,
                "error": f"Book '{book_title}' does not exist in our library catalogue."
            }
        
        if book['status'] != 'Available':
            return {
                "tool": "create_reservation",
                "success": False,
                "error": f"'{book['title']}' is currently '{book['status']}' and cannot be reserved immediately."
            }
        
        # Generate official unique reference
        res_id = f"RES-2026-{random.randint(1000, 9999)}"
        success = insert_reservation(
            res_id=res_id,
            user_name=user_name,
            student_id=student_id,
            book_id=book['book_id'],
            book_title=book['title'],
            res_date=res_date
        )
        return {
            "tool": "create_reservation",
            "success": success,
            "reservation_id": res_id,
            "details": {
                "reservation_id": res_id,
                "book_id": book['book_id'],
                "book_title": book['title'],
                "user_name": user_name,
                "student_id": student_id,
                "reservation_date": res_date,
                "status": "Active",
                "shelf_location": book['shelf_location']
            }
        }

    def tool_get_reservation_status(self, res_id):
        res = get_reservation(res_id)
        return {
            "tool": "get_reservation_status",
            "found": res is not None,
            "reservation": res
        }

    def tool_cancel_reservation(self, res_id):
        success, message = cancel_reservation_record(res_id)
        return {
            "tool": "cancel_reservation",
            "success": success,
            "message": message
        }

    # AGENTIC REASONING & INTENT ROUTING
    def process_message(self, session_id, user_text):
        session = self.get_or_create_session(session_id)
        text_clean = user_text.strip()
        text_lower = text_clean.lower()
        
        tools_called = []
        thoughts = []
        reply = ""

        # Check for reservation reference code (e.g. RES-2026-1030)
        res_code_match = re.search(r'\b(res-\d{4}-\d{4})\b', text_lower)
        res_code = res_code_match.group(1).upper() if res_code_match else None

        # Check for Student ID (e.g., STU-1234 or STU1234)
        stu_id_match = re.search(r'\b(stu-?\d{3,5})\b', text_lower)
        extracted_stu_id = stu_id_match.group(1).upper() if stu_id_match else None

        # Check for date (e.g., 2026-10-25 or tomorrow or 18th Oct)
        date_match = re.search(r'\b(\d{4}-\d{2}-\d{2}|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*|\d{1,2}/\d{1,2}/\d{4}|tomorrow)\b', text_lower)
        extracted_date = date_match.group(1) if date_match else None

        thoughts.append("Step 1: Analyzed user input for entities, keywords, and active dialog state.")

        # --- BRANCH A: CANCEL RESERVATION ---
        if "cancel" in text_lower and ("reservation" in text_lower or "booking" in text_lower or res_code):
            thoughts.append("Step 2: Identified cancellation intent.")
            if res_code:
                thoughts.append(f"Step 3: Invoking cancel_reservation tool for ID '{res_code}'.")
                call_res = self.tool_cancel_reservation(res_code)
                tools_called.append(call_res)
                if call_res["success"]:
                    reply = (
                        f"### Reservation Cancelled Successfully\n\n"
                        f"**{call_res['message']}**\n\n"
                        f"- **Reference:** `{res_code}`\n"
                        f"- **Status Updated:** `Cancelled`\n\n"
                        f"The book inventory has been restored to **Available**. Let me know if you would like to explore or reserve any other book!"
                    )
                else:
                    reply = (
                        f"### Cancellation Notice\n\n"
                        f"Unable to process cancellation for `{res_code}`:\n"
                        f"> {call_res['message']}\n\n"
                        f"Please verify your reservation reference ID or check with the library helpdesk."
                    )
            else:
                reply = (
                    "### Cancel a Reservation\n\n"
                    "I can help you cancel an active reservation. Please provide your **Reservation Reference ID** "
                    "(e.g., `RES-2026-1030`)."
                )
            self._update_history(session, text_clean, reply)
            return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

        # --- BRANCH B: CHECK RESERVATION STATUS ---
        if ("status" in text_lower or "check reservation" in text_lower or "my reservation" in text_lower or res_code) and ("cancel" not in text_lower):
            thoughts.append("Step 2: Identified reservation status enquiry intent.")
            if res_code:
                thoughts.append(f"Step 3: Invoking get_reservation_status tool for ID '{res_code}'.")
                call_res = self.tool_get_reservation_status(res_code)
                tools_called.append(call_res)
                if call_res["found"]:
                    r = call_res["reservation"]
                    status_badge = f"**{r['status']}**"
                    reply = (
                        f"### Reservation Details Found\n\n"
                        f"Here is the status for reference **`{r['reservation_id']}`**:\n\n"
                        f"- **Book Title:** {r['book_title']} (`{r['book_id']}`)\n"
                        f"- **Reserved By:** {r['user_name']} (Student ID: `{r['student_id']}`)\n"
                        f"- **Reservation Date:** {r['reservation_date']}\n"
                        f"- **Current Status:** {status_badge}\n"
                        f"- **Created At:** {r['created_at']}\n\n"
                        f"Please collect your book at the circulation counter before closing hours on your reservation date."
                    )
                else:
                    reply = (
                        f"### Reservation Not Found\n\n"
                        f"I could not locate any active record for reference **`{res_code}`**.\n\n"
                        f"Please verify that the reservation ID was typed correctly or provide your registered student details."
                    )
            else:
                reply = (
                    "### Check Reservation Status\n\n"
                    "To check your reservation status, please provide your **Reservation Reference ID** "
                    "(for example: `RES-2026-1030`)."
                )
            self._update_history(session, text_clean, reply)
            return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

        # --- BRANCH C: RESERVATION REQUEST OR ONGOING DRAFT FILLING ---
        is_reserve_intent = any(w in text_lower for w in ["reserve", "book this", "hold", "reserve it", "want to reserve"])
        in_pending_reservation = session.get("pending_intent") == "RESERVATION_PENDING"

        if is_reserve_intent or in_pending_reservation:
            thoughts.append("Step 2: Processing reservation flow / slot-filling validation.")
            session["pending_intent"] = "RESERVATION_PENDING"
            draft = session["reservation_draft"]

            # Update book title if mentioned or infer from last_mentioned_book
            all_bks = get_all_books()
            matched_book = None
            for b in all_bks:
                if b['title'].lower() in text_lower or b['book_id'].lower() in text_lower:
                    matched_book = b
                    break
            
            # Check keywords like "clean code", "deep learning", "algorithms", "python"
            if not matched_book:
                for b in all_bks:
                    keywords = [w.strip() for w in b['tags'].split(',')]
                    if any(k in text_lower for k in keywords if len(k) > 3):
                        matched_book = b
                        break

            if matched_book:
                draft["book_title"] = matched_book['title']
                draft["book_id"] = matched_book['book_id']
                session["last_mentioned_book"] = matched_book
            elif not draft["book_title"] and session["last_mentioned_book"]:
                # Use contextual pronoun resolution ("reserve it" / "book this")
                draft["book_title"] = session["last_mentioned_book"]['title']
                draft["book_id"] = session["last_mentioned_book"]['book_id']

            # Extract student ID
            if extracted_stu_id:
                draft["student_id"] = extracted_stu_id
            
            # Extract date
            if extracted_date:
                draft["reservation_date"] = extracted_date
            elif "today" in text_lower:
                draft["reservation_date"] = datetime.now().strftime("%Y-%m-%d")
            elif "tomorrow" in text_lower:
                draft["reservation_date"] = "Tomorrow"

            # Extract user name if specified like "name is Aarav" or "I am Priya" or "for Aarav Sharma"
            name_match = re.search(r'(?:name is|i am|my name is|student name is|for)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)', text_clean)
            if name_match:
                candidate_name = name_match.group(1).strip()
                # filter out non-names like "Artificial"
                if candidate_name.lower() not in ["artificial intelligence", "clean code", "deep learning"]:
                    draft["user_name"] = candidate_name
            elif not draft["user_name"]:
                # Look for potential capitalized name if text has just a name like "Priya Verma"
                lines = [w.strip() for w in text_clean.split() if w.strip()]
                if len(lines) in [1, 2] and all(w[0].isupper() for w in lines) and not any(kw in text_lower for kw in ['reserve', 'book', 'status', 'cancel']):
                    draft["user_name"] = text_clean

            thoughts.append(f"Step 3: Current reservation draft state: {draft}")

            # 1. Check if Book Title is missing
            if not draft["book_title"]:
                reply = (
                    "### Book Reservation Request\n\n"
                    "I would be glad to help you reserve a book! Which book would you like to reserve?\n"
                    "You can provide the **Title** or **Book ID** (e.g., *'Clean Code'* or `BK-101`)."
                )
                self._update_history(session, text_clean, reply)
                return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

            # 2. Check Book Availability first before asking more personal details
            target_bk = get_book_by_id_or_title(draft["book_title"])
            thoughts.append(f"Step 4: Validating live availability of '{draft['book_title']}' with database.")
            avail_call = self.tool_check_availability(draft["book_title"])
            tools_called.append(avail_call)

            if not target_bk:
                session["pending_intent"] = None
                reply = (
                    f"### Book Not Found\n\n"
                    f"I could not find **'{draft['book_title']}'** in our library catalogue.\n\n"
                    f"Would you like me to search for similar titles or list our current computer science and literature collection?"
                )
                self._update_history(session, text_clean, reply)
                return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

            if target_bk['status'] != 'Available':
                self.reset_reservation_draft(session)
                similar_books = query_books(category=target_bk['category'])
                alternatives = [b['title'] for b in similar_books if b['book_id'] != target_bk['book_id'] and b['status'] == 'Available']
                alt_text = "\n".join([f"- **{alt}** (Available)" for alt in alternatives[:2]]) if alternatives else "Please check back next week."

                reply = (
                    f"### Book Unavailable for Reservation\n\n"
                    f"I checked our catalogue, but **'{target_bk['title']}'** (`{target_bk['book_id']}`) is currently **{target_bk['status']}**.\n\n"
                    f"> **Location Note:** Shelf {target_bk['shelf_location']} — currently borrowed or reserved by another student.\n\n"
                    f"**Recommended Available Alternatives in {target_bk['category']}:**\n"
                    f"{alt_text}\n\n"
                    f"Would you like to reserve one of these alternative books instead, or be notified when '{target_bk['title']}' returns?"
                )
                self._update_history(session, text_clean, reply)
                return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

            # 3. Check for missing reservation details
            missing_fields = []
            if not draft["user_name"]:
                missing_fields.append("Your **Full Name**")
            if not draft["student_id"]:
                missing_fields.append("Your **Student ID** (e.g., `STU-2045`)")
            if not draft["reservation_date"]:
                missing_fields.append("Your **Preferred Pickup Date** (e.g., `2026-10-20` or `Tomorrow`)")

            if missing_fields:
                thoughts.append(f"Step 5: Missing reservation fields: {missing_fields}. Prompting user.")
                prompt_items = "\n".join([f"- {field}" for field in missing_fields])
                reply = (
                    f"### Reserving '{target_bk['title']}'\n\n"
                    f"Great! **'{target_bk['title']}'** is currently **Available** at **{target_bk['shelf_location']}**.\n\n"
                    f"To finalize your reservation, please provide the following missing detail(s):\n"
                    f"{prompt_items}\n\n"
                    f"*Example: 'My name is Rohan Shah, Student ID STU-3092, pickup tomorrow.'*"
                )
                self._update_history(session, text_clean, reply)
                return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

            # 4. All fields present -> Execute create_reservation Tool!
            thoughts.append("Step 5: All required reservation fields satisfied. Invoking create_reservation tool.")
            res_call = self.tool_create_reservation(
                user_name=draft["user_name"],
                student_id=draft["student_id"],
                book_title=draft["book_title"],
                res_date=draft["reservation_date"]
            )
            tools_called.append(res_call)
            self.reset_reservation_draft(session)

            if res_call["success"]:
                details = res_call["details"]
                reply = (
                    f"### Reservation Confirmed! 🎉\n\n"
                    f"Your reservation has been successfully registered in the library system.\n\n"
                    f"| Detail | Information |\n"
                    f"| :--- | :--- |\n"
                    f"| **Reservation ID** | **`{details['reservation_id']}`** |\n"
                    f"| **Book Title** | {details['book_title']} |\n"
                    f"| **Book ID** | `{details['book_id']}` |\n"
                    f"| **Student Name** | {details['user_name']} |\n"
                    f"| **Student ID** | `{details['student_id']}` |\n"
                    f"| **Pickup Date** | {details['reservation_date']} |\n"
                    f"| **Shelf Location** | {details['shelf_location']} |\n"
                    f"| **Status** | Active |\n\n"
                    f"> **Important:** Please quote reference **`{details['reservation_id']}`** at the circulation counter when collecting the book. Books are held for 48 hours."
                )
            else:
                reply = f"### Reservation Error\n\nSorry, could not complete the reservation: {res_call.get('error')}"

            self._update_history(session, text_clean, reply)
            return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

        # --- BRANCH D: AVAILABILITY CHECK ---
        is_avail_check = any(w in text_lower for w in ["available", "availability", "in stock", "can i get", "is there a copy"])
        if is_avail_check:
            thoughts.append("Step 2: Identified availability check intent.")
            # Search for candidate book
            all_bks = get_all_books()
            matched_book = None
            for b in all_bks:
                if b['title'].lower() in text_lower or b['book_id'].lower() in text_lower:
                    matched_book = b
                    break
            if not matched_book:
                for b in all_bks:
                    words = b['title'].lower().split()
                    if any(w in text_lower for w in words if len(w) > 4):
                        matched_book = b
                        break

            if matched_book:
                thoughts.append(f"Step 3: Invoking check_availability tool for '{matched_book['title']}'.")
                call_res = self.tool_check_availability(matched_book['book_id'])
                tools_called.append(call_res)
                session["last_mentioned_book"] = matched_book
                bk = call_res["book"]

                if bk["status"] == "Available":
                    reply = (
                        f"### Book Availability: Available ✅\n\n"
                        f"**{bk['title']}** by {bk['author']}\n\n"
                        f"- **Book ID:** `{bk['book_id']}`\n"
                        f"- **Category:** {bk['category']}\n"
                        f"- **Status:** **Available**\n"
                        f"- **Location:** {bk['shelf_location']}\n"
                        f"- **ISBN:** `{bk['isbn']}`\n\n"
                        f"**Summary:** {bk['description']}\n\n"
                        f"Would you like me to reserve this book for you now?"
                    )
                else:
                    reply = (
                        f"### Book Availability: {bk['status']} ⚠️\n\n"
                        f"**{bk['title']}** by {bk['author']}\n\n"
                        f"- **Book ID:** `{bk['book_id']}`\n"
                        f"- **Current Status:** **{bk['status']}**\n"
                        f"- **Shelf Location:** {bk['shelf_location']}\n\n"
                        f"This copy is currently not available for immediate checkout. "
                        f"Would you like me to recommend alternative titles in **{bk['category']}**?"
                    )
            else:
                reply = (
                    "### Check Availability\n\n"
                    "Which book title or Book ID would you like me to check? "
                    "For example, you can ask: *'Is Artificial Intelligence: A Modern Approach available?'*"
                )
            self._update_history(session, text_clean, reply)
            return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

        # --- BRANCH E: RECOMMENDATIONS ---
        is_rec_intent = any(w in text_lower for w in ["recommend", "suggestion", "suggest", "what should i read", "good book for", "interested in"])
        if is_rec_intent:
            thoughts.append("Step 2: Identified book recommendation intent.")
            # extract topic or genre
            topic = "computer science"
            for candidate in ["ai", "artificial intelligence", "algorithms", "software", "clean code", "python", "networking", "database", "systems", "deep learning"]:
                if candidate in text_lower:
                    topic = candidate
                    break
            
            thoughts.append(f"Step 3: Invoking recommend_books tool for topic '{topic}'.")
            call_res = self.tool_recommend_books(topic)
            tools_called.append(call_res)
            
            recs = call_res["recommendations"]
            if recs:
                rec_lines = []
                for b in recs:
                    status_badge = "Available ✅" if b['status'] == 'Available' else f"{b['status']} ⚠️"
                    rec_lines.append(
                        f"- **{b['title']}** by *{b['author']}*\n"
                        f"  - **ID:** `{b['book_id']}` | **Status:** {status_badge} | **Shelf:** {b['shelf_location']}\n"
                        f"  - *{b['description'][:110]}...*"
                    )
                reply = (
                    f"### Recommended Books for: *{topic.title()}*\n\n"
                    f"Here are top-recommended titles tailored to your interest:\n\n"
                    + "\n\n".join(rec_lines) +
                    f"\n\nTell me which title you'd like to check or reserve, and I can start your reservation right away!"
                )
            else:
                reply = "I couldn't find specific recommendations for that topic, but I can show you our popular engineering and AI catalogue."
            self._update_history(session, text_clean, reply)
            return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

        # --- BRANCH F: SEARCH CATALOGUE ---
        is_search = any(w in text_lower for w in ["search", "find", "look for", "show me", "catalogue", "catalog", "list books", "books on"])
        if is_search:
            thoughts.append("Step 2: Identified catalogue search intent.")
            # extract search term
            query_term = text_lower
            for stop in ["search", "find", "books", "on", "about", "for", "the", "library", "catalogue", "catalog", "please", "show", "me", "list"]:
                query_term = re.sub(rf'\b{stop}\b', '', query_term).strip()
            
            thoughts.append(f"Step 3: Invoking search_books tool with term '{query_term}'.")
            search_res = self.tool_search_books(query=query_term if query_term else None)
            tools_called.append(search_res)

            books = search_res["results"]
            if books:
                table_rows = []
                for b in books[:5]:
                    badge = "✅ Available" if b['status'] == 'Available' else f"⚠️ {b['status']}"
                    table_rows.append(f"| `{b['book_id']}` | **{b['title']}** | {b['author']} | {badge} | {b['shelf_location']} |")
                
                reply = (
                    f"### Search Results ({len(books)} found)\n\n"
                    f"| ID | Title | Author | Status | Shelf |\n"
                    f"| :--- | :--- | :--- | :--- | :--- |\n"
                    + "\n".join(table_rows) +
                    f"\n\nTo reserve any available book, simply say: *'Reserve BK-101'* or *'Reserve {books[0]['title']}'*."
                )
            else:
                reply = (
                    f"### No Matches Found\n\n"
                    f"We could not find any books matching **'{query_term}'** in our current catalogue.\n\n"
                    f"Try searching by broader terms such as `Python`, `Algorithms`, `Software`, `AI`, or `Database`."
                )
            self._update_history(session, text_clean, reply)
            return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

        # --- BRANCH G: GENERAL GREETINGS & FALLBACK ---
        thoughts.append("Step 2: Handling general greeting or conversational prompt.")
        if any(w in text_lower for w in ["hello", "hi", "hey", "greetings", "good morning", "good afternoon"]):
            reply = (
                "### Hello and welcome to the Book Reservation Assistant! 📚\n\n"
                "I am your automated library companion. I can help you with:\n\n"
                "1. **Book Search:** Find books by title, author, or keyword (e.g., *'Find books on Machine Learning'*)\n"
                "2. **Availability Checks:** Inspect current shelf location & status (e.g., *'Is Clean Code available?'*)\n"
                "3. **Book Recommendations:** Discover reading suggestions tailored to your coursework.\n"
                "4. **Book Reservations:** Lock and reserve an available book with instant confirmation.\n"
                "5. **Reservation Management:** Track (`RES-2026-1030`) or cancel existing reservations.\n\n"
                "How may I assist your reading journey today?"
            )
        else:
            reply = (
                "### Book Reservation Assistant\n\n"
                "I didn't quite catch that. Here is what I can do for you:\n"
                "- **Search books:** *'Show me AI textbooks'*\n"
                "- **Check availability:** *'Is Introduction to Algorithms available?'*\n"
                "- **Reserve a book:** *'I want to reserve Deep Learning'*\n"
                "- **Track status:** *'Check reservation status for RES-2026-1030'*\n"
                "- **Cancel reservation:** *'Cancel reservation RES-2026-1030'*\n\n"
                "What would you like to explore?"
            )

        self._update_history(session, text_clean, reply)
        return {"reply": reply, "thoughts": thoughts, "tools_called": tools_called}

    def _update_history(self, session, user_msg, bot_msg):
        session["history"].append({"role": "user", "text": user_msg, "timestamp": datetime.now().isoformat()})
        session["history"].append({"role": "assistant", "text": bot_msg, "timestamp": datetime.now().isoformat()})
        # Keep last 12 exchanges
        if len(session["history"]) > 24:
            session["history"] = session["history"][-24:]

agent_instance = BookReservationAgent()
