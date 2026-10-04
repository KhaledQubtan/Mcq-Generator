import json
d=json.load(open('/home/user/Mcq-Generator/work/output/8830.json'))
mine=[2,2,4,1,3,2,2,2,3,2, 3,1,2,2,1,2,3,1,1,4, 4,3,4,3,3,1,3,1,1,3, 2,2,3,4,1,3,3,4,2,2, 1,4,3,1,4,2,4,4,1,3, 2,3,3,4,1,1,1,4,4,1, 4,1,4,4,4,3,1,2,2,2, 3,4,2,2,1,4,1,2,3,3, 2,3,1,2,4,4,1,4,1,4, 3,3,1,1,2,3,4,3,4,2]
mine=[m-1 for m in mine]
assert len(mine)==100
for i,q in enumerate(d):
    if q['correct_answer']!=mine[i]: print(q['id'],'file',q['correct_answer'],'mine',mine[i])
