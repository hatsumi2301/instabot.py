import requests
import random
import time
import datetime
import logging
import json

class InstaBot:
    """ Instagram bot v 0.03 """
    error_400 = 0
    media_by_tag = 0
    login_status = 0

    url = 'https://www.instagram.com/'
    url_tag = 'https://www.instagram.com/explore/tags/'
    url_likes = 'https://www.instagram.com/web/likes/%s/like/'
    url_comment = 'https://www.instagram.com/web/comments/%s/add/'
    url_login = 'https://www.instagram.com/accounts/login/ajax/'
    url_logout = 'https://www.instagram.com/accounts/logout/'

    user_agent = ("Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                  "KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36")
    accept_language = 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4'

    # If instagram ban you - query return 400 error.
    error_400 = 0
    # If you have 3 in row 400 error - look like you banned.
    error_400_to_ban = 3
    # If InstaBot think you have banned - going to sleep.
    ban_sleep_time = 2*60*60

    # All likes counter.
    like_conter = 0

    # Log setting.
    log_file_path = '/var/www/python/log/'
    log_file = 0

    def __init__(self, login, password,
                like_per_day=1000,
                more_than_likes=10,
                tag_list=['cat', 'car', 'dog'],
                max_like_for_one_tag = 5,
                log_mod = 0):
        self.like_per_day = like_per_day
        self.time_in_day = 24*60*60
        self.like_delay = self.time_in_day / self.like_per_day
        # Don't like if media have more than n likes.
        self.more_than_likes = more_than_likes

        # Auto mod seting:
        # Default list of tag.
        self.tag_list = tag_list
        # Get random tag, from tag_list, and like (1 to n) times.
        self.max_like_for_one_tag = max_like_for_one_tag
        # log_mod 0 to console, 1 to file
        self.log_mod = log_mod

        self.s = requests.Session()
        self.user_login = login
        self.user_password = password

        now_time = datetime.datetime.now()
        log_string = 'Insta Bot v0.03 start at %s:' %\
                     (now_time.strftime("%d.%m.%Y %H:%M"))
        self.write_log(log_string)
        self.login()

    def __del__ (self):
        self.logout()

    def login(self):
        log_string = 'Try to login by %s...' % (self.user_login)
        self.write_log(log_string)
        self.s.cookies.update ({'sessionid' : '', 'mid' : '', 'ig_pr' : '1',
                               'ig_vw' : '1920', 'csrftoken' : '',
                               's_network' : '', 'ds_user_id' : ''})
        self.login_post = {'username' : self.user_login,
                           'password' : self.user_password}
        self.s.headers.update ({'Accept-Encoding' : 'gzip, deflate',
                               'Accept-Language' : self.accept_language,
                               'Connection' : 'keep-alive',
                               'Content-Length' : '0',
                               'Host' : 'www.instagram.com',
                               'Origin' : 'https://www.instagram.com',
                               'Referer' : 'https://www.instagram.com/',
                               'User-Agent' : self.user_agent,
                               'X-Instagram-AJAX' : '1',
                               'X-Requested-With' : 'XMLHttpRequest'})
        r = self.s.get(self.url)
        self.s.headers.update({'X-CSRFToken' : r.cookies['csrftoken']})
        time.sleep(5 * random.random())
        login = self.s.post(self.url_login, data=self.login_post,
                            allow_redirects=True)
        self.s.headers.update({'X-CSRFToken' : login.cookies['csrftoken']})
        self.csrftoken = login.cookies['csrftoken']
        time.sleep(5 * random.random())

        if login.status_code == 200:
            r = self.s.get('https://www.instagram.com/')
            finder = r.text.find(self.user_login)
            if finder != -1:
                self.login_status = 1
                log_string = 'Look like login by %s succes!' % (self.user_login)
                self.write_log(log_string)
            else:
                self.login_status = 0
                self.write_log('Login error! Check your login data!')
        else:
            self.write_log('Login error! Connenction error!')

    def logout(self):
        self.login_status = 0
        now_time = datetime.datetime.now()
        log_string = 'Insta Bot logout at %s, like count %i.' \
                     % (now_time.strftime("%d.%m.%Y_%H:%M"), self.like_conter)
        self.write_log(log_string)

        try:
            logout_post = {'csrfmiddlewaretoken' : self.csrftoken}
            logout = self.s.post(self.url_likes, data=logout_post)
            self.write_log("Logout succes!")
        except:
            self.write_log("Logout error!")

    def get_media_id_by_tag (self, tag):
        log_string = "Get media id by tag: %s" % (tag)
        self.write_log(log_string)
        if self.login_status == 1:
            url_tag = '%s%s%s' % (self.url_tag, tag, '/')
            try:
                r = self.s.get(url_tag)
                text = r.text

                finder_text_start = ('<script type="text/javascript">'
                                     'window._sharedData = ')
                finder_text_start_len = len(finder_text_start)-1
                finder_text_end = ';</script>'

                all_data_start = text.find(finder_text_start)
                all_data_end = text.find(finder_text_end, all_data_start + 1)
                json_str = text[(all_data_start + finder_text_start_len + 1) \
                               : all_data_end]
                all_data = json.loads(json_str)

                self.media_by_tag = list(all_data['entry_data']['TagPage'][0]\
                                        ['tag']['media']['nodes'])
            except:
                self.media_by_tag = []
                self.write_log("Exept on get_media!")
                time.sleep(60)
        else:
            return 0

    def like_all_exist_media (self, media_size=-1):
        if self.media_by_tag != 0:
            i=0
            for d in self.media_by_tag:
                # Media count by this tag.
                if media_size > 0 or media_size < 0:
                    media_size -= 1
                    if (self.media_by_tag[i]['likes']['count'] < \
                        self.more_than_likes):
                        log_string = "Try to like media: %s" %\
                                     (self.media_by_tag[i]['id'])
                        self.write_log(log_string)
                        like = self.like(self.media_by_tag[i]['id'])
                        if like != 0:
                            if like.status_code == 200:
                                # Like, all ok!
                                self.error_400 = 0
                                self.like_conter += 1
                                log_string = "Liked: %s. Like #%i." %\
                                             (self.media_by_tag[i]['id'],
                                              self.like_conter)
                                self.write_log(log_string)
                            elif like.status_code == 400:
                                log_string = "Not liked: %i" \
                                              % (like.status_code)
                                self.write_log(log_string)
                                # Some error. If repeated - can be ban!
                                if self.error_400 >= self.error_400_to_ban:
                                    # Look like you banned!
                                    time.sleep(self.ban_sleep_time)
                                else:
                                    self.error_400 += 1
                            else:
                                log_string = "Not liked: %i" \
                                              % (like.status_code)
                                self.write_log(log_string)
                                # Some error.
                            i += 1
                            time.sleep(self.like_delay*0.9 +
                                       self.like_delay*0.2*random.random())
                    #else:
                        # This media have to many likes!
        else:
            self.write_log("No media to like!")

    def like(self, media_id):
        url_likes = self.url_likes % (media_id)
        try:
            like = self.s.post(url_likes)
        except:
            self.write_log("Exept on like!")
            like = 0
        return like

    def comment(self, comment):
        # To do
        return 0

    def follow(self, user_id):
        # To do
        return 0

    def unfollow(self, user_id):
        # To do
        return 0


    def auto_mod(self):
        while True:
            random.shuffle(self.tag_list)
            self.get_media_id_by_tag(random.choice(self.tag_list))
            self.like_all_exist_media(random.randint \
                                     (1, self.max_like_for_one_tag))

    def write_log(self, log_text):
        if self.log_mod == 0:
            print (log_text)
        elif self.log_mod == 1:
            # Create log_file if not exist.
            if self.log_file == 0:
                self.log_file = 1
                now_time = datetime.datetime.now()
                self.log_full_path = '%s%s_%s.log' % (self.log_file_path,
                                     self.user_login,
                                     now_time.strftime("%d.%m.%Y_%H:%M"))
                formatter = logging.Formatter('%(asctime)s - %(name)s '
                            '- %(message)s')
                self.logger = logging.getLogger(self.user_login)
                self.hdrl = logging.FileHandler(self.log_full_path, mode='w')
                self.hdrl.setFormatter(formatter)
                self.logger.setLevel(level=logging.INFO)
                self.logger.addHandler(self.hdrl)
            # Log to log file.
            self.logger.info(log_text)