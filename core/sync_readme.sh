#!/bin/bash
# Sync core_rules.json → README.md (AUTO markers)
# Usage: bash anima-core/sync_readme.sh

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
JSON="$DIR/core_rules.json"
README="$DIR/README.md"

if [ ! -f "$JSON" ]; then echo "Error: $JSON not found"; exit 1; fi
if [ ! -f "$README" ]; then echo "Error: $README not found"; exit 1; fi

python3 -c "
import json, re

json_path = '$JSON'
readme_path = '$README'

d = json.load(open(json_path))
readme = open(readme_path).read()

# Sync verification_status
vs = d.get('verification_status', {})
if vs:
    vs_json = json.dumps(vs, indent=2, ensure_ascii=False)
    marker = 'verification_status'
    start = f'<!-- AUTO:{marker}:START -->'
    end = f'<!-- AUTO:{marker}:END -->'
    pattern = re.escape(start) + r'.*?' + re.escape(end)
    replacement = f'{start}\n\`\`\`json\n{vs_json}\n\`\`\`\n{end}'
    if start in readme:
        readme = re.sub(pattern, replacement, readme, flags=re.DOTALL)
        print(f'  synced: {marker} ({len(vs.get(\"ossified\",{}))-1} ossified, {len(vs.get(\"stable\",{}))-1} stable, {len(vs.get(\"failed\",{}))-1} failed)')

open(readme_path, 'w').write(readme)
print('Done.')
"
