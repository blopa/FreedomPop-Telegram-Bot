import json
import base64
import datetime
import requests
import sys


class FreedomPop:
    refresh_token = None
    token_expire_timestamp = None
    access_token = None

    api_client = sys.argv[4]
    api_secret = sys.argv[5]
    api_app = sys.argv[6]
    end_point = "https://api.freedompop.com"

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def update_token(self, params):
        url = self.end_point + "/auth/token"
        headers = dict(Authorization="Basic %s" % base64.encodestring("%s:%s" % (self.api_client, self.api_secret)).replace("\n", ""))
        buffer = requests.post(url, params=params, headers=headers, data="").content
        # print buffer
        data = json.loads(buffer)
        try:
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            self.token_expire_timestamp = datetime.datetime.now() + datetime.timedelta(seconds=data["expires_in"])
            return True
        except Exception:
            if params['grant_type'] == 'refresh_token':
                self.refresh_token = None
            return False

    def get_access_token(self):
        params = dict(username=self.username, password=self.password, grant_type="password")
        return self.update_token(params)

    def refresh_access_token(self):
        params = dict(refreshToken=self.refresh_token, grant_type="refresh_token")
        return self.update_token(params)

    def initialize_token(self):
        if self.refresh_token is None:
            return self.get_access_token()
        elif self.token_expire_timestamp < datetime.datetime.now():
            return self.refresh_access_token()
        return True

    def get_basic(self, command):
        if not self.initialize_token():
            return {}
        params = dict(accessToken=self.access_token)
        url = "%s/%s" % (self.end_point, command)
        buffer = requests.get(url, params=params).content
        return json.loads(buffer)

    def get_phone_numbers(self, qtd):
        return self.get_basic("phone/getnumbers/" + qtd)

    def get_account_info(self):
        return self.get_basic("phone/account/info")

    def get_text_messages(self, start_date, end_date, include_deleted, include_read, include_outgoing):  # TODO
        if not self.initialize_token():
            return {}
        params = dict(accessToken=self.access_token, startDate=start_date, endDate=end_date, includeDeleted=str(include_deleted).lower(), includeRead=str(include_read).lower(), includeOutgoing=str(include_outgoing).lower())
        url = self.end_point + '/phone/listsms/'
        req = requests.get(url, params=params)
        if req.status_code == 200:
            return json.loads(req.content)
        else:
            return False

    def get_balance(self, version_number):
        if not self.initialize_token():
            return {}
        app_ver = self.api_app + str(version_number)
        print 'Trying app version %s' % app_ver
        params = dict(accessToken=self.access_token, appIdVersion=app_ver)
        url = self.end_point + '/phone/balance/'
        req = requests.get(url, params=params)
        if req.status_code == 200:
            data = json.loads(req.content)
            if data.__contains__('error') and version_number < 20:  # recursively until 20
                data = self.get_balance(version_number + 1)
            return data
        else:
            return False

    def get_plan_balance(self):
        details = {}
        data = self.get_balance(2)  # number of app_version to start
        if data:
            for dt in data:
                if dt['type'] == 'DATA_PLAN':
                    details['baseData'] = str(dt['baseData'])
                if dt['type'] == 'VOICE_PLAN':
                    details['price'] = str(dt['price'])
                    details['name'] = str(dt['name'])
                    details['description'] = str(dt['description'])
                    details['baseSMS'] = str(dt['baseSMS'])
                    details['remainingSMS'] = str(dt['balance']['remainingSMS'])
                    details['unlimitedVoice'] = str(dt['unlimitedVoice'])
                    details['unlimitedText'] = str(dt['unlimitedText'])
                    details['remainingData'] = str(dt['balance']['remainingData'])
                    details['dataOfferBonusEarned'] = str(dt['balance']['dataOfferBonusEarned'])
                    details['bonusSMS'] = str(dt['balance']['bonusSMS'])
                    details['bonusMinutes'] = str(dt['balance']['bonusMinutes'])
                    details['remainingMinutes'] = str(dt['balance']['remainingMinutes'])
                    details['dataFriendBonusEarned'] = str(dt['balance']['dataFriendBonusEarned'])

                    return details
            return False

    def get_text_messages_balance(self):
        details = {}
        data = self.get_plan_balance()
        if data:
            details['name'] = data['name']
            details['description'] = data['description']
            details['baseSMS'] = data['baseSMS']
            details['remainingSMS'] = data['remainingSMS']

            return details
        else:
            usage = self.get_usage()
            if not usage:
                return False
            info = self.get_account_info()
            if not info:
                return False
            sms = self.get_text_messages(usage['startTime'], '', False, True, True)  # get sms including outgoing
            if not sms:
                return False

            base = info['voiceplan']['baseSMS']
            count = 0
            for t in sms['messages']:
                if t['from'] == str(info['phoneNumber']):  # count sent sms
                    count += 1

            # details['phoneNumber'] = str(info['phoneNumber'])
            # details['startTime'] = str(usage['startTime'])
            details['name'] = str(info['voiceplan']['name'])
            details['description'] = str(info['voiceplan']['description'])
            details['baseSMS'] = str(info['voiceplan']['baseSMS'])
            details['remainingSMS'] = str(int(base) - count)

            return details

    def get_all_text_messages(self):
        return self.get_basic("/phone/listsms")

    def get_usage(self):
        return self.get_basic("user/usage")

    def get_info(self):
        return self.get_basic("user/info")

    def get_plan(self, plan_id=None):
        if plan_id is None:
            return self.get_basic("plan")
        else:
            return self.get_basic("plan/%s" % plan_id)

    def get_plans(self):
        return self.get_basic("plans")

    def get_service(self, service_id=None):
        if service_id is None:
            return self.get_basic("service")
        else:
            return self.get_basic("service/%s" % service_id)

    def get_services(self):
        return self.get_basic("services")

    def get_contacts(self):
        return self.get_basic("contacts")

    def get_friends(self):
        return self.get_basic("friends")

    def send_text_message(self, to_numbers, message_body):  # TODO
        if not self.initialize_token():
            return {}
        url = self.end_point + '/phone/sendsms/?accessToken=' + self.access_token + '&to_numbers=' + str(to_numbers) + '&message_body=' + message_body
        files = {'media_file': (None, 'none')}
        req = requests.post(url, files=files)
        if req.status_code == 200:
            return json.loads(req.content)
        else:
            return False

    def mark_as_read(self, message_id):  # TODO
        if not self.initialize_token():
            return {}
        params = dict(accessToken=self.access_token, messageIds=message_id)
        url = self.end_point + '/phone/sms/read/'
        return requests.put(url, params=params)

    def get_my_info(self):
        usage = self.get_usage()
        in_mb = 1024 * 1024
        end_time = datetime.datetime.fromtimestamp(usage["endTime"] / 1000)
        delta = end_time - datetime.datetime.now()
        return "Data used: %0.2f%% (%0.2f MB of %0.2f MB) Time until quota reset: %d days %d hours (%s)" % (usage["percentUsed"] * 100, usage["planLimitUsed"] / in_mb, usage["totalLimit"] / in_mb, delta.days, delta.seconds / 3600, end_time)
