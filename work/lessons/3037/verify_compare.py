import json
qs=json.load(open('/home/user/Mcq-Generator/work/output/3037.json'))
a="1B 2B 3D 4A 5C 6B 7B 8B 9C 10B 11C 12A 13B 14B 15A 16B 17C 18A 19A 20D 21D 22C 23D 24C 25C 26A 27C 28A 29A 30C 31B 32B 33C 34D 35A 36C 37C 38D 39B 40B 41A 42D 43C 44A 45D 46B 47D 48D 49A 50C"
b="51B 52C 53C 54D 55A 56A 57A 58D 59D 60A 61D 62A 63D 64D 65D 66C 67A 68B 69B 70B 71C 72D 73B 74B 75A 76D 77A 78B 79C 80C 81B 82C 83A 84B 85D 86D 87A 88D 89A 90D 91C 92C 93A 94A 95B 96C 97D 98C 99D 100B"
mine=[ 'ABCD'.index(t[-1]) for t in (a+' '+b).split()]
assert len(mine)==100
from collections import Counter
print(Counter(q['correct_answer'] for q in qs))
for q,m in zip(qs,mine):
    if q['correct_answer']!=m: print('MISMATCH',q['id'],'key',q['correct_answer'],'mine',m)
    if q['topic_id']!='3037': print('topic',q['id'],q['topic_id'])
