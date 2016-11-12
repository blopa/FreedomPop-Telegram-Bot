import json
import base64
import datetime
import requests
import sys


class FreedomPop:
    refreshToken = None
    token = None
    tokenExpireTimestamp = None
    accessToken = None

    _apiClient = sys.argv[3]
    _apiSecret = sys.argv[4]
    endPoint = "https://api.freedompop.com"

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def _updateToken(self, params):
        url = self.endPoint + "/auth/token"
        headers = dict(Authorization = "Basic %s" % base64.encodestring("%s:%s" % (self._apiClient, self._apiSecret)).replace("\n", ""))
        buffer = requests.post(url, params=params, headers=headers, data="").content
        print buffer
        data = json.loads(buffer)
        self.accessToken = data["access_token"]
        self.refreshToken = data["refresh_token"]
        self.tokenExpireTimestamp = datetime.datetime.now() + datetime.timedelta(seconds = data["expires_in"])

        return True

    def _getAccessToken(self):
        params = dict(username = self.username, password = self.password, grant_type = "password")
        return self._updateToken(params)

    def _refreshAccessToken(self):
        params = dict(refresh_token = self.refreshToken, grant_type = "refresh_token")
        return self._updateToken(params)

    def initToken(self):
        if self.refreshToken is None:
            return self._getAccessToken()
        elif self.tokenExpireTimestamp < datetime.datetime.now():
            return self._refreshAccessToken()
        return True

    def _getBasic(self, command):
        if not self.initToken():
            return {}
        params = dict(accessToken = self.accessToken)
        url = "%s/%s" % (self.endPoint, command)
        buffer = requests.get(url, params=params).content
        return json.loads(buffer)

    def getPhone(self):
        return self._getBasic("/phone/getnumbers/1")

    def getSMS(self, startDate, endDate, includeDeleted, includeRead):  # TODO
        if not self.initToken():
            return {}
        params = dict(accessToken=self.accessToken, startDate=startDate, endDate=endDate, includeDeleted=str(includeDeleted).lower(), includeRead=str(includeRead).lower())
        url = self.endPoint + '/phone/listsms/'
        req = requests.get(url, params=params)
        if req.status_code == 200:
            return json.loads(req.content)
        else:
            return False

    def getAllSMS(self):
        return self._getBasic("/phone/listsms")

    def getUsage(self):
        return self._getBasic("user/usage")

    def getInfo(self):
        return self._getBasic("user/info")

    def getPlan(self, planId = None):
        if planId is None:
            return self._getBasic("plan")
        else:
            return self._getBasic("plan/%s" % planId)

    def getPlans(self):
        return self._getBasic("plans")

    def getService(self, serviceId = None):
        if serviceId is None:
            return self._getBasic("service")
        else:
            return self._getBasic("service/%s" % serviceId)

    def getServices(self):
        return self._getBasic("services")

    def getContacts(self):
        return self._getBasic("contacts")

    def getFriends(self):
        return self._getBasic("friends")

    def sendSMS(self, to_numbers, message_body):  # TODO
        if not self.initToken():
            return {}
        url = self.endPoint + '/phone/sendsms/?accessToken=' + self.accessToken + '&to_numbers=' + to_numbers + '&message_body=' + message_body
        files = {'media_file': (None, 'none')}
        req = requests.post(url, files=files)
        if req.status_code == 200:
            return json.loads(req.content)
        else:
            return False

    def setAsRead(self, message_id):  # TODO
        if not self.initToken():
            return {}
        params = dict(accessToken=self.accessToken, messageIds=message_id)
        url = self.endPoint + '/phone/sms/read/'
        return requests.put(url, params=params)

    def printMyInfo(self):
        usage = self.getUsage()
        inMB = 1024 * 1024
        endTime = datetime.datetime.fromtimestamp(usage["endTime"] / 1000)
        delta = endTime - datetime.datetime.now()
        print "Data used: %0.2f%% (%0.2f MB of %0.2f MB) Time until quota reset: %d days %d hours (%s)" % (usage["percentUsed"] * 100, usage["planLimitUsed"] / inMB, usage["totalLimit"] / inMB, delta.days, delta.seconds / 3600, endTime )