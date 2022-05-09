import json

import requests
import xmltodict
from bs4 import BeautifulSoup

from ehr_apis_epic import checkLocalDictAuth, setHeaders


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
    getMessage = checkLocalDictAuth(MI1ClientID, patientId)
    headers = setHeaders(getMessage['accessToken'])
    binaryUrlList = []
    responses = requests.get(
        'https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/DocumentReference?patient=' + patientId,
        headers=headers)
    convertedData = xmltodict.parse(responses.content)
    convertedData = json.dumps(convertedData)
    convertedData = json.loads(convertedData)

    for i in range(0, len(convertedData['Bundle']['entry']) - 1):
        if convertedData['Bundle']['entry'][i]['resource']['DocumentReference']['category']['coding']['code']['@value'] == 'clinical-note':
            # url tag returns value like "Binary/ekAJmRWsOeeVsqjgMnmX-5ZTCqyW.NZW3fvSH8mNXZSg3"
            urlData =  convertedData['Bundle']['entry'][i]['resource']['DocumentReference']['content']['attachment']['url'][
                    '@value']
            urlData = urlData.replace('Binary/','')
            binaryUrlList.append(urlData)

    binaryReadList = []
    binaryReadList.append({
        "PatientId":patientId,
        "NoteData":[]
    })
    for i in range(0, 5):
        lst = []
        responses = requests.get('https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Binary/' + binaryUrlList[i],
                                 headers=headers)
        BinaryData = BeautifulSoup(responses.content, 'html5lib')
        getFilter = BinaryData.find('div')
        for j in getFilter.recursiveChildGenerator():
            if j.name == 'span':
                if len(j.text.strip()) != 0:
                    lst.append(j.text)

        BinaryReadData = []
        index = -1
        for j in lst:
            if len(j.strip()) == len(j):
                index = index + 1
                BinaryReadData.append({
                    'ProblemText': j,
                    "Orders": []
                })
            else:
                BinaryReadData[index]['Orders'].append({
                    'OrderText': j.strip(),
                })
        binaryReadList[0]["NoteData"].append({
           "BinaryId":binaryUrlList[i],
           "HTML": responses.content,
           "JSON": BinaryReadData
        })
    return binaryReadList


if __name__ == '__main__':
    # Clinical Note read all
    response = readAllClinicalNOte('123456789', 'eXbMln3hu0PfFrpv2HgVHyg3')
    # print(response)
