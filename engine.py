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
            res = self.session.get(f"{self.base_url}/login/index.php", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            token = soup.find('input', {'name': 'logintoken'})['value']
            
            data = {'username': user, 'password': pw, 'logintoken': token}
            post_res = self.session.post(f"{self.base_url}/login/index.php", data=data, timeout=15)
            return "login/logout.php" in post_res.text
        except: return False

    def get_profile_and_courses(self):
        """سحب اسم الطالب ومواده من البروفايل"""
        try:
            res = self.session.get(f"{self.base_url}/user/profile.php", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            student_name = "طالب جامعة السودان"
            name_tag = soup.find('h1') or soup.select_one('.page-header-headings h1')
            if name_tag: student_name = name_tag.get_text(strip=True)

            courses = []
            for a in soup.find_all('a', href=True):
                if 'course/view.php?id=' in a['href']:
                    name = a.get_text(strip=True)
                    course_id = a['href'].split('id=')[-1].split('&')[0]
                    if name and not name.isdigit() and len(name) > 3:
                        courses.append({'name': name, 'id': course_id})
            
            seen = set()
            unique_courses = []
            for c in courses:
                if c['id'] not in seen:
                    seen.add(c['id'])
                    unique_courses.append(c)
            return {"name": student_name, "courses": unique_courses}
        except: return {"name": "طالب SUST", "courses": []}

    def get_student_grades(self):
        """سحب كشف الدرجات الشامل لجميع المواد من سستم العلامات المركزي"""
        try:
            res = self.session.get(f"{self.base_url}/grade/report/overview/index.php", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            grades_list = []
            
            # البحث عن جدول الدرجات الشهير في مودل
            table = soup.find('table', {'id': 'overview-grade'})
            if table:
                for row in table.find_all('tr')[1:]: # تخطي الهيدر
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        course_name = cols[0].get_text(strip=True)
                        grade_val = cols[1].get_text(strip=True)
                        grades_list.append({'course': course_name, 'grade': grade_val})
            return grades_list
        except: return []

    def get_course_deep_content(self, course_id):
        """رادار صيد الفيديوهات المخفية والملفات والتكليفات"""
        try:
            url = f"{self.base_url}/course/view.php?id={course_id}"
            res = self.session.get(url, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            content_list = []
            
            # 1. صيد الفيديوهات الاحترافي (المخفية داخل وسوم الفيديو والمشغلات)
            for video in soup.find_all(['video', 'source']):
                v_url = video.get('src') or video.get('data-src')
                if v_url:
                    content_list.append({'title': '🎬 محاضرة مرئية (تشغيل فوري)', 'url': v_url, 'type': '🎥 فيديو مباشر'})
            
            for iframe in soup.find_all('iframe', src=True):
                if 'youtube' in iframe['src'] or 'vimeo' in iframe['src'] or 'video' in iframe['src']:
                    content_list.append({'title': '📺 فيديو محاضرات مضمن خارجي', 'url': iframe['src'], 'type': '🎥 فيديو مباشر'})

            # 2. كشط باقي الأنشطة الكلاسيكية (ملفات، واجبات، روابط)
            activities = soup.select('li.activity')
            for activity in activities:
                classes = activity.get('class', [])
                act_type = "unknown"
                for c in classes:
                    if 'modtype_' in c: act_type = c.replace('modtype_', '')
                
                a_tag = activity.find('a', href=True)
                if not a_tag: continue
                
                title = a_tag.get_text(strip=True).replace(' File', '').replace(' URL', '').replace(' Assignment', '')
                href = a_tag['href']
                
                if act_type == 'resource' or '.pdf' in href:
                    icon = "📄 ملف / محاضرة PDF"
                elif act_type == 'url':
                    # إذا كان الرابط الخارجي يؤدي لفيديو
                    icon = "🎥 فيديو / رابط خارجي" if any(x in href for x in ['youtube', 'mp4', 'vimeo', 'drive']) else "🔗 رابط دراسي"
                elif act_type == 'assign':
                    icon = "📝 تكليف / شيت مطلوب"
                elif act_type == 'quiz':
                    icon = "❓ إختبار قصير (Quiz)"
                else:
                    icon = "💡 محتوى مقرر"
                    
                content_list.append({'title': title, 'url': href, 'type': icon})
                
            return content_list
        except: return []
