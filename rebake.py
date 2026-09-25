import re

html_path = 'index.html'
data_path = 'data.json'

with open(html_path, encoding='utf-8') as f:
    html = f.read()
with open(data_path, encoding='utf-8') as f:
    data_json = f.read().strip()

# Use a function repl (not a plain string) so backslashes/JSON content can
# never be misread as regex backreferences.
new_html, n = re.subn(
    r'const D = \{.*?\};',
    lambda _m: 'const D = ' + data_json + ';',
    html,
    count=1,
    flags=re.S,
)
assert n == 1, 'expected exactly one substitution, got ' + str(n)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print('re-baked, size:', len(new_html))
