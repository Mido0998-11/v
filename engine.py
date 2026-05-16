import requests
from bs4 import BeautifulSoup

class SUSTEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.base_url = "https://el.sustech.edu"

    def login(self, user, pw):
        try:
            res = self.session.get(f"{self.base_url}/login/index.php", timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            token = soup.find('input', {'name': 'logintoken'})['value']
            
            data = {'username': user, 'password': pw, 'logintoken': token}
            post_res = self.session.post(f"{self.base_url}/login/index.php", data=data, timeout=10)
            return "login/logout.php" in post_res.text
        except:
            return False

    def get_profile_and_courses(self):
        """سحب اسم الطالب الرسمي وقائمة مواده من البروفايل مباشرة"""
        try:
            res = self.session.get(f"{self.base_url}/user/profile.php", timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 1. صيد اسم الطالب من عنوان الصفحة الرئيسي (Moodle يضعه في h1)
            student_name = "طالب SUST"
            name_tag = soup.find('h1') or soup.select_one('.page-header-headings h1')
            if name_tag:
                student_name = name_tag.get_text(strip=True)

            # 2. سحب المواد
            courses = []
            for a in soup.find_all('a', href=True):
                if 'course/view.php?id=' in a['href']:
                    name = a.get_text(strip=True)
                    course_id = a['href'].split('id=')[-1].split('&')[0]
                    if name and not name.isdigit() and len(name) > 3:
                        courses.append({'name': name, 'id': course_id})
            
            # تنظيف التكرار
            seen = set()
            unique_courses = []
            for c in courses:
                if c['id'] not in seen:
                    seen.add(c['id'])
                    unique_courses.append(c)
                    
            return {"name": student_name, "courses": unique_courses}
        except:
            return {"name": "طالب SUST", "courses": []}

    def get_videos(self, course_id):
        try:
            url = f"{self.base_url}/course/view.php?id={course_id}"
            res = self.session.get(url, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            videos = []
            for a in soup.find_all('a', href=True):
                if '.mp4' in a['href'] or 'video' in a['href']:
                    videos.append({'title': a.get_text(strip=True) or "محاضرة فيديو", 'url': a['href']})
            return videos
        except: return []
