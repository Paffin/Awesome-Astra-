import json
from pathlib import Path
import shutil
import subprocess
import sys
workspace = Path(sys.argv[1])
node = shutil.which('node')
if not node:
    print('Prerequisite missing: Node.js. No automatic installation.', file=sys.stderr)
    raise SystemExit(77)
for amount in (0, 1999):
    payload = json.loads(subprocess.check_output([sys.executable, '-I', str(workspace / 'backend.py'), str(amount)], text=True))
    assert payload == {'total_cents': amount, 'currency': 'USD'}
    script = "const {parseReceipt}=await import(process.argv[1]); console.log(parseReceipt(JSON.parse(process.argv[2])));"
    output = subprocess.check_output([node, '--input-type=module', '-e', script, (workspace / 'client.mjs').as_uri(), json.dumps(payload)], text=True).strip()
    assert output == f'{amount} USD'
schema = json.loads((workspace / 'schema.json').read_text())
assert 'total_cents' in schema['required'] and 'amount' not in schema['required']
assert schema['properties']['total_cents']['type'] == 'integer'
assert 'amount' not in schema['properties']
print('Python producer, JavaScript consumer and shared schema use the same wire field.')
