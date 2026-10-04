import json
p='work/output/3022.json'
d=json.load(open(p,encoding='utf-8'))
q=[x for x in d if x['id']=='3022_068'][0]
assert '$ن \\ge 0$' in q['question']
q['question']=q['question'].replace('$ن \\ge 0$','$ن > 0$')
for c in ('choice2','choice3'):
    assert '$[0 , 1[$' in q[c]
    q[c]=q[c].replace('$[0 , 1[$','$]0 , 1[$')
print(q)
json.dump(d,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
