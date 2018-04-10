#!/usr/bin/env python

"""
Report retriever module.

Grab HTML from the url provided.
"""

import random
import requests

from urllib.parse import quote as url_quote

from pyquery import PyQuery as pq

USER_AGENTS = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
               'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0',
               'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0',
               ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) '
                'Chrome/19.0.1084.46 Safari/536.5'),
               ('Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46'
                'Safari/536.5'), )

ENV = {
    'QED': {
        'safe_url': 'https://safe.thomson.com/safe-ui/fcc/login.fcc',
        'headers': {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        },
        'payload': (
            "action=LoginPassThrough&AcctMaintPurpose=&ProtectionLevel=SAFE5&"
            "TARGET=HTTPS%3A%2F%2Fsafe.thomson.com%2Flogin%2Fsso%2FSSOService%3Fapp%3Derrorgul_WLNQED&"
            "SMAUTHREASON=0&USER={user}&PASSWORD={password}&CAPTCHAANSWER="
        ),
        'error_gui_url': 'http://cobalttools.qed.int.westgroup.com/ErrorGUINext'
    }
}

QUERY_STRING = (
    "/initialResults.do?search=y&param=&qS=&a=&b=&c=&d=&e=&f=&g=&h=&i=&j=&x=&y=&z=&v="
    "&environs={env}&view=summary&site=all&start_time={start_time}&end_time={end_time}&submitForm=Submit"
)

TIME_FORMAT = '%Y-%m-%d %H:%M'

class ErrorReportRetriever(object):
    def __init__(self, env, user, password):
        self.env = env
        self.user = user
        self.password = password

    def get_html(self, start_time, end_time):
        session = requests.session()
        adapter = requests.adapters.HTTPAdapter(max_retries=20)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        env_data = ENV[self.env]
        headers = env_data['headers']
        headers['User-Agent'] = random.choice(USER_AGENTS)

        # SAFE ID
        payload = env_data['payload'].format(user=self.user, password=url_quote(self.password))
        session.post(env_data['safe_url'], headers=headers, data=payload, allow_redirects=True)

        # ErrorGUI request returns re-auth form expecting auto submit by JavaScript code
        error_gui_url = self._get_error_gui_url(start_time, end_time)
        auth_response = session.get(error_gui_url, headers={ 'User-Agent': random.choice(USER_AGENTS) }).text

        auth_html = pq(auth_response)
        url = auth_html('form').attr('action')
        uid = auth_html('input[name="uid"]').val()
        time = auth_html('input[name="time"]').val()
        digest = auth_html('input[name="digest"]').val()
        payload='uid={uid}&time={time}&digest={digest}'.format(uid=uid, time=url_quote(time), digest=digest)
        session.post(url, headers=headers, data=payload, allow_redirects=True)

        # get actual errors report
        report_html = session.get(error_gui_url, headers={ 'User-Agent': random.choice(USER_AGENTS) }).text

        session.close()
        
        return report_html

    def _get_error_gui_url(self, start_time, end_time):
        start = start_time.strftime(TIME_FORMAT)
        end = end_time.strftime(TIME_FORMAT)

        url = ENV[self.env]['error_gui_url'] + QUERY_STRING.format(env=self.env, start_time=url_quote(start), end_time=url_quote(end))

        return url
