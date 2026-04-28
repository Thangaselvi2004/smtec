with open('templates/staff_portal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
tabs = re.findall(r'id=\"(tab-[a-z]+)\"', text)
for tab in tabs:
    print(tab)
