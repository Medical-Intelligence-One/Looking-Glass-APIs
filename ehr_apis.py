import json

import jwt
import xmltodict
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta, timezone
from requests.structures import CaseInsensitiveDict
from ehr_apis_cerner import cernerPatient, cernerCondition, getAccessTokenExpTime
# from jwt import (
#     JWT,
#     jwk_from_pem,
# )
# from jwt.utils import get_int_from_datetime
import calendar
import time

# ehr_apis.py
# Assigning global variables
accessToken = ""
patientName = patientMRN = patientDOB = ""
patientID = patientCategory = patientClinicalStatus = ""
listOfConditions = []
authDict = []
authUrl = patientUrl = conditionUrl = appClientId = ""
isCernerinDict = False
# api key, url,
expTimeForToken = 0
errorMessage = {
    'error': 'Try again after some time'
}
epicMessage = {
    'success': "Called Epic"
}
cernerMessage = {
    'success': "Called Cerner"
}

with open('clientIds.json', 'r') as jsonFile:
    config = json.load(jsonFile)
    config = config['clientIds']


def authorization():
    # instance = JWT()
    gmt = time.gmtime()
    currentEpochTime = calendar.timegm(gmt)
    # Load a RSA key from a PEM file.
    with open('privatekey.pem', 'rb') as fh:
        signing_key = fh.read()
    global expTimeForToken
    # Check if token is expired or not
    # currentEpochTime = get_int_from_datetime(datetime.now(timezone.utc))
    if currentEpochTime > expTimeForToken:
        message = {
            # Client ID for non-production
            'iss': appClientId,
            'sub': appClientId,
            'aud': authUrl,
            'jti': 'f9eaafba-2e49-11ea-8880-5ce0c5aee679',
            'iat': currentEpochTime,
            'exp': currentEpochTime + 300,
        }

        compact_jws = jwt.encode(message, signing_key, algorithm='RS384')
        # print(compact_jws)

        headers = CaseInsensitiveDict()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        data = {
            'grant_type': 'client_credentials',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': compact_jws
        }
        try:
            x = requests.post(authUrl, headers=headers, data=data)
            data = json.loads(x.text)
            getKeys = data.keys()
            getKeys = "error" in getKeys
            print(json.loads(x.text))
            if not getKeys:
                global accessToken
                accessToken = data['access_token']
                decodedToken = jwt.decode(accessToken, signing_key, options={"verify_signature": False})
                expTimeForToken = decodedToken['exp']
                return True
            else:
                return False
        except:
            return False
    else:
        return True


def checkAuthDict(mi1ClientId, type):
    # currentEpochTime = get_int_from_datetime(datetime.now(timezone.utc))
    gmt = time.gmtime()
    currentEpochTime = calendar.timegm(gmt)
    global errorMessage, isCernerinDict, authDict
    isCernerinDict = False
    errorMessage = {
        'error': "Try again after sometime"
    }
    if len(authDict) > 0:
        # check if data exists in local data
        for i in authDict:
            if i['type'] == 'epic' and str(i['mi1ClientId']) == str(mi1ClientId):
                if i['expTimeForToken'] < currentEpochTime:
                    checkForSuccessAuth = authorization()
                    if checkForSuccessAuth:
                        i['accessToken'] = accessToken
                        i['expTimeForToken']=expTimeForToken
                        return epicMessage
                    else:
                        return errorMessage
                return epicMessage
            if i['type'] == 'cerner':
                authDict_mi1ClientId = i['mi1ClientId']
                if str(authDict_mi1ClientId) == str(mi1ClientId):
                    isCernerinDict = True
                    return cernerMessage

    # check  for cerner type
    if type == "cerner":
        isCernerinDict = False

        return cernerMessage

    # check for epic type
    if type == "epic":
        if expTimeForToken < currentEpochTime:
            checkForSuccessAuth = authorization()
            if checkForSuccessAuth:
                tempJson = {
                    "type": type,
                    "mi1ClientId": mi1ClientId,
                    "accessToken": accessToken,
                    "expTimeForToken": expTimeForToken,
                    "AuthUrl": authUrl,
                    "PatientReadUrl": patientUrl,
                    "ConditionReadUrl": conditionUrl
                }
                authDict.append(tempJson)
                return epicMessage
            else:
                return errorMessage
        else:
            tempJson = {
                "type": type,
                "mi1ClientId": mi1ClientId,
                "accessToken": accessToken,
                "expTimeForToken": expTimeForToken,
                "AuthUrl": authUrl,
                "PatientReadUrl": patientUrl,
                "ConditionUrl": conditionUrl
            }
            authDict.append(tempJson)
            return epicMessage


