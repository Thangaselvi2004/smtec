import sqlite3
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.syllabus_data import SYLLABUS_DATA, SUBJECT_DETAILS

conn = sqlite3.connect('student.db')
c = conn.cursor()

unique_subjects = {}

for dept, semesters in SYLLABUS_DATA.items():
    for sem, subs in semesters.items():
        for sub in subs:
            name = sub['Name']
            code = sub['Code']
            desc = ""
            if code in SUBJECT_DETAILS:
                desc = " ".join(SUBJECT_DETAILS[code]['Units'])
            if name not in unique_subjects:
                unique_subjects[name] = desc

for name, desc in unique_subjects.items():
    try:
        c.execute("INSERT INTO subjects (name, description) VALUES (?, ?)", (name, desc))
    except sqlite3.IntegrityError:
        pass # Already exists

conn.commit()
conn.close()
print(f"Seeded {len(unique_subjects)} subjects.")
