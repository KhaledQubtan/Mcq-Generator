#!/bin/bash
# usage: work/accept.sh <topic_id>  — re-validate, mark done, commit locally
set -e
cd /home/user/Mcq-Generator
t=$1
python3 validate_mcq.py work/output/$t.json --topic-id $t | grep -E "^questions|error\(s\)|^ERROR" 
n=$(python3 -c "import json;d=json.load(open('work/output/$t.json'));assert all(isinstance(q['topic_id'],str) for q in d);print(len(d))")
[ "$n" = "100" ] || { echo "COUNT $n"; exit 1; }
python3 lessons.py mark $t done --work work
git add -A >/dev/null && git commit -q -m "Add validated MCQs for topic $t

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018fLpaEgXzdsRGt1xgy8Vfr" && echo committed
