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
