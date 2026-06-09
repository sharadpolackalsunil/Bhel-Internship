"""
FastAPI Backend for MITS Gwalior Dashboard
Serves scraped data (results, IUMS profiles, fees, academics) to the React frontend.
"""

import os
import csv
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MITS Gwalior Dashboard API")

# Allow CORS for local React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def read_csv_safe(filename):
    """Read a CSV file and return list of dicts. Returns [] if file missing."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if any(v.strip() for v in row.values())]


# ─── Results Endpoints ────────────────────────────────────────────

@app.get("/api/results")
def get_results():
    """Return all scraped result data (simplified to key columns)."""
    rows = read_csv_safe("results.csv")
    simplified = []
    for r in rows:
        simplified.append({
            "enrollment": r.get("Enrollment_No", ""),
            "name": r.get("Student_Name", ""),
            "father": r.get("Father_Name", ""),
            "branch": r.get("Branch", ""),
            "branch_code": r.get("Branch_Code", ""),
            "semester": r.get("Semester", ""),
            "program": r.get("Program", ""),
            "sgpa": _safe_float(r.get("SGPA", "")),
            "cgpa": _safe_float(r.get("CGPA", "")),
            "result_status": r.get("Result_Status", ""),
            "total_marks": r.get("Total_Marks", ""),
            "max_marks": r.get("Max_Marks", ""),
            "rank": _safe_int(r.get("Rank", "")),
        })
    return {"results": simplified, "total": len(simplified)}


@app.get("/api/analytics")
def get_analytics():
    """Pre-compute analytics from results data."""
    rows = read_csv_safe("results.csv")
    if not rows:
        return {"error": "No results data found"}

    simplified = []
    for r in rows:
        simplified.append({
            "enrollment": r.get("Enrollment_No", ""),
            "name": r.get("Student_Name", ""),
            "branch": r.get("Branch", ""),
            "branch_code": r.get("Branch_Code", ""),
            "sgpa": _safe_float(r.get("SGPA", "")),
            "result_status": r.get("Result_Status", ""),
            "rank": _safe_int(r.get("Rank", "")),
        })

    # ── Top 5 per branch ──
    branches = {}
    for s in simplified:
        bc = s["branch_code"] or s["branch"]
        if bc not in branches:
            branches[bc] = []
        branches[bc].append(s)

    top5_per_branch = {}
    for bc, students in branches.items():
        sorted_students = sorted(students, key=lambda x: x["sgpa"] or 0, reverse=True)
        top5_per_branch[bc] = sorted_students[:5]

    # ── Top 10 overall (department = entire AI dept) ──
    all_sorted = sorted(simplified, key=lambda x: x["sgpa"] or 0, reverse=True)
    top10_dept = all_sorted[:10]

    # ── Branch averages ──
    branch_averages = {}
    for bc, students in branches.items():
        sgpas = [s["sgpa"] for s in students if s["sgpa"] is not None]
        if sgpas:
            branch_averages[bc] = {
                "avg_sgpa": round(sum(sgpas) / len(sgpas), 2),
                "total_students": len(students),
                "pass_count": sum(1 for s in students if s["result_status"] and "PASS" in s["result_status"].upper() and "FAIL" not in s["result_status"].upper()),
                "fail_count": sum(1 for s in students if s["result_status"] and "FAIL" in s["result_status"].upper()),
            }

    # ── SGPA distribution ──
    sgpa_distribution = {"0-4": 0, "4-5": 0, "5-6": 0, "6-7": 0, "7-8": 0, "8-9": 0, "9-10": 0}
    for s in simplified:
        sgpa = s["sgpa"]
        if sgpa is None:
            continue
        if sgpa < 4: sgpa_distribution["0-4"] += 1
        elif sgpa < 5: sgpa_distribution["4-5"] += 1
        elif sgpa < 6: sgpa_distribution["5-6"] += 1
        elif sgpa < 7: sgpa_distribution["6-7"] += 1
        elif sgpa < 8: sgpa_distribution["7-8"] += 1
        elif sgpa < 9: sgpa_distribution["8-9"] += 1
        else: sgpa_distribution["9-10"] += 1

    return {
        "top5_per_branch": top5_per_branch,
        "top10_department": top10_dept,
        "branch_averages": branch_averages,
        "sgpa_distribution": sgpa_distribution,
        "total_students": len(simplified),
    }


# ─── IUMS Student Endpoints ──────────────────────────────────────

@app.get("/api/students")
def get_students():
    """Return list of IUMS students (profile summary)."""
    profiles = read_csv_safe("iums_profile.csv")
    academics = read_csv_safe("iums_academic.csv")

    # Build a lookup for academic data
    acad_lookup = {}
    for a in academics:
        acad_lookup[a.get("enrollment", "")] = a

    students = []
    for p in profiles:
        enroll = p.get("enrollment", "")
        acad = acad_lookup.get(enroll, {})
        students.append({
            "enrollment": enroll,
            "name": p.get("profile_name", ""),
            "branch": p.get("profile_branch", ""),
            "programme": p.get("profile_programme", ""),
            "cgpa": _safe_float(acad.get("overall_cgpa", "")),
        })
    return {"students": students}


@app.get("/api/student/{enrollment}")
def get_student_detail(enrollment: str):
    """Return full details for a specific IUMS student."""
    profiles = read_csv_safe("iums_profile.csv")
    fees = read_csv_safe("iums_fee.csv")
    academics = read_csv_safe("iums_academic.csv")

    profile = next((p for p in profiles if p.get("enrollment", "") == enrollment), None)
    fee = next((f for f in fees if f.get("enrollment", "") == enrollment), None)
    academic = next((a for a in academics if a.get("enrollment", "") == enrollment), None)

    if not profile:
        raise HTTPException(status_code=404, detail="Student not found")

    # Parse profile
    profile_data = {
        "name": profile.get("profile_name", ""),
        "dob": profile.get("profile_dob", ""),
        "father": profile.get("profile_father", ""),
        "mother": profile.get("profile_mother", ""),
        "gender": profile.get("profile_gender", ""),
        "programme": profile.get("profile_programme", ""),
        "branch": profile.get("profile_branch", ""),
        "category": profile.get("profile_category", ""),
        "email": profile.get("profile_email", ""),
        "address": profile.get("profile_address", ""),
        "city": profile.get("profile_city", ""),
        "state": profile.get("profile_state", ""),
        "pincode": profile.get("profile_pincode", ""),
        "phone": profile.get("profile_phone", ""),
        "admission_year": profile.get("profile_admission_year", "").replace(":", "").strip(),
    }

    # Parse fee data
    fee_data = []
    if fee:
        seen = set()
        for key, val in fee.items():
            if key == "enrollment":
                continue
            # Extract semester name from key like "fee_1st Sem_status"
            match = re.match(r"fee_(.+)_status", key)
            if match:
                sem_name = match.group(1)
                if sem_name not in seen:
                    seen.add(sem_name)
                    year_key = f"fee_{sem_name}_year"
                    fee_data.append({
                        "semester": sem_name,
                        "status": val,
                        "year": fee.get(year_key, ""),
                    })

    # Parse academic data
    academic_data = []
    cgpa = None
    if academic:
        cgpa = _safe_float(academic.get("overall_cgpa", ""))
        seen_sems = set()
        for key, val in academic.items():
            if key == "enrollment" or key == "overall_cgpa":
                continue
            match = re.match(r"sem_(\d+)_sgpa", key)
            if match:
                sem_num = match.group(1)
                if sem_num not in seen_sems:
                    seen_sems.add(sem_num)
                    academic_data.append({
                        "semester": int(sem_num),
                        "sgpa": _safe_float(val),
                        "session": academic.get(f"sem_{sem_num}_session", ""),
                        "result": academic.get(f"sem_{sem_num}_result", ""),
                    })
        academic_data.sort(key=lambda x: x["semester"])

    return {
        "enrollment": enrollment,
        "profile": profile_data,
        "fees": fee_data,
        "academic": academic_data,
        "cgpa": cgpa,
    }


def _safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