def checkAuthToken(mi1ClientId, patientId):
    global authDict, accessToken, expTimeForToken, appClientId
    getFilterId = [x for x in config if x['mi1ClientId'] == mi1ClientId]
    if getFilterId:
        global authUrl, patientUrl, conditionUrl
        authUrl = getFilterId[0]['AuthUrl']
        patientUrl = getFilterId[0]['PatientReadUrl']
        conditionUrl = getFilterId[0]['ConditionReadUrl']
        appClientId = getFilterId[0]['appClientId']
        getMessage = checkAuthDict(mi1ClientId, getFilterId[0]['type'])
        return getMessage
    # for i in config:
    #     if str(i['mi1ClientId']) == str(mi1ClientId):
    #         global authUrl, patientUrl, conditionUrl
    #         authUrl = i['AuthUrl']
    #         patientUrl = i['PatientReadUrl']
    #         conditionUrl = i['ConditionReadUrl']
    #         appClientId = i['appClientId']
    #         getMessage = checkAuthDict(mi1ClientId, i['type'])
    #         return getMessage
    global errorMessage
    errorMessage = {
        'error': "Invalid MI1 Client ID"
    }
    return errorMessage


def setHeaders(accessToken):
    headers = {
        'Authorization': 'Bearer ' + accessToken
    }
    return headers


def requestData(url, accessToken):
    headers = setHeaders(accessToken)
    data = requests.get(url, headers=headers)
    return data


def getPatientData(patientId, mi1ClientId):
    global authUrl, patientUrl, conditionUrl, appClientId
    authUrl = patientUrl = conditionUrl = appClientId = ""
    getMessage = checkAuthToken(mi1ClientId, patientId)
    # print(authDict)
    if getMessage is epicMessage:
        patientData = requestData(patientUrl + patientId,
                                  accessToken)

        soup = BeautifulSoup(patientData.content, 'html5lib')

        # Getting patient name from xml
        getName = soup.find("name")
        try:
            for rowName in getName.find_all('text'):
                # Getting name
                global patientName
                patientName = rowName['value']
                # print("Name: ", rowName['value'])

            # Getting patient mrn from xml
            getMRN = soup.find_all("identifier")

            for rowMRN in getMRN:

                getText = rowMRN.find('text')
                if getText['value'] == "EPI":
                    mrnValue = rowMRN.find('value')
                    global patientMRN
                    patientMRN = mrnValue['value']
                    # print("MRN: ", mrnValue['value'])

            # Getting date of birth from xml
            getDOB = soup.find('birthdate')
            global patientDOB
            patientDOB = getDOB['value']
            # print("DOB: ", getDOB['value'])
            PatientDatainJson = {
                "Name": patientName,
                "MRN": patientMRN,
                "DOB": patientDOB,
            }
            tempList = [PatientDatainJson]
            return tempList
        except:
            return []
    elif getMessage is cernerMessage:
        getCernerRes = cernerPatient(mi1ClientId, patientId, authUrl, patientUrl)
        getData = getAccessTokenExpTime(isCernerinDict, mi1ClientId, authUrl, patientUrl, conditionUrl, authDict)
        if getData is not None:
            authDict.append(getData)
        return getCernerRes
    else:
        return errorMessage


def getPatientCondition(patientId, category, clinical_status, mi1ClientId):
    global authUrl, patientUrl, conditionUrl, appClientId
    authUrl = patientUrl = conditionUrl = appClientId = ""
    getMessage = checkAuthToken(mi1ClientId, patientId)
    print(authDict)
    if getMessage is epicMessage:
        conditionJson = []
        global accessToken
        conditionData = requestData(
            conditionUrl + patientId + "&category=" + category + "&clinical-status=" + clinical_status + '"',
            accessToken)

        convertedData = xmltodict.parse(conditionData.content)
        convertedData = json.dumps(convertedData)
        convertedData = json.loads(convertedData)

        try:
            for i in convertedData['Bundle']['entry']:

                # Filter code
                getKeys = i['resource'].keys()
                checkConditionKey = "Condition" in getKeys
                if checkConditionKey:
                    for j in i['resource']['Condition']['code']['coding']:
                        if j['system']['@value'] == 'urn:oid:2.16.840.1.113883.6.96':
                            code = j['code']['@value']
                            # print(code)

                    # Get Text
                    text = i['resource']['Condition']['code']['text']['@value']
                    # print(text)
                    sampleVar = {
                        "Code": code,
                        "Text": text
                    }
                    conditionJson.append(sampleVar)

        except:
            conditionJson = []

        return conditionJson

    elif getMessage is cernerMessage:
        getCernerRes = cernerCondition(mi1ClientId, patientId, authUrl, conditionUrl)
        getData = getAccessTokenExpTime(isCernerinDict, mi1ClientId, authUrl, patientUrl, conditionUrl, authDict)
        if getData is not None:
            authDict.append(getData)
        return getCernerRes
    else:
        return errorMessage


if __name__ == '__main__':
    # epic
    PatientInfo = getPatientData("eq081-VQEgP8drUUqCWzHfw3", '123456789')
    print(PatientInfo)

    # epic
    PatientConditionInfo = getPatientCondition("egqBHVfQlt4Bw3XGXoxVxHg3", "problem-list-item", "active", '123456789')
    print(PatientConditionInfo)

    # Cerner
    # response = getPatientData('12724067','1122334455')
    # print(response)
    #
    # PatientConditionInfo = getPatientCondition("p73077203", "problem-list-item", "active", '1122334455')
    # print(PatientConditionInfo)
