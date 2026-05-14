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
            res = self.session.get(f"{self.base_url}/login/index.php")
            soup = BeautifulSoup(res.text, 'html.parser')
            token = soup.find('input', {'name': 'logintoken'})['value']
            
            data = {'username': user, 'password': pw, 'logintoken': token}
            post_res = self.session.post(f"{self.base_url}/login/index.php", data=data)
            return "login/logout.php" in post_res.text
        except Exception as e:
            print(f"Login Error: {e}")
            return False

    def get_courses(self):
        res = self.session.get(f"{self.base_url}/my/")
        soup = BeautifulSoup(res.text, 'html.parser')
        courses = []
        # مواءمة الكود مع تصميم مودل لجامعة السودان
        for a in soup.select('.coursename a') or soup.select('h4.multiline a'):
            courses.append({
                'name': a.get_text(strip=True),
                'id': a['href'].split('id=')[-1],
                'url': a['href']
            })
        return courses

    def get_videos(self, course_id):
        course_url = f"{self.base_url}/course/view.php?id={course_id}"
        res = self.session.get(course_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        videos = []
        for a in soup.find_all('a', href=True):
            if '.mp4' in a['href'] or 'video' in a['href']:
                videos.append({'title': a.get_text(strip=True), 'url': a['href']})
        return videos
