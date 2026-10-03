---
name: "arabic-maths-mcq-generator"
description: "توليد أسئلة اختيار من متعدد (MCQ) بالعربية لمادة كاملة (درس أو أكثر) من ملفات PDF الشرح والأسئلة (zip أو رابط Google Drive)، بصيغة JSON مع معادلات LaTeX. Use when the user wants MCQs generated from explanation PDFs and questions PDFs for one or more lessons."
---

# Arabic MCQ Generator: full subject, lesson by lesson

Generates Arabic multiple-choice questions for a whole subject. For every lesson in the user's manifest, the lesson's explanation PDF is the knowledge source and its questions PDF is the style reference. The skill loops over the lessons and runs the same per-lesson scenario for each one, then merges the results. Quality matters more than speed: every question must be correct, answerable from its lesson, and pass the validator.

## Step 0: Required inputs (hard gate, check before anything else)

Do NOT start reading PDFs or generating anything until BOTH of these are in hand:

1. **The PDF files**: every explanation PDF and questions PDF named in the manifest, provided in any of these forms (they can be combined):
   - **zip files**: one zip holding both sets (flat or in 2 folders), or a zip of explanation PDFs plus a separate zip of questions PDFs,
   - **Google Drive links**: a link to a zip file, to a single PDF, or to a folder (a folder may hold the PDFs directly, sub-folders, or zips),
   - PDFs or folders already attached or on disk.
2. **The lessons manifest** in exactly this JSON structure, pasted in the message or attached as a .json file. Each entry lists the lesson's questions PDF and explanation PDF by file name, and the lesson's topic_id. **topic_id is an input**: it always comes from this manifest and is never generated, renumbered or inferred by the skill.
```
[
    {
        "pdfs": [
            "اسئلة الوحدة {UNIT} درس {LESSON} {SUBJECT} {GRADE}.pdf",
            "الوحدة {UNIT} درس {LESSON} {SUBJECT} {GRADE}.pdf"
        ],
        "topic_id": "{TOPIC_ID}"
    }
]
```

If either is missing, reply with one short Arabic message that names what is missing (and, for the manifest, shows the template above), and stop. Do not guess file names or topic_ids.

Optional settings (use the defaults if not given, and state them in the start line):
- **Questions per lesson**: default 100. The user may give one number for all lessons or a number per topic_id.
- **correct_answer type**: integer 0–3 by default; if their platform needs "0"–"3" strings, pass `--answer-type str` to every validator run.

## Step 1: Set up and pre-flight

