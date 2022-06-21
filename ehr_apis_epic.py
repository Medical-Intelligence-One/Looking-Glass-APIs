import json
import jwt
import xmltodict
from bs4 import BeautifulSoup
import requests
from requests.structures import CaseInsensitiveDict
from ehr_apis_cerner import cernerPatient, cernerCondition, Create_Check_Cerner_Authorization
import calendar
import time
import datetime, base64

# Assigning global variables
authDict = []

errorMessage = {
    'error': 'Try again after some time'
}

# loading clientIds
with open('clientIds.json', 'r') as jsonFile:
    config = json.load(jsonFile)
    config = config['clientIds']


# Authorization for EPIC services
def Create_Check_Epic_Authorization(authUrl, appClientId, accessToken, expTimeForToken):
    # instance = JWT()
    gmt = time.gmtime()
    currentEpochTime = calendar.timegm(gmt)
    # Load a RSA key from a PEM file.
    with open('privatekey.pem', 'rb') as fh:
        signing_key = fh.read()
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
                accessToken = data['access_token']
                decodedToken = jwt.decode(accessToken, options={"verify_signature": False})
                expTimeForToken = decodedToken['exp']
                return True, {
                    'accessToken': accessToken,
                    'expTimeForToken': expTimeForToken}
            else:
                return False, {
                    'accessToken': None,
                    'expTimeForToken': 0}
        except:
            return False, {
                'accessToken': None,
                'expTimeForToken': 0}
    else:
        return True, {
            'accessToken': accessToken,
            'expTimeForToken': expTimeForToken}


# Checking and creating local dictionary
def checkAuthDict(mi1ClientId, filteredArr):
    # get current time in epoch format
    gmt = time.gmtime()
    currentEpochTime = calendar.timegm(gmt)

    global authDict
    getFilterAuth = [x for x in authDict if x['mi1ClientId'] == mi1ClientId]

    if len(getFilterAuth) == 0:
        authDict.append({
            'type': filteredArr['type'],
            'mi1ClientId': mi1ClientId,
            'accessToken': '',
            'expTimeForToken': 0,
            'appClientId': filteredArr['appClientId'],
            'AuthUrl': filteredArr['AuthUrl'],
            'PatientReadUrl': filteredArr['PatientReadUrl'],
            'ConditionReadUrl': filteredArr['ConditionReadUrl']
        })

    for i in authDict:
        if i['type'] == 'epic' and str(i['mi1ClientId']) == str(mi1ClientId):
            if i['expTimeForToken'] < currentEpochTime:
                Is_SuccessAuth, getAuthData = Create_Check_Epic_Authorization(filteredArr['AuthUrl'],
                                                                              filteredArr['appClientId'],
                                                                              i['accessToken'],
                                                                              i['expTimeForToken'])
                if Is_SuccessAuth:
                    i['accessToken'] = getAuthData['accessToken']
                    i['expTimeForToken'] = getAuthData['expTimeForToken']
                    return i
                else:
                    return errorMessage
            return i
        if i['type'] == 'cerner' and str(i['mi1ClientId']) == str(mi1ClientId):
            if i['expTimeForToken'] < currentEpochTime:
                Is_SuccessAuth, getAuthData = Create_Check_Cerner_Authorization(filteredArr['AuthUrl'],
                                                                                i['accessToken'],
                                                                                i['expTimeForToken'])
                if Is_SuccessAuth:
                    i['accessToken'] = getAuthData['accessToken']
                    i['expTimeForToken'] = getAuthData['expTimeForToken']
                    return i
                else:
                    return errorMessage
            return i
    return errorMessage


def checkLocalDictAuth(mi1ClientId, patientId):
    getFilterId = [x for x in config if x['mi1ClientId'] == mi1ClientId]

    # check for if client exists in the database or not
    if getFilterId:
        getMessage = checkAuthDict(mi1ClientId, getFilterId[0])
        return getMessage

    errorForInvalidClientId = {
        'error': 'Invalid MI1ClientId',
    }
    return errorForInvalidClientId


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
    getMessage = checkLocalDictAuth(mi1ClientId, patientId)
    # print(authDict)
    getkeys = getMessage.keys()
    getType = 'type' in getkeys

    # if getMessage is epicMessage:
    if getType and getMessage['type'] == 'epic':
        patientData = requestData(getMessage['PatientReadUrl'] + patientId,
                                  getMessage['accessToken'])

        patientData = BeautifulSoup(patientData.content, 'html5lib')
        patientName = patientMRN = ""
        # Getting patient name from xml
        getName = patientData.find("name")
        try:
            for rowName in getName.find_all('text'):
                # Getting name
                patientName = rowName['value']

            # Getting patient mrn from xml
            getMRN = patientData.find_all("identifier")

            for rowMRN in getMRN:

                getText = rowMRN.find('text')
                if getText is not None and getText['value'] == "EPI":
                    mrnValue = rowMRN.find('value')

                    patientMRN = mrnValue['value']

            # Getting date of birth from xml
            getDOB = patientData.find('birthdate')
            patientDOB = getDOB['value']

            PatientDatainJson = {
                "Name": patientName,
                "MRN": patientMRN,
                "DOB": patientDOB,
            }
            print(authDict)
            tempList = [PatientDatainJson]
            return tempList
        except:
            return []

    # elif getMessage is cernerMessage:
    elif getType and getMessage['type'] == 'cerner':
        getCernerRes = cernerPatient(patientId, getMessage)
        print(authDict)
        return getCernerRes
    else:
        return getMessage


