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
    s = re.sub(r"[ً-ْـ‎‏‪-‮]", "", s)  # tashkeel, tatweel, bidi marks
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
