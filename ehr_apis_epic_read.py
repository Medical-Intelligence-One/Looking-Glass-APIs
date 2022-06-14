import json

import requests
import xmltodict
from bs4 import BeautifulSoup

from ehr_apis_epic import checkLocalDictAuth, setHeaders

from ehr_apis_cerner import authHeaders
import inspect
import base64
paginationVariable = ''
fullURLList = []
PractitionerReference = []
ContentType = []
ContentUrl = []
returnData = []
creationDate = []
noteTitle = []
def BinaryClinicalNote(url, MI1ClientID, patientId):
    getMessage = checkLocalDictAuth(MI1ClientID, patientId)
    headers = setHeaders(getMessage['accessToken'])
    headersCerner = {
            
            'Authorization': headers['Authorization'],
            'Accept': 'application/json+fhir'
        }
    
    responses = requests.get(url,headers=headersCerner)
    convertedData = responses.content.decode('utf8')
    finalData = json.loads(convertedData)
    # jsonDecodedData = base64.b64decode(finalData['data'])
    # finalDecodedData = jsonDecodedData.decode("utf-8").replace('\n', '')
    return finalData['data']


def readClinicalNote(MI1ClientID, patientId, binaryId):
    try:
        lst = []

        getMessage = checkLocalDictAuth(MI1ClientID, patientId)
        headers = setHeaders(getMessage['accessToken'])

        responses = requests.get('https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Binary/' + binaryId,
                                 headers=headers)
        # Parsed HTML to json array
        # BinaryData = BeautifulSoup(responses.content, 'html5lib')
        # getFilter = BinaryData.find('div')
        # for i in getFilter.recursiveChildGenerator():
        #     if i.name == 'span':
        #         # print(i.text, len(i.text))
        #         if i.text and len(i.text) != 12 and len(i.text.strip()) != 0:
        #             lst.append(i.text)
        #
        # BinaryReadData = []
        # index = -1
        # for i in lst:
        #     if len(i.strip()) == len(i):
        #         index = index + 1
        #         BinaryReadData.append({
        #             'ProblemText': i,
        #             "Orders": []
        #         })
        #     else:
        #         BinaryReadData[index]['Orders'].append({
        #             'OrderText': i.strip(),
        #         })
        # # print(BinaryReadData)
        # return BinaryReadData
        return responses.content
    except:
        return []


