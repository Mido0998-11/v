import requests
from bs4 import BeautifulSoup

class SUSTEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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

    def get_user_profile(self):
        """سحب معلومات الطالب الشخصية كاملة"""
        try:
            res = self.session.get(f"{self.base_url}/user/profile.php", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            name = soup.find('h1').get_text(strip=True) if soup.find('h1') else "طالب جامعة السودان"
            email = "غير مدرج"
            email_tag = soup.find('a', href=lambda href: href and "mailto:" in href)
            if email_tag: email = email_tag.get_text(strip=True)
            
            return {"name": name, "email": email}
        except:
            return {"name": "طالب SUST", "email": "غير معروف"}

    def get_courses(self):
        """سحب كافة المقررات (الحالية والقديمة) من الرابط الدقيق الذي أرسلته"""
        try:
            # الدخول مباشرة للرابط الصحيح للمقررات
            res = self.session.get(f"{self.base_url}/my/courses.php", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            courses = []
            
            # كشط الروابط التي توجه للمواد
            for a in soup.find_all('a', href=True):
                if 'course/view.php?id=' in a['href']:
                    name = a.get_text(strip=True)
                    course_id = a['href'].split('id=')[-1].split('&')[0]
                    # تصفية النصوص والتأكد من أنه اسم مقرر حقيقي
                    if name and not name.isdigit() and len(name) > 3 and 'تخطي' not in name:
                        courses.append({'name': name, 'id': course_id})
            
            # تنظيف التكرار
            seen = set()
            unique_courses = []
            for c in courses:
                if c['id'] not in seen:
                    seen.add(c['id'])
                    unique_courses.append(c)
            return unique_courses
        except: return []

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

    def get_calendar_events(self):
        """سحب مفكرة الأحداث والواجبات القادمة من تقويم المنصة"""
        try:
            res = self.session.get(f"{self.base_url}/calendar/view.php", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            events = []
            for event in soup.select('.event'):
                title = event.get('data-event-title')
                date = event.find('.row') or event.get_text(strip=True)[:30]
                if title: events.append({'title': title, 'date': date})
            return events[:5] # جلب أهم 5 أحداث قادمة
        except: return []

    def get_course_deep_content(self, course_id):
        """البحث المتعمق في المادة ودخول الصفحات الفرعية لصيد الفيديوهات"""
        try:
            url = f"{self.base_url}/course/view.php?id={course_id}"
            res = self.session.get(url, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            content_list = []
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                title = a.get_text(strip=True)
                if not title or len(title) < 2 or 'تخطي' in title: continue
                
                title = title.replace(' File', '').replace(' URL', '').replace(' Assignment', '').replace(' Page', '')
                
                if 'mod/resource/view.php' in href:
                    content_list.append({'title': title, 'url': href, 'type': '📄 ملف PDF / كتاب'})
                elif 'mod/assign/view.php' in href:
                    content_list.append({'title': title, 'url': href, 'type': '📝 تكليف / شيت مطلوب'})
                elif 'mod/folder/view.php' in href:
                    content_list.append({'title': title, 'url': href, 'type': '📁 مجلد ملفات'})
                elif 'mod/url/view.php' in href:
                    content_list.append({'title': title, 'url': href, 'type': '🔗 رابط / فيديو خارجي'})
                elif 'mod/page/view.php' in href:
                    # الغوص داخل الصفحات الفرعية إذا كان الفيديو مخبأ بالداخل
                    try:
                        sub_res = self.session.get(href, timeout=5)
                        sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
                        for media in sub_soup.find_all(['video', 'source', 'iframe']):
                            v_url = media.get('src') or media.get('data-src')
                            if v_url:
                                content_list.append({'title': f"🎬 {title} (محاضرة مرئية)", 'url': v_url, 'type': '🎥 فيديو مباشر'})
                    except: pass
            
            # إزالة التكرار
            seen = set()
            return [x for x in content_list if not (x['url'] in seen or seen.add(x['url']))]
        except: return []
