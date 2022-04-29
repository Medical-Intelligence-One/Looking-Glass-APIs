import json
import base64
import jwt
import requests
import calendar
import time

with open('clientIds.json', 'r') as jsonFile:
    config = json.load(jsonFile)
    config = config['clientIds']


def setHeaders(clientSecret):
    headers = {
        'Authorization': 'Basic ' + clientSecret,
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    return headers


def authHeaders(accessToken):
    authHeaders = {
        'Authorization': 'Bearer ' + accessToken,
        'Accept': 'application/fhir+json'
    }
    return authHeaders


def cernerAuth(accessToken, expTimeForToken, authUrl):
    gmt = time.gmtime()
    currentEpochTime = calendar.timegm(gmt)

    clientID = "710a201d-e34a-451b-948e-ae1847273c68"  # System account id
    clientSecret = "8rvKOnkr7S4VPngJUt1uD_RfWRiehZ4U"  # System account secret key

    try:
        if currentEpochTime > expTimeForToken:
            data = {
                'grant_type': 'client_credentials',
                'scope': 'system/Observation.read system/Condition.read system/Patient.read'
            }
            encodeClient = clientID + ":" + clientSecret
            clientSecret_bytes = encodeClient.encode("ascii")
            clientSecret_64 = base64.b64encode(clientSecret_bytes)
            encodedString = clientSecret_64.decode("ascii")
            head = setHeaders(encodedString)
            response = requests.post(authUrl + "protocols/oauth2/profiles/smart-v1/token", headers=head, data=data)
            response = response.json()
            # print(response)
            accessToken = response['access_token']
            decodedToken = jwt.decode(accessToken, options={"verify_signature": False})
            expTimeForToken = decodedToken['exp']
            return True, [{
                'accessToken': accessToken,
                'expTimeForToken': expTimeForToken}]
        else:
            return True, [{
                'accessToken': accessToken,
                'expTimeForToken': expTimeForToken}]
    except:
        return False, [None, None]


def cernerAuthDict(cernerId, filterArr, authDict):
    # get current time in epoch format
    gmt = time.gmtime()
    currentEpochTime = calendar.timegm(gmt)
    # check if our local dictionary has expired token
    if filterArr['expTimeForToken'] < currentEpochTime:
        Is_SuccessAuth, getAuthData = cernerAuth(filterArr['accessToken'], filterArr['expTimeForToken'],
                                                 filterArr['AuthUrl'])
        if Is_SuccessAuth:
            # Filter authDict to check for Id
            getFilterId = [x for x in authDict if x['mi1ClientId'] == cernerId]
            # for loop
            if getFilterId:
                # updating in the local dictionary
                getFilterId[0]['accessToken'] = getAuthData[0]['accessToken']
                getFilterId[0]['expTimeForToken'] = getAuthData[0]['expTimeForToken']
                return Is_SuccessAuth, getFilterId[0], authDict
            else:
                # updating the local array that is to be added
                filterArr['accessToken'] = getAuthData[0]['accessToken']
                filterArr['expTimeForToken'] = getAuthData[0]['expTimeForToken']
                authDict.append(filterArr)
                return Is_SuccessAuth, filterArr, authDict
        else:
            return False, filterArr, authDict
    return True, filterArr, authDict


def cernerPatient(mi1ClientId, patientId, filterArr, authDict):
    # first var return is to check Authorisation
    # second var return our filtered array containing cerner data
    # third var our local authDict
    checkAuth, updatedfilterArr, updatedAuthDict = cernerAuthDict(mi1ClientId, filterArr, authDict)

    headers = authHeaders(updatedfilterArr['accessToken'])
    if checkAuth:
        cernerPatientData = requests.get(updatedfilterArr['PatientReadUrl'] + str(patientId), headers=headers)
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
            return sample_var, updatedAuthDict
        else:
            return [], updatedAuthDict
    else:
        return [], updatedAuthDict


def cernerCondition(cernerId, patientId, filterArr, authDict):
    # first var return is to check Authorisation
    # second var return our filter array containing cerner data
    # third var our local authDict
    checkAuth, updatedfilterArr, updatedAuthDict = cernerAuthDict(cernerId, filterArr, authDict)

    if checkAuth:
        conditionList = []
        headers = authHeaders(updatedfilterArr['accessToken'])
        cernerConditionData = requests.get(updatedfilterArr['ConditionReadUrl'] + str(patientId), headers=headers)
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
        return conditionList, updatedAuthDict
    else:
        return [], updatedAuthDict


# if __name__ == '__main__':
#     response = cernerPatient('1122334455', '12724067', config[1]['AuthUrl'], config[1]['PatientReadUrl'])
#     print(response)

#     conditionResponse = cernerCondition('1122334455', 'p73077203', config[1]['AuthUrl'], config[1]['ConditionReadUrl'])
#     print(conditionResponse)
