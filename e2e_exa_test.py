"""End-to-end timing test with Exa search."""
import json
import os
import time
import urllib.request
from dotenv import load_dotenv

load_dotenv('/Users/Lovegood/Desktop/Unveiling/.env')

BASE_URL = 'http://127.0.0.1:5001'
question = '人工智能会取代大量白领工作吗？'

start = time.time()
req = urllib.request.Request(
    f'{BASE_URL}/analyze',
    data=json.dumps({'question': question, 'language': '中文'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read().decode())
task_id = data['task_id']
print(f'[{time.time()-start:.2f}s] task_id={task_id}')

req = urllib.request.Request(f'{BASE_URL}/progress/{task_id}')
event_counts = {}
evidence_count = 0
last_ev_time = start

try:
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw_line in r:
            line = raw_line.decode('utf-8', errors='ignore').strip()
            if not line or line.startswith(':'):
                continue
            if line.startswith('data:'):
                payload = line[5:].strip()
                if not payload:
                    continue
                try:
                    ev = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                now = time.time()
                kind = ev.get('kind', 'unknown')
                event_counts[kind] = event_counts.get(kind, 0) + 1

                if kind == 'evidence_batch':
                    evidence_count += len(ev.get('evidence', []))
                    name = ev.get('evidence', [{}])[0].get('case_name', 'unnamed')
                    print(f'[{now-start:.2f}s] evidence: {name} (total {evidence_count})')
                elif kind == 'schedule':
                    entry = ev.get('entry', {})
                    reason = entry.get('reason', '')
                    print(f'[{now-start:.2f}s] schedule: {entry.get("author", "?")} / {entry.get("decision", "?")} ({reason})')
                elif kind == 'phase':
                    print(f'[{now-start:.2f}s] phase: {ev.get("phase", "?")}')
                elif kind == 'lens':
                    print(f'[{now-start:.2f}s] lens: {ev.get("lens", {}).get("name", "?")}')
                elif kind == 'done':
                    print(f'[{now-start:.2f}s] DONE')
                    break
                elif kind == 'error':
                    print(f'[{now-start:.2f}s] ERROR: {ev.get("error", "?")}')
                    break
                last_ev_time = now
except Exception as e:
    print(f'FAILED after {time.time()-start:.2f}s: {type(e).__name__}: {e}')

print(f'\nEvent counts: {event_counts}')
print(f'Total evidence: {evidence_count}')
print(f'Total time: {time.time()-start:.2f}s')
