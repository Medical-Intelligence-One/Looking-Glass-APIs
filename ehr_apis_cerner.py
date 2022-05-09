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


def Create_Check_Cerner_Authorization(authUrl, accessToken, expTimeForToken):
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
            return True, {
                'accessToken': accessToken,
                'expTimeForToken': expTimeForToken}
        else:
            return True, {
                'accessToken': accessToken,
                'expTimeForToken': expTimeForToken}
    except:
        return False, {
            'accessToken': None, 'expTimeForToken': 0}


def cernerPatient(patientId, filterArr):
    headers = authHeaders(filterArr['accessToken'])

    cernerPatientData = requests.get(filterArr['PatientReadUrl'] + str(patientId), headers=headers)
    cernerPatientData = cernerPatientData.json()
    getKeys = cernerPatientData.keys()
    isNameInData = 'name' in getKeys
    isDobInData = 'birthDate' in getKeys
    isMRNinData = 'identifier' in getKeys
    mrn = ""
    if isNameInData and isDobInData and isMRNinData:
        name = cernerPatientData['name'][0]['text']
        dob = cernerPatientData['birthDate']
        for i in cernerPatientData['identifier']:
            if i['system'] == 'urn:oid:2.16.840.1.113883.6.1000':
                mrn = i['value']
                break
        sample_var = {
            "Name": name,
            "MRN": mrn,
            "DOB": dob
        }
        sample_var = [sample_var]
        return sample_var
    else:
        return []


def cernerCondition(patientId, filterArr):
    conditionList = []
    headers = authHeaders(filterArr['accessToken'])
    cernerConditionData = requests.get(filterArr['ConditionReadUrl'] + str(patientId), headers=headers)
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


if __name__ == '__main__':
    response = cernerPatient('12724067', {'type': 'cerner', 'mi1ClientId': '1122334455', 'accessToken': 'eyJraWQiOiIyMDIyLTA1LTA0VDE3OjA2OjMxLjU0OC5lYyIsInR5cCI6IkpXVCIsImFsZyI6IkVTMjU2In0.eyJpc3MiOiJodHRwczpcL1wvYXV0aG9yaXphdGlvbi5jZXJuZXIuY29tXC8iLCJleHAiOjE2NTE4MzUwODcsImlhdCI6MTY1MTgzNDQ4NywianRpIjoiNWI0ZTk5NzgtOTcyZi00NzgxLWJlZWQtMTM5MDIwYTdiNjI0IiwidXJuOmNlcm5lcjphdXRob3JpemF0aW9uOmNsYWltczp2ZXJzaW9uOjEiOnsidmVyIjoiMS4wIiwicHJvZmlsZXMiOnsic21hcnQtdjEiOnsiYXpzIjoic3lzdGVtXC9PYnNlcnZhdGlvbi5yZWFkIHN5c3RlbVwvQ29uZGl0aW9uLnJlYWQgc3lzdGVtXC9QYXRpZW50LnJlYWQifX0sImNsaWVudCI6eyJuYW1lIjoiTUkxX0Vub2xhX0FQSSIsImlkIjoiNzEwYTIwMWQtZTM0YS00NTFiLTk0OGUtYWUxODQ3MjczYzY4In0sInRlbmFudCI6ImVjMjQ1OGYyLTFlMjQtNDFjOC1iNzFiLTBlNzAxYWY3NTgzZCJ9fQ.wdpp9zbRFCFkteS8sn-W8BPVlcIY_SQzaVpuwXs8ucLlrbpY_ZiOootsFpOI3trhE9c91r4-iCRP9ZNV11Hhlw', 'expTimeForToken': 1651835087, 'appClientId': 'ec2458f2-1e24-41c8-b71b-0e701af7583d', 'AuthUrl': 'https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/', 'PatientReadUrl': 'https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Patient/', 'ConditionReadUrl': 'https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Condition/'})
    print(response)

    # conditionResponse = cernerCondition('p73077203', {'type': 'cerner', 'mi1ClientId': '1122334455', 'accessToken': 'eyJraWQiOiIyMDIyLTA0LTI4VDE2OjEzOjE0LjY0Mi5lYyIsInR5cCI6IkpXVCIsImFsZyI6IkVTMjU2In0.eyJpc3MiOiJodHRwczpcL1wvYXV0aG9yaXphdGlvbi5jZXJuZXIuY29tXC8iLCJleHAiOjE2NTEyODc1OTIsImlhdCI6MTY1MTI4Njk5MiwianRpIjoiZThmOGRkNDctMjM2Ni00MWZlLTg0MjctMzRhY2IwY2YwNTk1IiwidXJuOmNlcm5lcjphdXRob3JpemF0aW9uOmNsYWltczp2ZXJzaW9uOjEiOnsidmVyIjoiMS4wIiwicHJvZmlsZXMiOnsic21hcnQtdjEiOnsiYXpzIjoic3lzdGVtXC9PYnNlcnZhdGlvbi5yZWFkIHN5c3RlbVwvQ29uZGl0aW9uLnJlYWQgc3lzdGVtXC9QYXRpZW50LnJlYWQifX0sImNsaWVudCI6eyJuYW1lIjoiTUkxX0Vub2xhX0FQSSIsImlkIjoiNzEwYTIwMWQtZTM0YS00NTFiLTk0OGUtYWUxODQ3MjczYzY4In0sInRlbmFudCI6ImVjMjQ1OGYyLTFlMjQtNDFjOC1iNzFiLTBlNzAxYWY3NTgzZCJ9fQ.l-YGcy5btDfTluUO0e0r2pLHwoUpZnxbDkOtovcm5zUvYO-gFLuEs3QpkBLQ8uTVsdi-KWn3G8YfQVL2bzxYEg', 'expTimeForToken': 1651287592, 'appClientId': 'ec2458f2-1e24-41c8-b71b-0e701af7583d', 'AuthUrl': 'https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/', 'PatientReadUrl': 'https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Patient/', 'ConditionReadUrl': 'https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Condition/'})
    # print(conditionResponse)
