# Independent answer check for one lesson's MCQs

You are a strict reviewer. File: /home/user/Mcq-Generator/work/output/<TOPIC_ID>.json (100 Arabic dynamics MCQs, Egyptian 3rd secondary). Lesson notes (transcribed explanation): /home/user/Mcq-Generator/work/lessons/<TOPIC_ID>/explanation.md.
Do NOT read the lesson's gen.py / checks.py / draft — your check must be independent of the author's.

For EVERY question:
1. Solve it from scratch WITHOUT looking at correct_answer first (g = 9.8 م/ث² = 980 سم/ث² unless stated; 1 ث.كجم = 9.8 نيوتن; 1 نيوتن = 10^5 داين; 1 ث.جم = 980 داين; 1 كم/س = 5/18 م/ث; 1 حصان = 75 ث.كجم.م/ث = 735 وات). For numeric problems compute in Python.
2. Confirm exactly one choice is correct and it is the one at index correct_answer (0-based: 0→choice1 … 3→choice4). Check also that no distractor is ALSO correct (equivalent values/forms) and the stem has all data needed and is unambiguous.
3. Concept questions: answer must agree with explanation.md.

Fix every wrong question directly in work/output/<TOPIC_ID>.json with a Python script (load json, edit, dump with ensure_ascii=False, indent=2):
- prefer fixing the stem numbers or the marked index / swapping the right value into the correct slot so correct_answer index stays the same (keeps the 0–3 balance). Keep ids, key order, topic_id string unchanged, LaTeX with $…$, no Unicode math symbols, English digits.
- If unsalvageable, rewrite that question entirely (same id) on the same concept.
Then run: cd /home/user/Mcq-Generator && python3 validate_mcq.py work/output/<TOPIC_ID>.json --topic-id <TOPIC_ID>   → must be 0 errors (review WARNs).
Do not touch any other file. No git.

Final reply (short): number of questions checked, list of ids changed with one-line reason each, final validator line.
