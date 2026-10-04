# Brief for one lesson (Arabic dynamics MCQs, Egyptian 3rd secondary, ديناميكا 3 ث)

You are generating exactly 100 Arabic MCQs for ONE lesson. Quality matters more than speed.

1. Read /home/user/Mcq-Generator/work/LESSON_INSTRUCTIONS.md in full FIRST. It contains the "Output rules", "Per-lesson scenario" and validator instructions verbatim from the skill. Follow them exactly.
2. Working directory for commands: /home/user/Mcq-Generator. All intermediate files for your lesson go in work/lessons/<TOPIC_ID>/ (explanation.md, examples.json, style.md, chunks.json, plan.md, draft.json, page images). Final output: work/output/<TOPIC_ID>.json.
3. topic_id on every question is the JSON STRING "<TOPIC_ID>" (with quotes, a string, as in the manifest). ids are "<TOPIC_ID>_001" … "<TOPIC_ID>_100".
4. Read the PDFs visually: `pdftoppm -r 110 -png <pdf> work/lessons/<TOPIC_ID>/expl` (and `.../q` for questions), then Read the PNGs in batches. pdftotext only as cross-check.
5. Physics notation reminders (the validator rejects Unicode math symbols such as × ÷ √ ² ³ ° π θ α ≤ ≥ ≠ − · →):
   - units with powers in LaTeX, e.g. `$4.9$ م/ث$^{2}$` or `$9.8 \\, م/ث^{2}$`; degrees `$60^{\\circ}$`; multiplication `$\\times$`; vectors `$\\overrightarrow{ق}$` or `$\\vec{ع}$`; unit vectors `$\\hat{س}$`, `$\\hat{ص}$`.
   - Use Arabic variable letters (ق، ك، ع، ح، ف، ن، م، ...) as the explanation does, inside $...$.
   - Use English digits 0-9 everywhere (also outside math), never ٠-٩.
   - Every backslash in draft.json is doubled.
6. Verify every calculation question with Python (g = 9.8 م/ث² unless the question states otherwise, as in the book). Exactly one correct choice; distractors from realistic mistakes (wrong unit conversion: ث.كجم vs نيوتن, km/h vs m/s, sign/direction errors, forgetting g, etc.).
7. Questions must be self-contained: never refer to a figure/الشكل/table. If a source question depends on a figure, describe the situation fully in words instead.
8. Finish with: draft validated (0 errors, WARNs reviewed), rebalanced to work/output/<TOPIC_ID>.json, re-validated with `--topic-id <TOPIC_ID>` (0 errors), then fix by hand any rebalanced question whose choice order is meaningful.
9. Do NOT run `lessons.py mark`, do NOT touch other lessons' folders or outputs, do NOT git commit.
10. Final reply (short, plain text): lesson title in Arabic (from the explanation PDF), number of questions in the output file, validator summary line (errors/warnings), the correct_answer distribution, and any problems (e.g. unreadable pages).
