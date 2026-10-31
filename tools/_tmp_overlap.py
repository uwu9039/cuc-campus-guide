import json
import re
from difflib import SequenceMatcher
from pathlib import Path

data = json.loads(Path('items.json').read_text(encoding='utf-8'))
items = {it['id']: it for it in data['items']}


def src(pid):
    it = items.get(pid)
    if not it:
        return ''
    return (it.get('evidence', {}).get('answer', {}) or {}).get('src', '')


def norm(s):
    return re.sub(r'[\s，。；：、（）()“”"\'《》【】\-—…]', '', str(s))


a = [(norm(it.get('answer')), pid) for pid, it in items.items() if src(pid).startswith('2e14e6ba')]
b = [(norm(it.get('answer')), pid) for pid, it in items.items() if src(pid).startswith('5d67dc12')]

matched = 0
unique = []
for bb, pidb in b:
    best = 0.0
    for aa, pida in a:
        r = SequenceMatcher(None, bb, aa).ratio()
        if r > best:
            best = r
    if best >= 0.8:
        matched += 1
    else:
        unique.append((pidb, round(best, 2), bb[:80]))

print('5d67dc12 total', len(b), 'matched>=0.8', matched, 'unique', len(unique))
for u in unique[:80]:
    print(u)
