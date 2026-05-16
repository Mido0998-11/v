import requests
from bs4 import BeautifulSoup

class SUSTDownloaderEngine:
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

    def extract_real_video(self, moodle_url):
        """إذا كان الرابط يحتوي على ملف mp4 مباشر (مثل روابط pluginfile) يعيده فوراً"""
        if '.mp4' in moodle_url.lower():
            return moodle_url
            
        try:
            res = self.session.get(moodle_url, timeout=15)
            if '.mp4' in res.url.lower(): return res.url
            
            soup = BeautifulSoup(res.text, 'html.parser')
            video = soup.find(['video', 'source'])
            if video and video.get('src'): return video['src']
            
            # البحث عن الروابط البديلة داخل الصفحة
            for workaround in ['urlworkaround', 'resourceworkaround']:
                div = soup.find('div', class_=workaround)
                if div and div.find('a'): return div.find('a')['href']
                
            return moodle_url
        except: return moodle_url
