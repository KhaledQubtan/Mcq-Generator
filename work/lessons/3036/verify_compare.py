import json
d=json.load(open('/home/user/Mcq-Generator/work/output/3036.json'))
mine="1 1 3 0 2 1 1 1 2 1 2 0 1 1 0 1 2 0 0 3 3 2 3 2 2 0 2 0 0 2 1 1 2 3 0 2 2 3 1 1 0 3 2 0 3 1 3 3 0 2 1 2 2 3 0 0 0 3 3 0 3 0 3 3 3 2 0 1 1 1 2 3 1 1 0 3 0 1 2 2 1 2 0 1 3 3 0 3 0 3 2 2 0 0 1 2 3 2 3 1".split()
assert len(mine)==100
from collections import Counter
print(Counter(q['correct_answer'] for q in d))
for q,m in zip(d,mine):
    if q['correct_answer']!=int(m): print('MISMATCH',q['id'],q['correct_answer'],m)
