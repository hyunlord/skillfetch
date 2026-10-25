#!/bin/bash
# shallow-clone the stage 8 top 30 repositories (default branch) into ~/.skillfetch/work-staging
cd ~/.skillfetch/work-staging || exit 1
python3 -c "
import json
for r in json.load(open('$HOME/<e2e>/stage8/source-candidates.json'))[:30]: print(r['repo'])
" > repos30.txt
while read -r repo; do
  d="${repo/\//__}"
  if [ -d "$d/.git" ]; then echo "have $repo"; continue; fi
  if git clone -q --depth 1 "https://github.com/$repo" "$d" 2>err.txt; then echo "ok $repo $(git -C "$d" rev-parse --short HEAD)"; else echo "FAIL $repo $(head -1 err.txt)"; fi
done < repos30.txt
