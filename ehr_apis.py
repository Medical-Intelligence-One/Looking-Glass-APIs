import json

import jwt
import xmltodict
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta, timezone
from requests.structures import CaseInsensitiveDict
from jwt import (
    JWT,
    jwk_from_pem,
)
from jwt.utils import get_int_from_datetime
# ehr_apis.py
# Assigning global variables
accessToken = ""
patientName = patientMRN = patientDOB = ""
patientID = patientCategory = patientClinicalStatus = ""
listOfConditions = []
authDict = []

def authorization():
    instance = JWT()
    message = {
        # Client ID for non-production
        'iss': 'eac7c715-24c8-448a-9605-8b7226f468c0',
        'sub': 'eac7c715-24c8-448a-9605-8b7226f468c0',
        'aud': 'https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token',
        'jti': 'f9eaafba-2e49-11ea-8880-5ce0c5aee679',
        'iat': get_int_from_datetime(datetime.now(timezone.utc)),
        'exp': get_int_from_datetime(datetime.now(timezone.utc) + timedelta(minutes=5)),
    }

    # Load a RSA key from a PEM file.
    with open('privatekey.pem', 'rb') as fh:
        signing_key = jwk_from_pem(fh.read())

    compact_jws = instance.encode(message, signing_key, alg='RS384')
    # print(compact_jws)

    headers = CaseInsensitiveDict()
    headers['Content-Type'] = 'application/x-www-form-urlencoded'

    data = {
        'grant_type': 'client_credentials',
        'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
        'client_assertion': compact_jws
    }

    x = requests.post('https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token', headers=headers, data=data)
    data = json.loads(x.text)
    getKeys = data.keys()
    getKeys = "error" in getKeys
    # print(json.loads(x.text))
    if not getKeys:
        global accessToken
        accessToken = data['access_token']


def checkAuthToken(mi1ClientId):
    check = False
    global authDict
    if authDict:
        for i in authDict:
            if i[0] == mi1ClientId:
                check = True
                # print(i)
                currentEpochTime = get_int_from_datetime(datetime.now(timezone.utc))
                if i[2] < currentEpochTime:
                    authorization()
                    global accessToken
                    i[1] = accessToken
                    i[2] = currentEpochTime + 3600

    if not check:
        instance = JWT()
        # Load a RSA key from a PEM file.

        if accessToken == "":
            authorization()
        with open('privatekey.pem', 'rb') as fh:
            signing_key = jwk_from_pem(fh.read())
        try:
            decodedToken = instance.decode(accessToken, signing_key, do_verify=False)
            expTimeForToken = decodedToken['exp']
            currentEpochTime = get_int_from_datetime(datetime.now(timezone.utc))
            if currentEpochTime > expTimeForToken:
                authorization()
        except:
            authorization()
            decodedToken = instance.decode(accessToken, signing_key, do_verify=False)
            expTimeForToken = decodedToken['exp']

        tempArray = [mi1ClientId, accessToken, expTimeForToken]

        authDict.append(tempArray)
    # instance = JWT()
    # # Load a RSA key from a PEM file.
    # global accessToken
    # if accessToken == "":
    #     authorization()
    # with open('privatekey.pem', 'rb') as fh:
    #     signing_key = jwk_from_pem(fh.read())
    # decodedToken = instance.decode(accessToken, signing_key, do_verify=False)
    # currentEpochTime = get_int_from_datetime(datetime.now(timezone.utc))
    # tokenExpiryEpochTime = decodedToken['exp']
    # if currentEpochTime > tokenExpiryEpochTime:
    #     authorization()


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
    checkAuthToken(mi1ClientId)
    patientData = requestData("https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Patient/" + patientId,
                              accessToken)
    soup = BeautifulSoup(patientData.content, 'html5lib')

    # Getting patient name from xml
    getName = soup.find("name")
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
    return PatientDatainJson


def getPatientCondition(patientId, category, clinical_status, mi1ClientId):
    checkAuthToken(mi1ClientId)
    conditionJson = []
    global accessToken
    conditionData = requestData(
        "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Condition?patient=" + patientId + "&category=" + category + "&clinical-status=" + clinical_status + '"',
        accessToken)
    # soup = BeautifulSoup(conditionData.content, 'html5lib')
    convertedData = xmltodict.parse(conditionData.content)
    convertedData = json.dumps(convertedData)
    convertedData = json.loads(convertedData)
    try:
        # print(convertedData['Bundle']['entry'][0]['resource']['Condition']['code']['coding'][1]['code']['@value'],
        #       convertedData['Bundle']['entry'][0]['resource']['Condition']['code']['text']['@value'])

        text = convertedData['Bundle']['entry'][0]['resource']['Condition']['code']['text']['@value']
        code = convertedData['Bundle']['entry'][0]['resource']['Condition']['code']['coding'][1]['code']['@value']
        sampleVar = {
            "Code": code,
            "Text": text
        }
        conditionJson.append(sampleVar)
    except:
        conditionJson = []


    return conditionJson


# if __name__ == '__main__':
    # PatientInfo = getPatientData("eq081-VQEgP8drUUqCWzHfw3", "123456789")
    # print(PatientInfo)

    # PatientConditionInfo = getPatientCondition("eq081-VQEgP8drUUqCWzHfw3", "problem-list-item", "active", '123456789')
    # print(PatientConditionInfo)
