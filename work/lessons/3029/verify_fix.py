import json, math
p='/home/user/Mcq-Generator/work/output/3029.json'
qs=json.load(open(p))
q=qs[39]; assert q['id']=='3029_040'
q['question']="جسمان على نفس المستوى المائل الأملس يتحركان تحت تأثير وزنيهما فقط، أحدهما يصعد والآخر يهبط. عجلة الجسم الصاعد مقارنة بعجلة الجسم الهابط:"
q['choice1']="ضعفها في المقدار"
q['choice2']="تساويها في المقدار ($د \\sin هـ$) والاتجاه (لأسفل المستوى)"
q['choice3']="أصغر منها في المقدار"
q['choice4']="أكبر منها في المقدار"
assert q['correct_answer']==1
q=qs[81]; assert q['id']=='3029_082'
k=8; s=1/4; F=8; a=2.45
assert abs((F*0.5 - k*s)*9.8 - k*a) < 1e-9
assert k*math.sqrt(1-s*s) - F*math.sin(math.pi/3) > 0
q['question']="جسم كتلته $8$ كجم على مستوٍ أملس يميل على الأفقي بزاوية جيبها $\\frac{1}{4}$، أثرت عليه قوة $ق$ ث.كجم يميل خط عملها على خط أكبر ميل لأعلى بزاوية $60^{\\circ}$ بعيداً عن المستوى فتحرك لأعلى بعجلة $2.45$ م/ث$^{2}$. مقدار $ق$:"
q['choice1']="$4$ ث.كجم"
q['choice2']="$\\frac{8\\sqrt{3}}{3}$ ث.كجم"
q['choice3']="$8$ ث.كجم"
q['choice4']="$16$ ث.كجم"
assert q['correct_answer']==2
json.dump(qs, open(p,'w'), ensure_ascii=False, indent=2)
