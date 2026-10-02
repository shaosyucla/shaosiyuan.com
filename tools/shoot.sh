#!/usr/bin/env bash
# Headless screenshots of the local rebuild (and optionally the live site) for side-by-side checks.
#   bash shoot.sh new  home about ...     -> compare/new_<name>.png from http://127.0.0.1:8791
#   bash shoot.sh orig home about ...     -> compare/orig_<name>.png from https://www.shaosiyuan.com
# Optional: W=390 H=844 bash shoot.sh new home   (phone size)
CH="/c/Program Files/Google/Chrome/Application/chrome.exe"
OUT="/c/FACT Workplace/Numerical Code/Claude Workspace/website/compare"
W=${W:-1280}; H=${H:-2300}
mode=$1; shift
declare -A NEW=( [home]=index.html [about]=about.html [life]=life.html [contact]=contact.html
  [ornithopter]=towards-ornithopter.html [jumping]=jumping-vehicle.html [moments]=moments-mechanical.html
  [course]=course-projects.html [letgo]=jumping-vehicle/let-go.html [finaltests]=towards-ornithopter/final-tests.html )
declare -A OLD=( [home]= [about]=about [life]=life [contact]=contact [ornithopter]=towards-ornithopter
  [jumping]=jumping-vehicle [moments]=moments-mechanical [course]=course-projects [letgo]=jumping-vehicle/let-go
  [finaltests]=towards-ornithopter/final-tests )
for n in "$@"; do
  if [ "$mode" = new ]; then url="http://127.0.0.1:8791/${NEW[$n]}"; else url="https://www.shaosiyuan.com/${OLD[$n]}"; fi
  suffix=""; [ "$W" != 1280 ] && suffix="_${W}"
  "$CH" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=6000 \
    --window-size=$W,$H --screenshot="$(cygpath -w "$OUT/${mode}_${n}${suffix}.png")" "$url" 2>/dev/null
  echo "$OUT/${mode}_${n}${suffix}.png"
done
