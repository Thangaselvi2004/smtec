import sqlite3
import os

DB_NAME = 'student.db'

def inspect_paths():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    print("--- EXAMS ---")
    c.execute("SELECT id, title, file_path FROM exams")
    for row in c.fetchall():
        print(row)
        
    print("\n--- ASSIGNMENTS ---")
    c.execute("SELECT id, title, file_path FROM assignments")
    for row in c.fetchall():
        print(row)
        
    print("\n--- QUESTION BANK ---")
    c.execute("SELECT id, topic, file_path FROM question_bank")
    for row in c.fetchall():
        print(row)
        
    conn.close()

if __name__ == "__main__":
    inspect_paths()
