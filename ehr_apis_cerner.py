import json
import base64
from wsgiref import headers
import jwt
# from jwt import JWT, jwk_from_pem
import requests
import xmltodict
import calendar;
import time;
from requests.structures import CaseInsensitiveDict

with open('clientIds.json', 'r') as jsonFile:
    config = json.load(jsonFile)
    config = config['clientIds']

accessToken = ""
appID = "ec2458f2-1e24-41c8-b71b-0e701af7583d"
clientID = "710a201d-e34a-451b-948e-ae1847273c68"  # System account id
clientSecret = "8rvKOnkr7S4VPngJUt1uD_RfWRiehZ4U"  # System account secret key
expTimeForToken = 0


def setHeaders(clientSecret):
    headers = {
        'Authorization': 'Basic ' + clientSecret,
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
        # 'Content-Length': 61,
        # 'Connection': 'close'
    }
    return headers


def authHeaders():
    global accessToken
    authHeaders = {
        'Authorization': 'Bearer ' + accessToken,
        'Accept': 'application/fhir+json'
    }
    return authHeaders


def cernerAuth(authUrl):
    # instance = JWT()
    gmt = time.gmtime()
    currentEpochTime = calendar.timegm(gmt)
    try:
        global expTimeForToken
        if currentEpochTime > expTimeForToken:
            data = {
                'grant_type': 'client_credentials',
                'scope': 'system/Observation.read system/Condition.read system/Patient.read'
            }
            global clientID, clientSecret
            encodeClient = clientID + ":" + clientSecret
            clientSecret_bytes = encodeClient.encode("ascii")
            clientSecret_64 = base64.b64encode(clientSecret_bytes)
            encodedString = clientSecret_64.decode("ascii")
            head = setHeaders(encodedString)
            response = requests.post(authUrl + "protocols/oauth2/profiles/smart-v1/token", headers=head, data=data)
            response = response.json()
            print(response)
            global accessToken
            accessToken = response['access_token']
            decodedToken = jwt.decode(accessToken, options={"verify_signature": False})
            expTimeForToken = decodedToken['exp']
            return True
        else:
            return True
    except:
        return False


def getAccessTokenExpTime(checkAuthDict, mi1ClientId, authUrl, patientUrl, conditionUrl, authDict):
    global accessToken, expTimeForToken
    if not checkAuthDict:
        tempObj = {
            "type": "cerner",
            "mi1ClientId": mi1ClientId,
            "accessToken": accessToken,
            "expTimeForToken": expTimeForToken,
            "AuthUrl": authUrl,
            "PatientReadUrl": patientUrl,
            "ConditionReadUrl": conditionUrl
        }
        return tempObj
    # check if existing token and exptime is updated or not
    for i in authDict:
        gmt = time.gmtime()
        currentEpochTime = calendar.timegm(gmt)
        if i['type'] == 'cerner' and str(i['mi1ClientId']) == str(mi1ClientId):
            if i['expTimeForToken'] < currentEpochTime:
                i['expTimeForToken'] = expTimeForToken
                i['accessToken'] = accessToken
    return None


def cernerPatient(cernerId, patientId, authUrl, patientUrl):
    checkAuth = cernerAuth(authUrl)

    headers = authHeaders()
    if checkAuth:
        cernerPatientData = requests.get(patientUrl + str(patientId), headers=headers)
        cernerPatientData = cernerPatientData.json()
        getKeys = cernerPatientData.keys()
        isNameInData = 'name' in getKeys
        isDobInData = 'birthDate' in getKeys
        if isNameInData and isDobInData:
            name = cernerPatientData['name'][0]['text']
            dob = cernerPatientData['birthDate']
            sample_var = {
                "Name": name,
                "DOB": dob
            }
            sample_var = [sample_var]
            return sample_var
        else:
            return []
    else:
        return []


def cernerCondition(cernerId, patientId, authUrl, conditionUrl):
    checkAuth = cernerAuth(authUrl)
    if checkAuth:
        conditionList = []
        headers = authHeaders()
        cernerConditionData = requests.get(conditionUrl + str(patientId), headers=headers)
        cernerConditionData = cernerConditionData.json()
        getConditionKeys = cernerConditionData.keys()
        isCodeInData = 'code' in getConditionKeys
        if isCodeInData:
            try:
                for i in cernerConditionData['code']['coding']:
                    PatientCondition = i['display']
                    ConditionCode = i['code']
                    temp_obj = {
                        "Code": ConditionCode,
                        "Text": PatientCondition
                    }
                    conditionList.append(temp_obj)
            except:
                conditionList = []
        return conditionList
    else:
        return []


if __name__ == '__main__':
    response = cernerPatient('1122334455', '12724067', config[1]['AuthUrl'], config[1]['PatientReadUrl'])
    print(response)

    conditionResponse = cernerCondition('1122334455', 'p73077203', config[1]['AuthUrl'], config[1]['ConditionReadUrl'])
    print(conditionResponse)
