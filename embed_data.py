import re

html_path = r'C:\Users\j0i03e4\Documents\puppy_workspace\372-A\index.html'
data_path = r'C:\Users\j0i03e4\Documents\puppy_workspace\372-A\data.json'

with open(data_path, encoding='utf-8') as f:
    data_json = f.read().strip()

with open(html_path, encoding='utf-8') as f:
    html = f.read()

assert '__DATA_JSON__' in html, 'placeholder not found'
html = html.replace('__DATA_JSON__', data_json)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print('Embedded', len(data_json), 'bytes of JSON into', html_path)
