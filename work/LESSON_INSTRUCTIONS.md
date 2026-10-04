## Output rules (the user's spec, follow exactly)

مهمتك: إنشاء أسئلة اختيار من متعدد (MCQ) مع دعم كامل لتنسيق النص العربي والمعادلات بشكل صحيح.

مخطط الإخراج النهائي (مصفوفة JSON، بهذا الترتيب للمفاتيح، بدون فاصلة زائدة بعد آخر مفتاح):
```
[{
"id": "<معرّف السؤال>",
"question": "نص السؤال بالعربية",
"choice1": "الخيار الأول",
"choice2": "الخيار الثاني",
"choice3": "الخيار الثالث",
"choice4": "الخيار الرابع",
"correct_answer": <0 أو 1 أو 2 أو 3>,
"topic_id": <قيمة topic_id كما هي في ملف الدروس>
}]
```

- استخدم تنسيق LaTeX حصرياً لأي معادلة أو رمز رياضي. يُمنع تماماً استخدام رموز Unicode الجاهزة (× ÷ √ ² π ≤ ≥ ≠ ° …).
- للمعادلات استخدم `$ ... $`، واكتب الشرطة المائلة مزدوجة `\\` بدلاً من `\` لتتوافق مع تنسيق JSON (مثال في الملف: `"$\\frac{1}{2}$"`).
- استخدم المتغيرات بالعربية (س، ص، ع…) إذا كان الشرح بالعربية، وللمصطلحات استخدم `\sin`, `\cos`, `\frac`, …
- استخدم دائماً الأرقام الإنجليزية (0-9) في جميع المعادلات.
- إذا وجدت في المصادر أسئلة، ولّد أسئلة مشابهة لها في الفكرة الأساسية بالاستعانة بكتاب الشرح (لا تنسخها حرفياً).
- أنشئ صيغ وأشكال متعددة ومتنوعة للسؤال الواحد حول نفس المفهوم الأساسي.
- كل سؤال كامل ومستقل بذاته؛ لا تشر أبداً إلى "السؤال السابق" أو "النص" أو "الشكل المقابل" أو "المصدر" أو "الجدول".
- لا تكرر الإجابات والاختيارات، ولا تضع تلميحات للإجابة الصحيحة أو مثالاً إضافياً داخل نص الاختيارات.
- تجنب المصطلحات الإنجليزية غير الضرورية في الأسئلة العربية.
- كل سؤال له 4 بدائل فقط وإجابة صحيحة واحدة. رقم الإجابة الصحيحة يبدأ من 0.
- المخرج النهائي ملف يحتوي مصفوفة JSON فقط، بدون أي نصوص أو علامات markdown.

## Per-lesson scenario

Run these steps for one lesson, inside `work/lessons/<topic_id>/`.

### 1. Read the PDFs
- Arabic text extracted with pdftotext/pypdf is often reversed, split into isolated letters, or loses equations. Render pages to images (`pdftoppm -r 110 -png file.pdf page`) and read them visually with the Read tool, in batches. Use extracted text only as a cross-check.
- Save a clean transcription of the explanation to `explanation.md`, marking sections with headings, and writing every equation in LaTeX.

### 2. Parse the questions PDF
- Split it into individual questions and save them to `examples.json` as `[{"question": ..., "choices": [...], "answer": ..., "concept": ...}]`.
- Write a short style profile in `style.md`: typical question forms (direct recall, calculation, "which of the following", complete the statement, compare, cause/effect), stem length, how distractors are built (common mistakes, sign errors, swapped concepts, near values), and difficulty mix.
- If the questions PDF turns out to be empty or unreadable, continue from the explanation alone and note it in the lesson's progress line.

### 3. Chunk the explanation
- One chunk per concept (a definition, a law, a rule plus its worked example), following the section structure. Do not split an equation or a worked example from the rule it illustrates.
- Save `chunks.json`: `[{"chunk_id", "title", "text"}]`.

### 4. Plan the distribution
- Allocate the lesson's question count across chunks in proportion to how much testable content each has; skip chunks with nothing testable (introductions, objectives).
- For each chunk, list the example questions that test the same or a similar concept (you pick them by reading; no vector DB is needed at this scale). These are the few-shot references for that chunk.
- Mix difficulty and question forms following the style profile. Save the plan to `plan.md`.

### 5. Generate per chunk
For each chunk, write its questions using only that chunk (plus basic prerequisite knowledge), imitating the matched examples' idea and form with new numbers, wording and angles. Several different forms per concept are wanted.

Distractors: plausible, same type and similar length as the correct answer, based on real student mistakes; never "all of the above" unless the style reference uses it; no hints.

Write batches to `draft.json` as a raw JSON array, with every backslash doubled (`\\frac`, `\\sin`, `\\sqrt`, `^{\\circ}`). A single backslash breaks the file: `\f`, `\t`, `\n`, `\b` silently turn into control characters, and `\s` is invalid JSON. Use the lesson's id pattern `"<topic_id>_001"` and its topic_id on every question.

### 6. Verify correctness
For every question, solve it from scratch without looking at `correct_answer`, and confirm exactly one choice is right, the marked index matches it, and the answer follows from the explanation. Fix or drop any that fail, then top up to the target count. For calculation questions, check the arithmetic by running it in Python.

### 7. Validate format
Run from the working directory root (where `validate_mcq.py` and `work/` are), with L=`work/lessons/<topic_id>`:
```
python3 validate_mcq.py $L/draft.json --examples $L/examples.json --topic-id <topic_id>
```
- Fix every ERROR. Review every WARN and fix it unless it is a false positive (for example «الضلع المقابل» in trigonometry is a real concept, not a reference to a figure).
- Re-run until 0 errors.

### 8. Balance and save
```
python3 validate_mcq.py $L/draft.json --topic-id <topic_id> --rebalance work/output/<topic_id>.json
python3 validate_mcq.py work/output/<topic_id>.json --topic-id <topic_id>
```
Rebalancing shuffles choices so correct answers spread evenly over 0–3. If a question's choices have a meaningful order (ascending numbers, «كلاهما», «لا شيء مما سبق»), fix that question's order by hand afterwards and re-validate. Then return to the lesson loop (mark done, progress line, next lesson).


## validate_mcq.py

The validator script is already saved at /home/user/Mcq-Generator/validate_mcq.py (identical to the skill's). Run every validator command from /home/user/Mcq-Generator.
