import requests
import json
import urllib3

from base64 import b64encode
from datetime import datetime
from time import sleep

class ZoomEyeClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False

        self.base_url = 'https://www.zoomeye.ai'

        self.session.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )

    def login(self, encrypted_password):
        '''
        Complete ZoomEye login flow
        Returns True if successful, False otherwise
        '''
        try:
            print('Step 1: Getting initial CSRF token...')

            resp1 = self.session.get(f'{self.base_url}/cas/api/user/userInfo')
            if 304 != resp1.status_code != 200:
                print(f'Failed to get CSRF token. Status: {resp1.status_code}')
                return False

            csrf_token = self.session.cookies.get('_csrf')

            if not csrf_token:
                print('CSRF token not found in cookies')
                return False

            print(f'Got CSRF token: {csrf_token}')

            print('Step 2: Getting SSO CSRF tokens...')

            resp2 = self.session.get(f'{self.base_url}/cas/api/index')
            if 304 != resp2.status_code != 200:
                print(f'Failed to get SSO CSRF tokens. Status: {resp2.status_code}')
                return False

            sso_csrf = self.session.cookies.get('ssoCsrfToken')
            replace_sso_csrf = self.session.cookies.get('replaceSsoCsrfToken')

            if not sso_csrf or not replace_sso_csrf:
                print('SSO CSRF tokens not found')
                return False

            print(f'Got SSO tokens: {sso_csrf}, {replace_sso_csrf}')

            print('Step 3: Attempting login...')
            login_data = encrypted_password

            resp3 = self.session.post(
                f'{self.base_url}/cas/api/cas/login',
                headers={'encode-X': 'change_it'},
                data=login_data,
            )

            if resp3.status_code == 201:
                print('Login successful!')

                if self.session.cookies.get('sessionid'):
                    print('Session established')
                    return True

                else:
                    print('No session ID found after login')
                    return False
            else:
                print(
                    f'Login failed. Status: {resp3.status_code}',
                    f'Response: {resp3.text}',
                    sep='\n',
                )
                return False

        except Exception as e:
            print(f'Error during login: {e}')
            return False

    def search(self, query, jwt):
        if not self.session.cookies.get('sessionid'):
            print('Not authenticated. Please login first.')
            return None

        search_url = f'{self.base_url}/api/search'
        total_url = f'{self.base_url}/api/search_total'
        headers = {'Cube-Authorization': jwt}

        b64query = b64encode(query.encode('ascii'))
        total = self.session.get(
            total_url, headers=headers, params={'q': b64query}
        ).json()['total']

        ips = 'host, port, banner\n'

        for i in range(1, (total + 50 - 1) // 50):
            if i > 5:
                break

            params = {
                'q': b64query,
                'page': str(i),
                'pageSize': 50,
            }

            response = self.session.get(search_url, headers=headers, params=params)

            if response.status_code == 200:
                matches = response.json()['matches']

                for j in matches:
                    banner = j['banner'].strip().partition('\n')[0]
                    ips += f"{j['ip']}, {j['portinfo']['port']}, {banner if banner else 'NoBannerSorry'}\n"

            else:
                print(f'Something went wrong. Status: {response.status_code}')

        return ips


if __name__ == '__main__':
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    client = ZoomEyeClient()
    encrypted_password = '"change_it"' # double quotes are IMPORTANT here!
    auth_token = 'change_it'

    if client.login(encrypted_password):
        print("I'm ready to search", '', '---!!!---', sep='\n')

        query = input('Your query: ')

        ips = client.search(query, auth_token)
        with open(f'{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv', 'w') as f:
            f.write(ips)

    else:
        print('Login failed')
