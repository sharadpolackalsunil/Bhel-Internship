"""
Generate SVG placeholder images for the portal gallery.
Run this once, then replace with actual screenshots.
"""
import os

IMAGE_DIR = os.path.join(os.path.dirname(__file__), 'images')
os.makedirs(IMAGE_DIR, exist_ok=True)

placeholders = [
    ("portal_1_home.svg", "IUMS Portal Homepage", "Student Login · Sign Up · Employee Login", "#1a365d"),
    ("portal_2_login.svg", "Student Login Page", "Username · Password · CAPTCHA Verification", "#742a2a"),
    ("portal_3_dashboard.svg", "Student Dashboard", "Announcements · Student Services", "#1a4731"),
    ("portal_4_sidebar.svg", "Student Services Sidebar", "Course Registration · Fees · Profile · Marks", "#44337a"),
    ("portal_5_profile.svg", "Student Profile", "Personal Information · Academic History", "#744210"),
]

for filename, title, subtitle, color in placeholders:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="576" viewBox="0 0 1024 576">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color};stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#0a0e1a;stop-opacity:1"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="576" fill="url(#bg)"/>
  <rect x="40" y="40" width="944" height="496" rx="12" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>
  <text x="512" y="260" text-anchor="middle" fill="white" font-family="Inter, sans-serif" font-size="28" font-weight="700">{title}</text>
  <text x="512" y="300" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-family="Inter, sans-serif" font-size="16">{subtitle}</text>
  <text x="512" y="360" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-family="Inter, sans-serif" font-size="13">Replace with actual screenshot: images/{filename.replace('.svg', '.png')}</text>
</svg>'''
    
    with open(os.path.join(IMAGE_DIR, filename), 'w') as f:
        f.write(svg)
    print(f"Created {filename}")

print("Done! Replace .svg files with actual .png screenshots.")