1. Write the two scripts at the end of this file to `lessons.py` and `validate_mcq.py` in the working directory (skip any that already exist in the skill's `scripts/` folder). If the manifest was pasted, save it unchanged to `manifest.json`.
2. If any source is a Google Drive link, get its files first (see **Google Drive links** below).
3. Run the pre-flight check, listing every source (zips, folders, PDFs, and any Drive links not yet downloaded):
```
python3 lessons.py prepare manifest.json <source1> [<source2> ...] --work work
```
   It downloads remaining Drive links, extracts every zip (fixing Arabic file names from Windows zips, and opening zips found inside folders or other zips), pools all PDFs from all sources, and matches every manifest file name against the pool (ignoring differences such as أ/ا, ة/ه, ى/ي, extra spaces). Folder layout does not matter; the manifest decides which file is which. It rejects unreadable sources, placeholders left unfilled, missing files, entries without exactly one questions file (name starts with «اسئلة») and one explanation file, and duplicate topic_ids. Identical copies of a file across sources are merged silently; different files with the same name produce a WARN.
4. **If it prints `Pre-flight FAILED`, stop.** Send the user the ERROR lines (translated into short Arabic where helpful, keeping the file names exactly), and ask them to fix the manifest or the files. Do not run any lesson until pre-flight passes. WARN lines (for example PDFs not listed in the manifest) are reported in the start line but do not block.
5. When it passes, `work/lessons.json` lists the lessons in manifest order with resolved paths, and `work/progress.json` tracks each lesson's status.

Then send one short line saying how many lessons will run, questions per lesson, and any warnings, and begin. Do not wait for approval.

### Google Drive links

Try these in order, and stop at the first that works:

1. **Google Drive connector.** If the session has Google Drive tools loaded (check the tool list, and ToolSearch for "drive" if deferred tools exist), use them. Take the file or folder id from the link (`/file/d/<id>`, `/folders/<id>`, `?id=<id>`), list the folder's contents if it is a folder (including sub-folders), and download each PDF or zip into `work/downloads/`, following the connector's own tool descriptions. Then pass `work/downloads` to `prepare` as a source. If a connector file tool only returns extracted text and not the file itself, do not use that text as a substitute for the PDF; go to the next option.
2. **Direct download.** `python3 lessons.py fetch <link> --work work` (or just pass the link to `prepare`) downloads it with gdown. This works only where the network can reach drive.google.com (for example Claude Code on the user's computer) and only for links shared as «Anyone with the link». Drive folders download at most 50 files per folder; with more files, ask for a zip. If it prints `DRIVE_BLOCKED`, do not retry with curl, wget or any other download method, because the network refuses them all.
3. **Ask the user.** In one short Arabic message, say the Drive link could not be opened from here, and offer two options: connect Google Drive in the connector settings (if a Google Drive connector exists for them but is not connected or not enabled in this chat) and send the link again, or upload the files as zip(s). Do not start any lesson meanwhile.

If some sources loaded and a Drive link failed, still stop: pre-flight needs every manifest file.

## Step 2: Lesson loop

```
python3 lessons.py status --work work     # shows every lesson's status and NEXT
```
For each lesson in `lessons.json` order whose status is not `done`:

1. `python3 lessons.py mark <topic_id> in_progress --work work`
2. Create `work/lessons/<topic_id>/` and do all of that lesson's intermediate files there.
3. Run the **Per-lesson scenario** below with:
   - explanation PDF = the lesson's `explanation` path, questions PDF = its `questions` path,
   - `topic_id` = the lesson's `topic_id_value` from `lessons.json`, copied exactly as passed in the manifest (same characters, same JSON type: a string stays a string, a number stays a number), identical on every question of the lesson. Never invent, renumber or change it,
   - ids = `"<topic_id>_001"`, `"<topic_id>_002"`, … so they stay unique across the whole subject.
4. Save the final, validated, balanced array to `work/output/<topic_id>.json`.
5. `python3 lessons.py mark <topic_id> done --work work`, then send the user one progress line: lesson title, topic_id, question count, lessons remaining.
6. If a lesson cannot be completed (unreadable or empty PDF, content that cannot support the requested count), save whatever passed validation, run `mark <topic_id> failed --note "<reason>"`, tell the user in one line, and continue with the next lesson. Never stop the whole run for one lesson.

Keep lessons separate: each lesson's questions come only from its own explanation PDF, with examples only from its own questions PDF. Once a lesson is done, rely on its files, not on memory of it.

**Resuming:** if the session is interrupted or the user says «كمّل», run `lessons.py status` and continue from NEXT. Lessons already `done` are never regenerated unless the user asks.

**Many lessons:** when a subagent tool is available and there are more than 3 lessons, you may give each lesson to a subagent. Pass it the lesson's two PDF paths, topic_id, question count, and the "Output rules", "Per-lesson scenario" and `validate_mcq.py` sections of this file verbatim, and have it write `work/output/<topic_id>.json`. Re-run the validator on its output yourself (with `--topic-id`) before marking the lesson done.

## Step 3: Merge and deliver

```
python3 lessons.py merge --work work --out all_questions.json
python3 validate_mcq.py all_questions.json
```
- `merge` refuses to run while any lesson is not `done`. If some lessons failed, ask the user whether to deliver without them (`--force`) or retry them first; if they are not there to answer, deliver without them and say so.
- The merged validation checks for duplicate ids and near-duplicate questions across lessons; fix real duplicates in the lesson file, then merge again.
- Zip `work/output/` as `questions_by_lesson.zip`.
- Send `all_questions.json` and `questions_by_lesson.zip`. In chat give only a short table: topic_id, lesson title, question count, status. Both JSON files hold only the JSON array.

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

## lessons.py

```python
#!/usr/bin/env python3
"""Multi-lesson helper for the Arabic MCQ skill.

  prepare  <manifest.json> <SOURCE> [<SOURCE> ...] [--work DIR]
      Pre-flight. Each SOURCE may be a .zip, a folder, a single .pdf, or a
      Google Drive link (file or folder). Zips are extracted (fixing Arabic file
      names from Windows zips; zips nested inside zips or folders are opened too).
      Every manifest file name is matched against all PDFs found, so these all
      work: one zip with both sets, a zip with 2 folders, a zip of explanations
      plus a zip of questions, a Drive folder, etc.
      Writes DIR/lessons.json + DIR/progress.json. Exit 1 = do not start.

  fetch    <drive-link> [--work DIR]
      Download a Google Drive file or folder (shared as "Anyone with the link")
      into DIR/downloads/ and print the local path. Needs network access to
      drive.google.com; prints DRIVE_BLOCKED when the network refuses it.

  status   [--work DIR]
      Show per-lesson progress (pending / in_progress / done / failed).

  mark     <topic_id> <status> [--note TEXT] [--work DIR]
      Update one lesson's status in progress.json.

  merge    [--work DIR] [--out FILE]
      Combine DIR/output/<topic_id>.json in manifest order into one JSON array,
      checking ids are unique and topic_ids match the manifest.
"""
import argparse, hashlib, inspect, json, os, re, subprocess, sys, unicodedata, zipfile, shutil
from collections import Counter

def norm(s):
    s = unicodedata.normalize("NFC", str(s)).strip().lower()
    s = re.sub(r"[ً-ْـ--]", "", s)  # tashkeel, tatweel, bidi marks
    s = re.sub(r"[إأآٱا]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    if s.endswith(".pdf"):
        s = s[:-4].strip()
    return s


def is_q_name(name):
    n = norm(os.path.basename(name))
    return n.startswith("اسئله") or n.startswith("سؤال") or n.startswith("questions")


def fix_zip_name(info):
    if info.flag_bits & 0x800:
        return info.filename
    raw = info.filename.encode("cp437", errors="replace")
    for enc in ("utf-8", "cp1256"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return info.filename


DRIVE_RE = re.compile(r"https?://(?:drive|docs)\.google\.com/", re.I)


def drive_id(url):
    for pat, kind in ((r"/folders/([\w-]{10,})", "folder"), (r"/file/d/([\w-]{10,})", "file"),
                      (r"[?&]id=([\w-]{10,})", "file"), (r"/d/([\w-]{10,})", "file")):
        m = re.search(pat, url)
        if m:
            return m.group(1), kind
    return None, None


def fetch_drive(url, work):
    """Return local path of the downloaded file/folder, or raise RuntimeError."""
    fid, kind = drive_id(url)
    if not fid:
        raise RuntimeError(f"cannot read a Google Drive file or folder id from: {url}")
    try:
        import gdown  # noqa
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "gdown"],
                       check=False, capture_output=True)
        try:
            import gdown  # noqa
        except ImportError:
            raise RuntimeError("could not install gdown (pip unavailable)")
    import gdown
    out = os.path.join(work, "downloads", fid)
    os.makedirs(out, exist_ok=True)
    try:
        if kind == "folder":
            kw = {"remaining_ok": True} if "remaining_ok" in inspect.signature(gdown.download_folder).parameters else {}
            files = gdown.download_folder(id=fid, output=out, quiet=True, **kw)
            if not files:
                raise RuntimeError("folder is empty or not shared as 'Anyone with the link'")
            if len(files) >= 50:
                print(f"WARN  Drive folder download is capped at 50 files per folder; got {len(files)}. "
                      "If files are missing, share a zip of the folder instead.")
            return out
        path = gdown.download(id=fid, output=out + os.sep, quiet=True)
        if not path:
            raise RuntimeError("file not downloadable — is it shared as 'Anyone with the link'?")
        return path
    except RuntimeError:
        raise
    except Exception as e:
        msg = str(e)
        if "403" in msg or "Tunnel connection failed" in msg or "ProxyError" in msg or "Max retries" in msg:
            raise RuntimeError("DRIVE_BLOCKED: this environment's network cannot reach drive.google.com")
        raise RuntimeError(f"Drive download failed: {msg.splitlines()[0][:200]}")


def extract_zip(src, dest):
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            name = fix_zip_name(info).replace("\\", "/")
            if name.startswith("__MACOSX/") or "/." in "/" + name:
                continue
            target = os.path.normpath(os.path.join(dest, name))
            if not os.path.abspath(target).startswith(os.path.abspath(dest)):
                continue
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as fsrc, open(target, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
    return dest


def collect_sources(sources, work, errors, info):
    """Resolve every source into local folders/files; open nested zips once."""
    roots = []
    ex_root = os.path.join(work, "source")
    shutil.rmtree(ex_root, ignore_errors=True)
    for n, src in enumerate(sources, 1):
        src = src.strip()
        if DRIVE_RE.match(src):
            try:
                src = fetch_drive(src, work)
                info.append(f"OK downloaded from Drive -> {src}")
            except RuntimeError as e:
                errors.append(f"source {n}: {e}")
                continue
        if os.path.isdir(src):
            roots.append(src)
        elif os.path.isfile(src) and zipfile.is_zipfile(src):
            roots.append(extract_zip(src, os.path.join(ex_root, f"{n}_{os.path.splitext(os.path.basename(src))[0]}")))
            info.append(f"OK extracted {os.path.basename(src)}")
        elif os.path.isfile(src) and src.lower().endswith(".pdf"):
            roots.append(src)
        else:
            errors.append(f"source {n}: not a zip, folder, PDF or Google Drive link: {src}")
    # open zips found inside the sources (one level)
    for r in list(roots):
        if os.path.isdir(r):
            for dp, _, fs in os.walk(r):
                for f in fs:
                    p = os.path.join(dp, f)
                    if f.lower().endswith(".zip") and zipfile.is_zipfile(p):
                        roots.append(extract_zip(p, os.path.join(ex_root, "nested", hashlib.md5(p.encode()).hexdigest()[:8])))
                        info.append(f"OK extracted nested {f}")
    return roots


def index_pdfs(roots):
    idx, seen = {}, {}
    for r in roots:
        files = [r] if os.path.isfile(r) else [os.path.join(dp, f) for dp, _, fs in os.walk(r) for f in fs]
        for p in files:
            if not p.lower().endswith(".pdf"):
                continue
            h = hashlib.md5(open(p, "rb").read()).hexdigest()
            k = norm(os.path.basename(p))
            if seen.get((k, h)):
                continue          # identical copy from another source
            seen[(k, h)] = p
            idx.setdefault(k, []).append(p)
    return idx


def prepare(a):
    os.makedirs(a.work, exist_ok=True)
    errors, warns, info = [], [], []

    try:
        manifest = json.load(open(a.manifest, encoding="utf-8-sig"))
    except Exception as e:
        sys.exit(f"ERROR manifest: cannot parse JSON: {e}")
    if not isinstance(manifest, list) or not manifest:
        sys.exit("ERROR manifest: must be a non-empty JSON array of {\"pdfs\": [...], \"topic_id\": ...}")

    roots = collect_sources(a.sources, a.work, errors, info)
    if errors:
        for m in info: print(m)
        for e in errors: print("ERROR", e)
        print("Pre-flight FAILED — could not load every source.")
        sys.exit(1)
    pool = index_pdfs(roots)
    if not pool:
        print("ERROR no PDF files found in the sources"); sys.exit(1)
    info.append(f"OK {sum(len(v) for v in pool.values())} PDF file(s) found")
    used = set()
    lessons, tids = [], Counter()

    for i, ent in enumerate(manifest, 1):
        tag = f"lesson {i}"
        if not isinstance(ent, dict) or set(ent) - {"pdfs", "topic_id"} or "pdfs" not in ent or "topic_id" not in ent:
            errors.append(f"{tag}: entry must have exactly the keys 'pdfs' and 'topic_id'"); continue
        tid = str(ent["topic_id"]).strip()
        pdfs = ent["pdfs"]
        if not tid or "{" in tid:
            errors.append(f"{tag}: topic_id is empty or still a placeholder: {ent['topic_id']!r}")
        tids[tid] += 1
        if not (isinstance(pdfs, list) and len(pdfs) == 2 and all(isinstance(p, str) for p in pdfs)):
            errors.append(f"{tag} (topic {tid}): 'pdfs' must list exactly 2 file names"); continue
        for p in pdfs:
            if re.search(r"\{[A-Z_]+\}", p):
                errors.append(f"{tag} (topic {tid}): file name still has a placeholder: {p}")
        qn = [p for p in pdfs if is_q_name(p)]
        en = [p for p in pdfs if not is_q_name(p)]
        if len(qn) != 1 or len(en) != 1:
            errors.append(f"{tag} (topic {tid}): need one questions file (name starts with 'اسئلة') and one explanation file, got {pdfs}")
            continue
        found = {}
        for role, name in (("questions", qn[0]), ("explanation", en[0])):
            k = norm(name)
            hits = pool.get(k) or []
            if not hits:
                close = [os.path.basename(v[0]) for kk, v in pool.items()
                         if is_q_name(kk) == (role == "questions")
                         and (kk.split()[-3:] == k.split()[-3:] or kk.replace(" ", "") == k.replace(" ", ""))]
                hint = f" — did you mean: {close[:2]}" if close else ""
                errors.append(f"{tag} (topic {tid}): {role} file not found: {name}{hint}")
                continue
            if len(hits) > 1:
                warns.append(f"{tag} (topic {tid}): {len(hits)} different files named {name}; using {hits[0]}")
            found[role] = hits[0]
            used.update(hits)
        if len(found) == 2:
            lessons.append({"order": i, "topic_id": tid, "topic_id_value": ent["topic_id"],
                            "title": os.path.splitext(os.path.basename(found["explanation"]))[0],
                            "explanation": os.path.abspath(found["explanation"]),
                            "questions": os.path.abspath(found["questions"])})

    for t, n in tids.items():
        if n > 1 and t:
            errors.append(f"topic_id {t!r} is used by {n} lessons — each lesson needs its own topic_id")
    base = os.path.commonpath([os.path.abspath(r) for r in roots]) if roots else ""
    for paths in pool.values():
        for p in paths:
            if p not in used:
                warns.append(f"not in manifest (will be ignored): {os.path.relpath(p, base) if base else p}")

    for m in info: print(m)
    for w in warns: print("WARN ", w)
    for e in errors: print("ERROR", e)
    print(f"\n{len(manifest)} lesson(s) in manifest, {len(lessons)} resolved, {len(errors)} error(s), {len(warns)} warning(s)")
    if errors:
        print("Pre-flight FAILED — fix the manifest or the source files before starting.")
        sys.exit(1)

    json.dump(lessons, open(os.path.join(a.work, "lessons.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    pp = os.path.join(a.work, "progress.json")
    old = json.load(open(pp, encoding="utf-8")) if os.path.exists(pp) else {}
    prog = {l["topic_id"]: old.get(l["topic_id"], {"status": "pending", "note": ""}) for l in lessons}
    json.dump(prog, open(pp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.makedirs(os.path.join(a.work, "output"), exist_ok=True)
    print(f"Pre-flight OK -> {a.work}/lessons.json")
    for l in lessons:
        print(f"  {l['order']:>2}. topic {l['topic_id']}: {l['title']}  [{prog[l['topic_id']]['status']}]")


def fetch(a):
    try:
        print(fetch_drive(a.url, a.work))
    except RuntimeError as e:
        print("ERROR", e); sys.exit(1)


def load(a):
    lessons = json.load(open(os.path.join(a.work, "lessons.json"), encoding="utf-8"))
    pp = os.path.join(a.work, "progress.json")
    return lessons, json.load(open(pp, encoding="utf-8")), pp


def status(a):
    lessons, prog, _ = load(a)
    for l in lessons:
        p = prog.get(l["topic_id"], {})
        out = os.path.join(a.work, "output", f"{l['topic_id']}.json")
        n = len(json.load(open(out, encoding="utf-8"))) if os.path.exists(out) else 0
        print(f"{l['order']:>2}. topic {l['topic_id']:<8} {p.get('status','?'):<12} {n:>4} q  {l['title']}  {p.get('note','')}")
    c = Counter(p["status"] for p in prog.values())
    print(dict(c))
    nxt = next((l for l in lessons if prog[l["topic_id"]]["status"] != "done"), None)
    print(f"NEXT: topic {nxt['topic_id']} — {nxt['title']}" if nxt else "ALL DONE")


def mark(a):
    lessons, prog, pp = load(a)
    if a.topic_id not in prog:
        sys.exit(f"ERROR unknown topic_id {a.topic_id}")
    prog[a.topic_id] = {"status": a.status, "note": a.note or ""}
    json.dump(prog, open(pp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"topic {a.topic_id} -> {a.status}")


def merge(a):
    lessons, prog, _ = load(a)
    allq, ids, errors = [], Counter(), []
    for l in lessons:
        f = os.path.join(a.work, "output", f"{l['topic_id']}.json")
        if prog[l["topic_id"]]["status"] != "done" or not os.path.exists(f):
            errors.append(f"topic {l['topic_id']} is not done ({prog[l['topic_id']]['status']})"); continue
        qs = json.load(open(f, encoding="utf-8"))
        bad = [q["id"] for q in qs if str(q.get("topic_id")) != l["topic_id"]]
        if bad:
            errors.append(f"topic {l['topic_id']}: {len(bad)} question(s) with a different topic_id, e.g. {bad[:3]}")
        for q in qs:
            ids[q["id"]] += 1
        allq += qs
        print(f"topic {l['topic_id']}: {len(qs)} questions")
    dup = [k for k, n in ids.items() if n > 1]
    if dup:
        errors.append(f"duplicate ids across lessons: {dup[:5]}")
    for e in errors: print("ERROR", e)
    if errors and not a.force:
        sys.exit(1)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(allq, fh, ensure_ascii=False, indent=2)
    print(f"merged {len(allq)} questions -> {a.out}")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prepare"); p.add_argument("manifest"); p.add_argument("sources", nargs="+")
    p = sp.add_parser("fetch"); p.add_argument("url")
    p = sp.add_parser("status")
    p = sp.add_parser("mark"); p.add_argument("topic_id"); p.add_argument("status", choices=["pending", "in_progress", "done", "failed"]); p.add_argument("--note")
    p = sp.add_parser("merge"); p.add_argument("--out", default="all_questions.json"); p.add_argument("--force", action="store_true")
    for s in sp.choices.values():
        s.add_argument("--work", default="work")
    a = ap.parse_args()
    {"prepare": prepare, "fetch": fetch, "status": status, "mark": mark, "merge": merge}[a.cmd](a)


if __name__ == "__main__":
    main()
```

## validate_mcq.py

```python
#!/usr/bin/env python3
"""Validate (and optionally rebalance) an Arabic MCQ JSON array.

Usage:
  python validate_mcq.py questions.json [--examples examples.json]
                        [--answer-type int|str] [--topic-id ID]
                        [--rebalance out.json]

Exit code 1 if any ERROR is found. WARNINGs need human/Claude review.
"""
import json, re, sys, random, argparse, unicodedata
from collections import Counter
from difflib import SequenceMatcher

KEYS = ["id", "question", "choice1", "choice2", "choice3", "choice4",
        "correct_answer", "topic_id"]
CHOICES = ["choice1", "choice2", "choice3", "choice4"]

# Ready-made Unicode math symbols are forbidden (LaTeX only).
UNICODE_MATH = set("×÷√∛∜²³¹⁰⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾₀₁₂₃₄₅₆₇₈₉₊₋πθαβγδΔλμσΣΩωφΦ∞≤≥≠≈≡±∓∑∏∫∂∇°′″→←↔⇒⇔∈∉⊂⊃⊆⊇∪∩∅ℝℕℤℚ½⅓¼¾⅔·−∠⊥∥△")
ARABIC_DIGITS = re.compile(r"[٠-٩۰-۹]")
# Control chars after json parsing => a single backslash was used
# (e.g. "\frac" -> form feed, "\theta" -> tab, "\neq" -> newline, "\beta" -> backspace)
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\t\r\n]")

HARD_REFS = ["السؤال السابق", "الأسئلة السابقة", "الشكل المقابل", "الشكل التالي",
             "الجدول المقابل", "الجدول التالي", "الرسم المقابل", "الرسم التالي",
             "الشكل البياني", "النص السابق", "من النص", "في النص", "المصدر",
             "الكتاب", "أعلاه", "كما في الشكل", "انظر"]
SOFT_REFS = [r"(?<!\w)[وفبل]?الشكل(?!\w)", r"(?<!\w)[وفبل]?الجدول(?!\w)",
             r"(?<!\w)[وفبل]?النص(?!\w)", r"(?<!\w)[وفبل]?الرسم(?!\w)"]
ALL_NONE = ["جميع ما سبق", "كل ما سبق", "لا شيء مما سبق", "جميع الإجابات", "كل الإجابات"]


def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    s = re.sub(r"[ً-ْـ]", "", s)          # tashkeel + tatweel
    s = re.sub(r"[إأآا]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", "", s)


def math_segments(s):
    s2 = s.replace(r"\$", "")
    return re.findall(r"\$([^$]*)\$", s2), s2.count("$")


def check_text(field, s, err, warn):
    if CTRL.search(s):
        err(f"{field}: control character found -> a LaTeX command was written with a single backslash (use \\\\ in the JSON file)")
    if r"\(" in s or r"\[" in s:
        err(f"{field}: uses \\( or \\[ delimiters; use $...$ only")
    if "$$" in s:
        warn(f"{field}: uses $$...$$; the spec asks for $...$")
    segs, n = math_segments(s)
    if n % 2:
        err(f"{field}: odd number of $ (unclosed math)")
    bad = sorted({c for c in s if c in UNICODE_MATH})
    if bad:
        err(f"{field}: Unicode math symbols {bad} — write them in LaTeX")
    for m in segs:
        if ARABIC_DIGITS.search(m):
            err(f"{field}: Arabic-Indic digits inside math: ${m}$ — use 0-9")
        if m.count("{") != m.count("}"):
            err(f"{field}: unbalanced braces in ${m}$")
        stripped = re.sub(r"\\[A-Za-z]+", "", m)
        latin = re.findall(r"(?<![A-Za-z])[A-Za-z](?![A-Za-z])", stripped)
        if latin:
            warn(f"{field}: Latin variable(s) {sorted(set(latin))} in ${m}$ — use س، ص، ع if the explanation is Arabic")
    outside = re.sub(r"\$[^$]*\$", "", s.replace(r"\$", ""))
    if ARABIC_DIGITS.search(outside):
        warn(f"{field}: Arabic-Indic digits outside math — prefer 0-9 for consistency")
    if re.search(r"\\[A-Za-z]+", outside):
        err(f"{field}: LaTeX command outside $...$")
    words = re.findall(r"[A-Za-z]{4,}", outside)
    if words:
        warn(f"{field}: English words outside math {sorted(set(words))[:5]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--examples", help="JSON list of example question strings (or objects with 'question')")
    ap.add_argument("--answer-type", choices=["int", "str"], default="int")
    ap.add_argument("--rebalance", metavar="OUT", help="shuffle choices so correct answers spread evenly over 0-3, write OUT")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--topic-id", help="every question must have exactly this topic_id (the lesson's id from the manifest)")
    a = ap.parse_args()

    raw = open(a.file, encoding="utf-8").read()
    if raw.lstrip()[:1] != "[" or raw.rstrip()[-1:] != "]":
        print("ERROR file: must contain only a JSON array (no markdown fences or text)"); sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR file: invalid JSON: {e}\n  Hint: \\sin, \\cos, \\sqrt... with a single backslash are invalid JSON escapes; write \\\\sin")
        sys.exit(1)

    errors, warnings = [], []
    ids, qnorms = Counter(), []
    for i, q in enumerate(data):
        tag = f"[{i}] id={q.get('id') if isinstance(q, dict) else '?'}"
        err = lambda m: errors.append(f"{tag} {m}")
        warn = lambda m: warnings.append(f"{tag} {m}")
        if not isinstance(q, dict):
            err("item is not an object"); continue
        if list(q.keys()) != KEYS:
            missing, extra = set(KEYS) - set(q), set(q) - set(KEYS)
            if missing or extra:
                err(f"keys mismatch missing={sorted(missing)} extra={sorted(extra)}")
            else:
                warn("keys out of schema order")
        ids[str(q.get("id"))] += 1
        ca = q.get("correct_answer")
        if a.answer_type == "int":
            if not (isinstance(ca, int) and not isinstance(ca, bool) and 0 <= ca <= 3):
                err(f"correct_answer must be integer 0-3, got {ca!r}")
        else:
            if ca not in ("0", "1", "2", "3"):
                err(f"correct_answer must be string '0'-'3', got {ca!r}")
        if q.get("topic_id") in (None, ""):
            err("topic_id is empty")
        elif a.topic_id is not None and str(q.get("topic_id")) != str(a.topic_id):
            err(f"topic_id must be {a.topic_id!r} for this lesson, got {q.get('topic_id')!r}")
        for f in ["question"] + CHOICES:
            v = q.get(f)
            if not isinstance(v, str) or not v.strip():
                err(f"{f} empty or not a string"); continue
            check_text(f, v, err, warn)
        qt = str(q.get("question", ""))
        for r in HARD_REFS:
            if r in qt or any(r in str(q.get(c, "")) for c in CHOICES):
                err(f"refers to external context: '{r}' — question must be self-contained")
        for r in SOFT_REFS:
            if re.search(r, qt):
                warn(f"mentions a figure/table/text word ({r}) — confirm it is not a reference to missing context")
        ch = [str(q.get(c, "")) for c in CHOICES]
        nc = [norm(c) for c in ch]
        if len(set(nc)) < 4:
            err("duplicate choices")
        for c in ch:
            if any(x in c for x in ALL_NONE):
                warn(f"choice uses 'all/none of the above': {c}")
            if "(" in c and any(w in c for w in ["مثل", "مثال", "لأن", "صحيح"]):
                warn(f"choice may contain a hint/example: {c}")
        try:
            k = int(ca)
            if not 0 <= k <= 3:
                raise ValueError
            lens = [len(x) for x in nc]
            others = [l for j, l in enumerate(lens) if j != k]
            if others and lens[k] > 1.8 * max(others) and lens[k] > 20:
                warn("correct choice is much longer than the others (length hint)")
        except (TypeError, ValueError):
            pass
        qnorms.append((tag, norm(qt)))

    for k, n in ids.items():
        if n > 1:
            errors.append(f"id '{k}' used {n} times")

    for x in range(len(qnorms)):
        for y in range(x + 1, len(qnorms)):
            sm = SequenceMatcher(None, qnorms[x][1], qnorms[y][1])
            if sm.real_quick_ratio() <= 0.9 or sm.quick_ratio() <= 0.9:
                continue
            r = sm.ratio()
            if r > 0.9:
                warnings.append(f"near-duplicate questions {qnorms[x][0]} ~ {qnorms[y][0]} ({r:.2f})")

    if a.examples:
        ex = json.load(open(a.examples, encoding="utf-8"))
        ex = [norm(e["question"] if isinstance(e, dict) else e) for e in ex]
        for tag, qn in qnorms:
            for e in ex:
                sm = SequenceMatcher(None, qn, e)
                if sm.real_quick_ratio() <= 0.85 or sm.quick_ratio() <= 0.85:
                    continue
                r = sm.ratio()
                if r > 0.85:
                    warnings.append(f"{tag} too close to a source question ({r:.2f}) — rephrase, don't copy")
                    break

    dist = Counter(str(q.get("correct_answer")) for q in data if isinstance(q, dict))
    print(f"questions: {len(data)} | correct_answer distribution: {dict(sorted(dist.items()))}")
    topics = Counter(str(q.get("topic_id")) for q in data if isinstance(q, dict))
    print(f"per topic_id: {dict(sorted(topics.items()))}")
    for e in errors: print("ERROR", e)
    for w in warnings: print("WARN ", w)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")

    if a.rebalance:
        if errors:
            print("Not rebalancing while errors exist."); sys.exit(1)
        rng = random.Random(a.seed)
        targets = [i % 4 for i in range(len(data))]
        rng.shuffle(targets)
        for q, t in zip(data, targets):
            ch = [q[c] for c in CHOICES]
            k = int(q["correct_answer"])
            correct = ch.pop(k)
            rng.shuffle(ch)
            ch.insert(t, correct)
            for c, v in zip(CHOICES, ch):
                q[c] = v
            q["correct_answer"] = t if a.answer_type == "int" else str(t)
        with open(a.rebalance, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"rebalanced -> {a.rebalance}: {dict(sorted(Counter(str(q['correct_answer']) for q in data).items()))}")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
```