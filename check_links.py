import sqlite3

conn = sqlite3.connect('student.db')

print("=== ASSIGNED TASKS (Staff -> Student Links) ===")
rows = conn.execute("SELECT id, title, task_url, due_date, file_path FROM assigned_tasks").fetchall()
if rows:
    for r in rows:
        print(f"  ID:{r[0]} | Title:{r[1]} | URL:{r[2]} | Due:{r[3]} | File:{r[4]}")
else:
    print("  (No tasks found)")

print()
print("=== TOPICS (Video Links) ===")
rows = conn.execute("SELECT id, title, video_url, pdf_path FROM topics").fetchall()
if rows:
    for r in rows:
        print(f"  ID:{r[0]} | Title:{r[1]} | Video:{r[2]} | PDF:{r[3]}")
else:
    print("  (No topics found)")

print()
print("=== RESOURCES (Library Links) ===")
rows = conn.execute("SELECT id, title, resource_url, file_path, type FROM resources").fetchall()
if rows:
    for r in rows:
        print(f"  ID:{r[0]} | Title:{r[1]} | URL:{r[2]} | File:{r[3]} | Type:{r[4]}")
else:
    print("  (No resources found)")

print()
print("=== QUESTIONS (with Links) ===")
rows = conn.execute("SELECT id, question_text, link FROM questions WHERE link IS NOT NULL AND link != ''").fetchall()
if rows:
    for r in rows:
        print(f"  ID:{r[0]} | Q:{r[1][:40]} | Link:{r[2]}")
else:
    print("  (No question links found)")

print()
print("=== ALL DB TABLES ===")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f"  {t[0]}: {count} rows")

conn.close()