def getPatientCondition(patientId, category, clinical_status, mi1ClientId):
    global authDict
    getMessage = checkLocalDictAuth(mi1ClientId, patientId)
    getkeys = getMessage.keys()
    getType = 'type' in getkeys

    if getType and getMessage['type'] == 'epic':
        conditionJson = []

        conditionData = requestData(
            getMessage['ConditionReadUrl'] + patientId + "&category=" + category + "&clinical-status=" + clinical_status
            + '"', getMessage['accessToken'])

        convertedData = xmltodict.parse(conditionData.content)
        convertedData = json.dumps(convertedData)
        convertedData = json.loads(convertedData)

        try:
            for i in convertedData['Bundle']['entry']:

                # Filter code
                code = ""
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
                    print(authDict)
        except:
            conditionJson = []

        return conditionJson

    elif getType and getMessage['type'] == 'cerner':
        getCernerRes = cernerCondition(patientId, getMessage)
        print(authDict)
        return getCernerRes
    else:
        return getMessage


def createClinicalNote(response):
    getMessage = checkLocalDictAuth(response['MI1ClientID'], response['patientId'])
    getkeys = getMessage.keys()
    getType = 'type' in getkeys
    #Create Clinical Note for EPIC Document Reference
    if getType and getMessage['type'] == 'epic':
        
        with open('clinicalNoteTemplate.json', 'r') as template:
            getData = template.read()
            getData = getData.replace('#patientId#', response['patientId'])
            getData = getData.replace('#note_type_code#', response['note_type_code'])
            getData = getData.replace('#note_content#', response['note_content'])
            getData = json.loads(getData)
        headers = {
            "Authorization": "Bearer " + getMessage['accessToken'],
            'Prefer': 'return=representation'
        }
        

        responses = requests.post('https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/DocumentReference',
                                headers=headers, json=getData)
        
        convertedData = xmltodict.parse(responses.content)
        convertedData = json.dumps(convertedData)
        convertedData = json.loads(convertedData)
        getBinaryUrl = convertedData['DocumentReference']['content']['attachment']['url']['@value']
       
        if int(responses.status_code) == 201:
            returnData = [{
                'StatusCode': responses.status_code,
                'Clinical Note' : 'Created',
                'Location': getBinaryUrl
            }]
            return returnData
        else:
            return [{
                'StatusCode': responses.status_code,
            }]
    #Create Clinical Note for CERNER Document Reference
    if getType and getMessage['type'] == 'cerner':
        
        dateOfCreation = datetime.datetime.now()
        formattedDate = dateOfCreation.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]+ "Z"
        
        with open('cerner_clinical_note.json', 'r') as template:
            getData = template.read()
            getData = getData.replace('#patientId#', response['patientId'])
            getData = getData.replace('#PractitionerReference#', response['practitionerReference'])
            getData = getData.replace('#note_content#', response['note_content'])
            getData = getData.replace('#EncounterReference#', response['encounterReference'])
            getData = getData.replace("#creationDate#",formattedDate)
            getData = getData.replace("#startDate#",formattedDate)
            getData = getData.replace("#endDate#",formattedDate)
            getData = json.loads(getData)
        headers = {
            "Authorization": "Bearer " + getMessage['accessToken'],
            'Accept' : "application/fhir+json"
        }
        
        responses = requests.post('https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/DocumentReference',
                                headers=headers, json=getData)

        if int(responses.status_code) == 201:
            returnData = [{
                'StatusCode': responses.status_code,
                'Clinical Note' : 'Created',
                'Location': responses.headers['Location']
            }]
            return returnData
        else:
            return [{
                'StatusCode': responses.status_code,
            }]


# if __name__ == '__main__':
    # # epic
    # PatientInfo = getPatientData("eq081-VQEgP8drUUqCWzHfw3", '123456789')
    # print(PatientInfo)
    # #
    # # # epic
    # PatientConditionInfo = getPatientCondition("egqBHVfQlt4Bw3XGXoxVxHg3", "problem-list-item", "active", '123456789')
    # print(PatientConditionInfo)
    #
    # # # Cerner
    # response = getPatientData('12724067', '1122334455')
    # print(response)
    #
    # PatientConditionInfo = getPatientCondition("p73077203", "problem-list-item", "active", '1122334455')
    # print(PatientConditionInfo)

    # Clinical Note
    # response = createClinicalNote('123456789', "eXbMln3hu0PfFrpv2HgVHyg3", "11488-4", "abcd")
    # print(response)

    # Clinical Note read
    # response = readClinicalNote('123456789', 'eXbMln3hu0PfFrpv2HgVHyg3', 'eYuxo145oFk8gq-gXLM8WiA3')
    # print(response)

    # Clinical Note read all
    # response = readAllClinicalNOte('123456789', 'eXbMln3hu0PfFrpv2HgVHyg3')
    # print(response)
