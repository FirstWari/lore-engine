#!/bin/bash
# NotebookLM smoke test: notebook -> transcript source -> long slide deck -> PDF -> A4. Uses ~/work/bin/nlm.
set -u
cd "$HOME/work/lore-engine" || exit 1
NAME="${1:-Lore Test - UX lifecycle}"
SRC="${2:-$(ls -d results/*product-development-life-cycle*/transcript.txt | head -1)}"
OUT="${3:-$HOME/work/lore-engine/results/nlm-smoke}"
mkdir -p "$OUT"
echo "source: $SRC ($(wc -w < "$SRC") words)"

echo "--- notebook"
NB=$(~/work/bin/nlm list --json 2>/dev/null | python3 -c '
import json,sys
data=json.load(sys.stdin); items=data if isinstance(data,list) else data.get("notebooks") or data.get("items") or []
name=sys.argv[1]
for n in items:
    if (n.get("title") or n.get("name")) == name: print(n.get("id") or n.get("notebook_id")); break
' "$NAME")
if [ -z "$NB" ]; then
  ~/work/bin/nlm create "$NAME" --json > /tmp/nb_create.json 2>&1
  NB=$(python3 -c 'import json,sys;d=json.load(open("/tmp/nb_create.json"));print(d.get("id") or d.get("notebook_id") or (d.get("notebook") or {}).get("id") or "")')
fi
echo "notebook id: $NB"; [ -z "$NB" ] && { echo "no notebook id"; exit 1; }
~/work/bin/nlm use "$NB" 2>&1 | tail -1

echo "--- source add"
~/work/bin/nlm source add "$SRC" --json 2>&1 | tail -20 | cut -c1-300

echo "--- generate slide-deck (long)"
START=$(date +%s)
~/work/bin/nlm generate slide-deck --length long --wait --timeout 1200 --json 2>&1 | tail -30 | cut -c1-400
echo "generation took $(( $(date +%s) - START )) s"

echo "--- download slide-deck"
~/work/bin/nlm download slide-deck --help 2>&1 | grep -E '^\s+-' | head -8
~/work/bin/nlm download slide-deck "$OUT/slides.pdf" 2>&1 | tail -3 | cut -c1-300 || ~/work/bin/nlm download slide-deck --output "$OUT/slides.pdf" 2>&1 | tail -3
ls -la "$OUT"
PDF=$(ls "$OUT"/*.pdf 2>/dev/null | head -1)
if [ -n "$PDF" ]; then
  echo "--- A4"; ~/work/bin/yatay-a4 "$PDF" "$OUT/slides_a4.pdf"
  ~/work/yatay-a4/.venv/bin/python -c "from pypdf import PdfReader as R; r=R('$OUT/slides_a4.pdf'); print(len(r.pages), 'pages', r.pages[0].mediabox)"
fi
echo "--- cleanup: notebook kept for inspection (id $NB); delete with: nlm delete $NB"
