import database
from agent import agent_instance
import sys
import io

# Ensure UTF-8 output on Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_tests():
    print("--- 1. Initializing Database ---")
    database.init_db()
    books = database.get_all_books()
    print(f"Total books in catalogue: {len(books)}")

    print("\n--- 2. Test 1: Search Book by Title & Check Availability ---")
    res1 = agent_instance.process_message("sess-1", "Is Clean Code available right now?")
    print("Reply:", res1["reply"][:140], "...")
    print("Tools invoked:", [t["tool"] for t in res1["tools_called"]])

    print("\n--- 3. Test 2: Book Recommendations ---")
    res2 = agent_instance.process_message("sess-1", "Can you recommend good books on Artificial Intelligence?")
    print("Reply:", res2["reply"][:140], "...")
    print("Tools invoked:", [t["tool"] for t in res2["tools_called"]])

    print("\n--- 4. Test 3: Reserve Available Book ---")
    res3 = agent_instance.process_message("sess-1", "I want to reserve Deep Learning. My name is Aarav Sharma, Student ID STU-4081, pickup tomorrow.")
    print("Reply:", res3["reply"][:140], "...")
    print("Tools invoked:", [t["tool"] for t in res3["tools_called"]])

    print("\n--- 5. Test 4: Reserve Unavailable Book ---")
    res4 = agent_instance.process_message("sess-2", "Please reserve Introduction to Algorithms for me.")
    print("Reply:", res4["reply"][:140], "...")
    print("Tools invoked:", [t["tool"] for t in res4["tools_called"]])

    print("\n--- 6. Test 5: Check Existing Reservation Status ---")
    res5 = agent_instance.process_message("sess-3", "Check reservation status for RES-2026-1030")
    print("Reply:", res5["reply"][:140], "...")
    print("Tools invoked:", [t["tool"] for t in res5["tools_called"]])

    print("\n--- 7. Test 6: Cancel Reservation ---")
    res6 = agent_instance.process_message("sess-3", "Cancel reservation RES-2026-1030")
    print("Reply:", res6["reply"][:140], "...")
    print("Tools invoked:", [t["tool"] for t in res6["tools_called"]])

    print("\nAll automated tests completed successfully!")

if __name__ == "__main__":
    run_tests()
