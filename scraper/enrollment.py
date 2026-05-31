"""
Enrollment Number Generator
==============================
Generates enrollment numbers for 3 branches at MITS Gwalior:
    - BTAD24O1001 to BTAD24O1070  (AI & Data Science)
    - BTAM24O1001 to BTAM24O1070  (AI & Machine Learning)
    - BTAI24O1001 to BTAI24O1070  (Artificial Intelligence)

Format: BTxx24O1YYY
    BT  = B.Tech
    xx  = Branch code (AD/AM/AI)
    24  = Year
    O1  = Section/campus code
    YYY = Roll number (001-070)
"""

# Branch configuration
BRANCHES = {
    'BTAD': {
        'code': 'BTAD',
        'prefix': 'BTAD24O1',
        'name': 'AI & Data Science',
        'short_name': 'AI_DS',
        'start_roll': 1,
        'end_roll': 70,
    },
    'BTAM': {
        'code': 'BTAM',
        'prefix': 'BTAM24O1',
        'name': 'AI & Machine Learning',
        'short_name': 'AI_ML',
        'start_roll': 1,
        'end_roll': 70,
    },
    'BTAI': {
        'code': 'BTAI',
        'prefix': 'BTAI24O1',
        'name': 'Artificial Intelligence',
        'short_name': 'AI',
        'start_roll': 1,
        'end_roll': 70,
    },
}

SEMESTER = 4
TOTAL_STUDENTS = sum(
    b['end_roll'] - b['start_roll'] + 1 for b in BRANCHES.values()
)


def generate_enrollment_numbers(branch_code=None):
    """
    Generate enrollment numbers.

    Args:
        branch_code: Optional. One of 'BTAD', 'BTAM', 'BTAI'.
                     If None, generates for all branches.

    Returns:
        List of tuples: (enrollment_number, branch_name, branch_short_name)
    """
    enrollments = []

    if branch_code:
        branches_to_process = {branch_code: BRANCHES[branch_code]}
    else:
        branches_to_process = BRANCHES

    for code, info in branches_to_process.items():
        for roll in range(info['start_roll'], info['end_roll'] + 1):
            enrollment = f"{info['prefix']}{roll:03d}"
            enrollments.append((enrollment, info['name'], info['short_name']))

    return enrollments


def get_branch_info(enrollment_number):
    """
    Extract branch information from an enrollment number.

    Args:
        enrollment_number: e.g., 'BTAD24O1001'

    Returns:
        Dict with branch info, or None if not recognized.
    """
    for code, info in BRANCHES.items():
        if enrollment_number.startswith(info['prefix']):
            return info
    return None


if __name__ == "__main__":
    print("=" * 60)
    print("Enrollment Number Generator")
    print("=" * 60)

    all_enrollments = generate_enrollment_numbers()

    print(f"\nTotal students: {len(all_enrollments)}")
    print(f"Semester: {SEMESTER}")
    print()

    for code, info in BRANCHES.items():
        branch_enrollments = generate_enrollment_numbers(code)
        print(f"  {info['name']} ({code}):")
        print(f"    Range: {branch_enrollments[0][0]} -> {branch_enrollments[-1][0]}")
        print(f"    Count: {len(branch_enrollments)}")
    print()

    # Show first and last 3
    print("First 3:", [e[0] for e in all_enrollments[:3]])
    print("Last 3: ", [e[0] for e in all_enrollments[-3:]])
