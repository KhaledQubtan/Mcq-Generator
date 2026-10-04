import json
p='/home/user/Mcq-Generator/work/output/3029.json'
qs=json.load(open(p))
q=qs[39]; assert q['id']=='3029_040'
q['choice2']="تساويها في المقدار والاتجاه"
json.dump(qs, open(p,'w'), ensure_ascii=False, indent=2)
