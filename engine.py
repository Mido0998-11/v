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
        try:
            res = self.session.get(f"{self.base_url}/grade/report/overview/index.php", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            grades_list = []
            table = soup.find('table', {'id': 'overview-grade'})
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        grades_list.append({
                            'course': cols[0].get_text(strip=True),
                            'grade': cols[1].get_text(strip=True)
                        })
            return grades_list
        except: return []

    def get_course_deep_content(self, course_id):
        """كشط متغلغل لكل المحتويات والملفات القديمة والبحث داخل الصفحات الفرعية عن الفيديوهات"""
        try:
            url = f"{self.base_url}/course/view.php?id={course_id}"
            res = self.session.get(url, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            content_list = []
            
            # فحص كل الروابط والأنشطة التعليمية في الصفحة (بما فيها المواد المرفوعة سابقاً)
            for a in soup.find_all('a', href=True):
                href = a['href']
                title = a.get_text(strip=True)
                if not title or len(title) < 2 or 'تخطي' in title: continue
                
                title = title.replace(' File', '').replace(' URL', '').replace(' Assignment', '').replace(' Page', '')
                
                # تصنيف المحتوى بدقة
                if 'mod/resource/view.php' in href:
                    content_list.append({'title': title, 'url': href, 'type': '📄 ملف / محاضرة'})
                elif 'mod/assign/view.php' in href:
                    content_list.append({'title': title, 'url': href, 'type': '📝 تكليف / شيت'})
                elif 'mod/folder/view.php' in href:
                    content_list.append({'title': title, 'url': href, 'type': '📁 مجلد ملفات كامل'})
                elif 'mod/url/view.php' in href:
                    content_list.append({'title': title, 'url': href, 'type': '🔗 رابط دراسي / فيديو خارجي'})
                elif 'mod/page/view.php' in href:
                    # الدخول التلقائي للصفحات الفرعية لصيد الفيديوهات المخبأة جواها!
                    try:
                        sub_res = self.session.get(href, timeout=5)
                        sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
                        found_video = False
                        for media in sub_soup.find_all(['video', 'source', 'iframe']):
                            v_url = media.get('src') or media.get('data-src')
                            if v_url:
                                content_list.append({'title': f"🎬 {title} (محاضرة مرئية)", 'url': v_url, 'type': '🎥 فيديو مباشر'})
                                found_video = True
                        if not found_video:
                            content_list.append({'title': title, 'url': href, 'type': '📄 صفحة محتوى'})
                    except:
                        content_list.append({'title': title, 'url': href, 'type': '📄 صفحة محتوى'})
                        
            # تنظيف الروابط المكررة
            seen = set()
            unique_content = []
            for item in content_list:
                if item['url'] not in seen:
                    seen.add(item['url'])
                    unique_content.append(item)
            return unique_content
        except: return []
