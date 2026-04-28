with open('templates/staff_portal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<div id="tab-' in line or 'End ' in line and 'Tab' in line:
        print(f'{i+1}: {line.strip()}')
