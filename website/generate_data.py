"""
Generate data.js from raw_results_4.json
Converts scraped data into a compact JavaScript module for the static website.
"""
import json
import os

RAW_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'raw_results_4.json')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'data.js')

with open(RAW_PATH, 'r', encoding='utf-8') as f:
    raw = json.load(f)

students = []
for r in raw:
    enrollment = r.get('enrollment', '')
    status = r.get('result_status', 'UNKNOWN')
    if status == 'SCRAPE_FAILED':
        continue

    sgpa_raw = r.get('sgpa', '')
    try:
        sgpa = float(sgpa_raw) if sgpa_raw else None
    except:
        sgpa = None

    cgpa_raw = r.get('cgpa', '')
    try:
        cgpa = float(cgpa_raw) if cgpa_raw else None
    except:
        cgpa = None

    subjects = []
    for s in r.get('subjects', []):
        subjects.append({
            'code': s.get('course_code', ''),
            'tc': s.get('total_credit', ''),
            'ec': s.get('earned_credit', ''),
            'grade': s.get('grade', '')
        })

    students.append({
        'enrollment': enrollment,
        'name': r.get('student_name', '—'),
        'branch': r.get('branch', '—'),
        'branchCode': r.get('branch_short', '—'),
        'semester': r.get('semester', '4'),
        'status': r.get('status', ''),
        'result': status.upper() if status else '—',
        'sgpa': sgpa,
        'cgpa': cgpa,
        'subjects': subjects
    })

# Compute stats
total = len(students)
passed = sum(1 for s in students if s['result'] == 'PASS')
sgpas = [s['sgpa'] for s in students if s['sgpa'] is not None]
avg_sgpa = sum(sgpas) / len(sgpas) if sgpas else 0
max_sgpa = max(sgpas) if sgpas else 0
min_sgpa = min(sgpas) if sgpas else 0

branches = {}
for s in students:
    bc = s['branchCode']
    if bc not in branches:
        branches[bc] = {'count': 0, 'passed': 0, 'sgpas': [], 'name': s['branch']}
    branches[bc]['count'] += 1
    if s['result'] == 'PASS':
        branches[bc]['passed'] += 1
    if s['sgpa'] is not None:
        branches[bc]['sgpas'].append(s['sgpa'])

branch_stats = {}
for bc, info in branches.items():
    branch_stats[bc] = {
        'name': info['name'],
        'count': info['count'],
        'passed': info['passed'],
        'passRate': round(info['passed'] / info['count'] * 100, 1) if info['count'] > 0 else 0,
        'avgSGPA': round(sum(info['sgpas']) / len(info['sgpas']), 2) if info['sgpas'] else 0,
        'maxSGPA': round(max(info['sgpas']), 2) if info['sgpas'] else 0,
        'minSGPA': round(min(info['sgpas']), 2) if info['sgpas'] else 0
    }

# SGPA distribution (histogram buckets)
buckets = {f'{i}-{i+1}': 0 for i in range(0, 10)}
for s in sgpas:
    bucket_idx = min(int(s), 9)
    key = f'{bucket_idx}-{bucket_idx+1}'
    buckets[key] += 1

# Add rank to students (within overall and within branch)
sorted_by_sgpa = sorted([s for s in students if s['sgpa'] is not None], key=lambda x: x['sgpa'], reverse=True)
for rank, s in enumerate(sorted_by_sgpa, 1):
    s['rank'] = rank

# Branch ranks
for bc in branches:
    branch_students = sorted([s for s in students if s['branchCode'] == bc and s['sgpa'] is not None], key=lambda x: x['sgpa'], reverse=True)
    for rank, s in enumerate(branch_students, 1):
        s['branchRank'] = rank
        s['branchTotal'] = len(branch_students)

# For students without sgpa
for s in students:
    if 'rank' not in s:
        s['rank'] = None
    if 'branchRank' not in s:
        s['branchRank'] = None
        s['branchTotal'] = None

stats = {
    'total': total,
    'passed': passed,
    'passRate': round(passed / total * 100, 1) if total > 0 else 0,
    'avgSGPA': round(avg_sgpa, 2),
    'maxSGPA': round(max_sgpa, 2),
    'minSGPA': round(min_sgpa, 2),
    'branches': branch_stats,
    'distribution': buckets
}

# Write JS
js = f"// Auto-generated from raw_results_4.json\n"
js += f"const STATS = {json.dumps(stats, indent=2)};\n\n"
js += f"const STUDENTS = {json.dumps(students, indent=2)};\n"

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(js)

print(f"Generated data.js: {len(students)} students, {os.path.getsize(OUTPUT_PATH)} bytes")