def readAllClinicalNOte(MI1ClientID, patientId):
    returnData = []
    
    getMessage = checkLocalDictAuth(MI1ClientID, patientId)

    headers = setHeaders(getMessage['accessToken'])

    getkeys = getMessage.keys()
    getType = 'type' in getkeys
    if getType and getMessage['type'] == 'epic':
        binaryUrlList = []
        responses = requests.get(
            'https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/DocumentReference?patient='+patientId+'&_count=1&type=http://loinc.org|11488-4',
            headers=headers)
        convertedData = xmltodict.parse(responses.content)
        convertedData = json.dumps(convertedData)
        convertedData = json.loads(convertedData)
        for i in convertedData['Bundle']['entry']:
            getKeys = i['resource'].keys()
            checkDocumentReferenceKey = "DocumentReference" in getKeys
            
            if checkDocumentReferenceKey:
                fullURLListvar = i['fullUrl']['@value']
                PractitionerReferencevar = i['resource']['DocumentReference']['author']['reference']['@value']
                ContentTypevar = i['resource']['DocumentReference']['content']['attachment']['contentType']['@value']
                ContentUrlvar = i['resource']['DocumentReference']['content']['attachment']['url']['@value']
                creationDatevar = i['resource']['DocumentReference']['date']['@value']
                binaryURLId = ContentUrlvar.replace('Binary/','')
                # getting the data from binary read API
                responses = requests.get('https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Binary/'+binaryURLId,
                headers=headers)
                base64text = ''
                convertedData = BeautifulSoup(responses.content.decode('utf8'), 'html5lib')
                getFilter = convertedData.find('div')
                for j in getFilter.recursiveChildGenerator():
                    if j.name == 'span':
                        if len(j.text.strip()) != 0:
                            base64text = j.text
                recordData = {
                    "creationDate": creationDatevar,
                    "fullURLList": fullURLListvar,
                    "PractitionerReference": PractitionerReferencevar,
                    "ContentType": ContentTypevar,
                    "ContentUrl": ContentUrlvar,
                    "DecodedData": base64text
                }

                returnData.append(recordData)
        return returnData

    if getType and getMessage['type'] == 'cerner':
        
        headersCerner = {
            
            'Authorization': headers['Authorization'],
            'Accept': 'application/json+fhir'
        }
        responses = requests.get(
            'https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/DocumentReference?patient='+patientId+'&_count=1&type=https://fhir.cerner.com/ec2458f2-1e24-41c8-b71b-0e701af7583d/codeSet/72|20732501',
             headers=headersCerner)
        convertedData = responses.content.decode('utf8')

        finalData = json.loads(convertedData)

        paginationVariable = finalData['link'][1]['relation']
        for i in range(0,len(finalData['entry'])):

            fullURLListvar = finalData['entry'][i]['fullUrl']
            PractitionerReferencevar = finalData['entry'][i]['resource']['author'][0]['reference']
            ContentTypevar = finalData['entry'][i]['resource']['content'][0]['attachment']['contentType']
            ContentUrlvar = finalData['entry'][i]['resource']['content'][0]['attachment']['url']
            creationDatevar = finalData['entry'][i]['resource']['content'][0]['attachment']['creation']
            noteTitlevar = finalData['entry'][i]['resource']['content'][0]['attachment']['title']
            if ContentTypevar != 'application/pdf' and ContentTypevar != 'text/xml':
                recordData = {
                    "creationDate": creationDatevar,
                    "noteTitle": noteTitlevar,
                    "fullURLList": fullURLListvar,
                    "PractitionerReference": PractitionerReferencevar,
                    "ContentType": ContentTypevar,
                    "ContentUrl": ContentUrlvar,
                    "DecodedData":BinaryClinicalNote(ContentUrlvar, MI1ClientID, patientId)
                }
                returnData.append(recordData)
            

        # while paginationVariable == 'next':
            
        #     if len(returnData) > 10:
        #         break 

        #     recursiveResponse = requests.get(finalData['link'][1]['url'],headers = headersCerner)
        #     convertedData = recursiveResponse.content.decode('utf8')
        #     finalData = json.loads(convertedData)
        #     if len(finalData['link']) == 1:
        #         for i in range(0,len(finalData['entry'])):
        #             fullURLListvar = finalData['entry'][i]['fullUrl']
        #             PractitionerReferencevar = finalData['entry'][i]['resource']['author'][0]['reference']
        #             ContentTypevar = finalData['entry'][i]['resource']['content'][0]['attachment']['contentType']
        #             ContentUrlvar = finalData['entry'][i]['resource']['content'][0]['attachment']['url']
        #             if ContentTypevar != 'application/pdf' and ContentTypevar != 'text/xml':
        #                 recordData = {
        #                     "fullURLList": fullURLListvar,
        #                     "PractitionerReference": PractitionerReferencevar,
        #                     "ContentType": ContentTypevar,
        #                     "ContentUrl": ContentUrlvar,
        #                     "DecodedData":BinaryClinicalNote(ContentUrlvar, MI1ClientID, patientId)
        #                 }
        #                 returnData.append(recordData)
        #         break
        #     else:
        #         paginationVariable = finalData['link'][1]['relation']
        #         for i in range(0,len(finalData['entry'])):
        #             fullURLListvar = finalData['entry'][i]['fullUrl']
        #             PractitionerReferencevar = finalData['entry'][i]['resource']['author'][0]['reference']
        #             ContentTypevar = finalData['entry'][i]['resource']['content'][0]['attachment']['contentType']
        #             ContentUrlvar = finalData['entry'][i]['resource']['content'][0]['attachment']['url']
        #             if ContentTypevar != 'application/pdf' and ContentTypevar != 'text/xml':
        #                 recordData = {
        #                     "fullURLList": fullURLListvar,
        #                     "PractitionerReference": PractitionerReferencevar,
        #                     "ContentType": ContentTypevar,
        #                     "ContentUrl": ContentUrlvar,
        #                     "DecodedData":BinaryClinicalNote(ContentUrlvar, MI1ClientID, patientId)
        #                 }
        #                 returnData.append(recordData)

        return returnData


# if __name__ == '__main__':
#     Clinical Note read all
#     response = readAllClinicalNOte('123456789', 'eXbMln3hu0PfFrpv2HgVHyg3')
#     print(response)
