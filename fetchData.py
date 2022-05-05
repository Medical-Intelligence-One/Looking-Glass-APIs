import pandas as pd
from neo4j import GraphDatabase
import matplotlib.pyplot as plt
from neo4j import GraphDatabase
import pandas as pd
from py2neo import Graph
from IPython.core.display import display, HTML, Javascript
import mi1_neo4jupyter

import graphistry
graphistry.register(api=3, protocol="https", server="hub.graphistry.com", username="Graphistry12345", password="Alacron_05")
from neo4j import GraphDatabase, Driver

driver=GraphDatabase.driver(uri="bolt://76.251.77.235:7687", auth=('neo4j', 'NikeshIsCool')) 
session=driver.session()
    
def autocompleteProblems(startingtext):
    query = '''
    MATCH (c1:Concept)
    WHERE c1.term STARTS WITH '{startingtext}' AND c1.semantic_type IN ["['Pathologic Function']", "['Disease or Syndrome']", "['Mental or Behavioral Dysfunction']", "['Sign or Symptom']", "['Injury or Poisoning']", "['Neoplastic Process']"] 
    RETURN DISTINCT(c1.cui) AS `Known_CUI`, c1.term AS `Known_Problem`
    '''.format(startingtext=startingtext)
    data = session.run(query)
    autocomplete_problems_prompts = pd.DataFrame([dict(record) for record in data])
    return autocomplete_problems_prompts

def autocompleteOrders(startingtext):
    query = '''
    MATCH (c1:Concept)
    WHERE c1.term STARTS WITH '{startingtext}' AND c1.semantic_type IN ["['Clinical Drug']", "['Clinical Attribute']"] 
    RETURN DISTINCT(c1.cui) AS `Known_CUI`, c1.term AS `Known_Order`
    '''.format(startingtext=startingtext)
    data = session.run(query)
    autocomplete_orders_prompts = pd.DataFrame([dict(record) for record in data])
    return autocomplete_orders_prompts
   
def autocomplete_rareDz_findings(startingtext):
    query = '''
    MATCH (c1:Concept)
    MATCH (h:HPOentity)
    WHERE c1.term STARTS WITH '{startingtext}' and c1.cui = h.umls_id
    RETURN DISTINCT(c1.cui) AS `Clinical_Finding_CUI`, c1.term AS `Clinical_Finding`
    '''.format(startingtext=startingtext)
    data = session.run(query)
    autocomplete_rareDz_findings = pd.DataFrame([dict(record) for record in data])
    return autocomplete_rareDz_findings

def PotentialComorbidities(cui_prob_list):
    
    # Get NLP-derived problem matches
    query = '''
    MATCH p=(ord:Concept)-[r:OCCURS_WITH]->(c:Concept) 
    WHERE c.cui IN {cui_prob_list} AND ord.semantic_type IN ["['Pathologic Function']", "['Disease or Syndrome']", "['Mental or Behavioral Dysfunction']", "['Sign or Symptom']", "['Injury or Poisoning']", "['Neoplastic Process']"]
    WITH round(r.co_occurrence_probability, 5) AS Score, ord, r, c
    RETURN c.cui AS `Known_CUI`, c.term AS `Known_Problem`, ord.cui AS `CUI`, ord.term AS `Problem`, Score
    ORDER BY r.co_occurrence_probability DESC
    LIMIT 10
    '''.format(cui_prob_list=cui_prob_list)
    data = session.run(query)
    likely_comorbidities_NLP = pd.DataFrame([dict(record) for record in data])
    
    # Get ICD-coded problem matches
    query = '''
    MATCH p=(ord:D_Icd_Diagnoses)-[r:OCCURS_WITH]->(c:Concept) 
    WHERE c.cui IN {cui_prob_list} 
    WITH round(r.co_occurrence_probability, 5) AS Score, ord, r, c
    RETURN c.cui AS `Known_CUI`, c.term AS `Known_Problem`, ord.icd9_code AS `CUI`, ord.long_title AS `Problem`, Score
    ORDER BY r.co_occurrence_probability DESC
    LIMIT 10
    '''.format(cui_prob_list=cui_prob_list)
    data = session.run(query)
    likely_comorbidities_ICD = pd.DataFrame([dict(record) for record in data])
    
    # Combine the NLP-derived and ICD-coded dataframes for output
    likely_comorbidities = likely_comorbidities_NLP.append(likely_comorbidities_ICD)
    if(likely_comorbidities.empty):
        lst = []
        df=pd.DataFrame(lst)
        return df


    likely_comorbidities.sort_values(by='Score', ascending=False, inplace=True)

    
    return likely_comorbidities.head(10)

def LikelyOrders(cui_prob_list):
    
    # Find prescriptions associated with the input problem    
    query = '''
    MATCH p=(ord:Concept)-[r:OCCURS_WITH]->(c:Concept) 
    WHERE c.cui IN {cui_prob_list} AND ord.semantic_type IN ["['Clinical Drug']"]
    WITH round(r.co_occurrence_probability, 5) AS Score, ord, r
    RETURN ord.cui AS `Code`, ord.term AS `Order`, Score
    ORDER BY r.co_occurrence_probability DESC
    LIMIT 10
    '''.format(cui_prob_list=cui_prob_list)
    data = session.run(query)
    orders_likely_rx = pd.DataFrame([dict(record) for record in data]).head(10)
    
    # Find abnormal labs associated with the input problem
    query = '''
    MATCH p=(ord:Concept)-[r:OCCURS_WITH]->(c:Concept) 
    WHERE c.cui IN {cui_prob_list} AND ord.semantic_type IN ["['Clinical Attribute']"]
    WITH round(r.co_occurrence_probability, 5) AS Score, ord, r
    RETURN ord.cui AS `Code`, ord.description AS `Order`, Score
    ORDER BY r.co_occurrence_probability DESC
    LIMIT 10
    '''.format(cui_prob_list=cui_prob_list)
    data = session.run(query)
    orders_likely_lab = pd.DataFrame([dict(record) for record in data]).head(10)
    
    # Find procedures associated with the input problem
    query = '''
    MATCH p=(ord:D_Icd_Procedures)-[r:OCCURS_WITH]->(c:Concept) 
    WHERE c.cui IN {cui_prob_list}
    WITH round(r.co_occurrence_probability, 5) AS Score, ord, r
    RETURN ord.icd9_code AS `Code`, ord.long_title AS `Order`, Score
    ORDER BY r.co_occurrence_probability DESC
    LIMIT 10
    '''.format(cui_prob_list=cui_prob_list)
    data = session.run(query)
    orders_likely_procedure = pd.DataFrame([dict(record) for record in data]).head(10)
    
    return orders_likely_rx, orders_likely_lab, orders_likely_procedure

# Create a new endpoint with a single dataframe and a new column for type of order, limit results to about 10

def AssocOrders(cui_prob_list):
    orders_likely_rx, orders_likely_lab, orders_likely_procedure = LikelyOrders(cui_prob_list)
    orders_likely_rx['Type'] = 'Prescription'
    orders_likely_lab['Type'] = 'Lab'
    orders_likely_procedure['Type'] = 'Procedure'
    AssocOrders = pd.concat([orders_likely_rx, orders_likely_lab, orders_likely_procedure])

    if(AssocOrders.empty):
        lst = []
        df=pd.DataFrame(lst)
        return df

    AssocOrders.sort_values('Score', ascending = False, inplace = True)
    AssocOrders = AssocOrders.head(10)
    return AssocOrders
    
def rareDiseaseSearch(cui_finding_list):

    # Get a list of the most likely diseases and the data used to calculate likelihood
    query = '''
    MATCH (pos_f:HPOentity)-[given_r:ASSOC_WITH]->(d:OrphEntity)<-[total_r:ASSOC_WITH]-(total_f:HPOentity)

    // Get a list of diseases which have at least one finding in the list of CUIs for given findings
    // Filter out any diseases which are excluded by a finding in the list of given findings
    WHERE pos_f.umls_id IN {cui_finding_list} AND d.prevalence_estimate_upper IS NOT NULL AND (given_r.diagnostic_criterion_attribute IS NULL OR NOT given_r.diagnostic_criterion_attribute = 'Exclusion_DC')

    // Get lists of positive findings and relationships to positive findings
    WITH d.name AS Disease, d.umls_id AS Disease_CUI, d.definition AS Disease_Definition, d.prevalence_estimate_upper AS Disease_Prevalence, collect(DISTINCT(pos_f.name)) AS Positive_Findings, collect(DISTINCT(pos_f.umls_id)) AS Pos_Find_CUIs, collect(DISTINCT(total_r)) AS All_Find_Rel, collect(DISTINCT(total_f.name)) AS all_dz_findings, collect(DISTINCT(total_f.umls_id)) AS all_dz_CUIs, collect(DISTINCT(given_r)) AS Pos_Find_Rel

    // Get list of relationships to negative findings
    WITH [x IN All_Find_Rel WHERE NOT x IN Pos_Find_Rel] AS Neg_Find_Rel, Pos_Find_Rel, Disease, Disease_CUI, Disease_Definition, all_dz_findings, all_dz_CUIs, Disease_Prevalence, Positive_Findings, Pos_Find_CUIs

    // Get list of negative findings
    WITH [x IN all_dz_findings WHERE NOT x in Positive_Findings] AS Negative_Findings, [x IN all_dz_CUIs WHERE NOT x in Pos_Find_CUIs] AS Neg_Find_CUIs, Neg_Find_Rel, Pos_Find_Rel, Disease, Disease_CUI, Disease_Definition, Disease_Prevalence, Positive_Findings, Pos_Find_CUIs

    UNWIND Pos_Find_Rel as Pos_Find_Rel_List

    UNWIND
      CASE
        WHEN Neg_Find_Rel = [] THEN [null]
        ELSE Neg_Find_Rel
      END AS Neg_Find_Rel_List

    // Calculate the sum of approximate frequency values for all negative findings for each disease, changing null to 0 when no relationships to negative findings exist
    WITH Disease, Disease_CUI, Disease_Definition, Disease_Prevalence, Positive_Findings, Pos_Find_CUIs, Negative_Findings, Neg_Find_CUIs, Pos_Find_Rel_List, sum(toFloat(COALESCE(Neg_Find_Rel_List.approx_frequency, 0))) AS Sum_Neg_Find_Freq, collect(COALESCE(toFloat(Neg_Find_Rel_List.approx_frequency), 'Null')) AS Neg_Find_Freqs

    // Calculate the sum of approximate frequency values for all positive findings for each disease
    WITH Disease, Disease_CUI, Disease_Definition, Disease_Prevalence, Positive_Findings, Pos_Find_CUIs, Negative_Findings, Neg_Find_CUIs, sum(toFloat(Pos_Find_Rel_List.approx_frequency)) AS Sum_Pos_Find_Freq, Pos_Find_Rel_List.evidence AS Disease_Finding_Assoc_Evidence, collect(COALESCE(toFloat(Pos_Find_Rel_List.approx_frequency), 'Null')) AS Pos_Find_Freqs, Sum_Neg_Find_Freq, Neg_Find_Freqs

    // Multiply the disease prevalence by the difference between the sum of frequencies of positive and negative findings
    RETURN Disease, Disease_CUI, Disease_Definition, Disease_Prevalence, Positive_Findings, Pos_Find_CUIs, Pos_Find_Freqs, Negative_Findings, Neg_Find_CUIs, Neg_Find_Freqs, ((Sum_Pos_Find_Freq - Sum_Neg_Find_Freq) * -log(Disease_Prevalence)) AS Disease_Probability, Disease_Finding_Assoc_Evidence

    ORDER BY Disease_Probability DESC
    LIMIT 10
    '''.format(cui_finding_list = cui_finding_list)
    data = session.run(query)
    mostLikelyRareDiseases = pd.DataFrame([dict(record) for record in data])
    
    # Handle empty results without causing an error
    if(mostLikelyRareDiseases.empty):
        lst = []
        df=pd.DataFrame(lst)
        return df    

    # Transform the evidence column into URLs whenever the evidence comes from PubMed
    mostLikelyRareDiseases['Disease_Finding_Assoc_Evidence'] = mostLikelyRareDiseases['Disease_Finding_Assoc_Evidence'].str.split('_')
    evidence_column = []
    Matched_Findings_Column = []
    Unmatched_Findings_Column = []
    
    for row in mostLikelyRareDiseases.iterrows():
        
        # Convert PMIDs into links to their respective PubMed articles
        evidence_urls = []
        evidence = row[1]['Disease_Finding_Assoc_Evidence']
        if evidence is not None:
            for item in evidence:
                publication = item.split(':')
                if publication[0] == 'PMID':
                    url = 'https://pubmed.ncbi.nlm.nih.gov/'+publication[1]
                    evidence_urls.append(url)
                else:
                    evidence_urls.append(item)
            evidence_column.append(evidence_urls)
        else:
            evidence_column.append(None)
            
            
        # Combine the matched findings for each disease into a list of dictionaries
        Matched_Name_List = row[1]["Positive_Findings"]
        Matched_Frequency_List = row[1]["Pos_Find_Freqs"]
        Matched_CUI_List = row[1]["Pos_Find_CUIs"]
        Matched_dict_list = []
        for index, Name in enumerate(Matched_Name_List):
            Matched_dict = {}
            Matched_dict['Name'] = Name
            Matched_dict['Frequency'] = Matched_Frequency_List[index]
            Matched_dict['CUI'] = Matched_CUI_List[index]
            Matched_dict_list.append(Matched_dict)
        
        Matched_Findings_Column.append(Matched_dict_list)
        
        
        # Combine the unmatched findings for each disease into a list of dictionaries
        Unmatched_Name_List = row[1]["Negative_Findings"]
        Unmatched_Frequency_List = row[1]["Neg_Find_Freqs"]
        Unmatched_CUI_List = row[1]["Neg_Find_CUIs"]
        Unmatched_dict_list = []
        for index, Name in enumerate(Unmatched_Name_List):
            Unmatched_dict = {}
            Unmatched_dict['Name'] = Name
            Unmatched_dict['Frequency'] = Unmatched_Frequency_List[index]
            Unmatched_dict['CUI'] = Unmatched_CUI_List[index]
            Unmatched_dict_list.append(Unmatched_dict)
        Unmatched_Findings_Column.append(Unmatched_dict_list)
            
    mostLikelyRareDiseases['Disease_Finding_Assoc_Evidence'] = evidence_column
    mostLikelyRareDiseases['Matched_Findings'] = Matched_Findings_Column
    mostLikelyRareDiseases['Unmatched_Findings'] = Unmatched_Findings_Column
    mostLikelyRareDiseases.drop(inplace=True, columns = ['Positive_Findings', 'Pos_Find_Freqs', 'Pos_Find_CUIs', 'Negative_Findings', 'Neg_Find_Freqs', 'Neg_Find_CUIs'])

    return mostLikelyRareDiseases

def nodedisplay():
#     g=Graph('neo4j+s://1d23f23f.databases.neo4j.io:7687', auth=("neo4j", "FUjaBMKHBigyHtjaD9il71GV4GVGAsi7YBWtIBn-Cyo"))
    g=Graph('bolt://76.251.77.235:7687', auth=('neo4j', 'NikeshIsCool'))
    options = {"Src_Prob": "name", "Problem": "name", "Diagnosis": "name", "Treatment": "name"}


    query = """
        MATCH (n)-[r]->(m)
        RETURN n ,
            id(n),
            r,
            m ,
            id(m)
        LIMIT 25
        """
        
    test = mi1_neo4jupyter.draw(g,options,query, physics=True)
    return test.data 

def graphdisplay(kp, p, code, type):
    #NEO4J_CREDS = {'uri': 'neo4j+s://1d23f23f.databases.neo4j.io:7687', 'auth': ('neo4j', 'FUjaBMKHBigyHtjaD9il71GV4GVGAsi7YBWtIBn-Cyo')}
    NEO4J_CREDS = {'uri': 'bolt://76.251.77.235:7687', 'auth': ('neo4j', 'NikeshIsCool')}
    graphistry.register(bolt=GraphDatabase.driver(**NEO4J_CREDS))
    
    g = graphistry.cypher("""
    WITH '{p}' as p, '{code}' as code
    MATCH path = (stroke:Concept)-[*..4]-(af:Concept) 
    WHERE stroke.cui = p AND af.cui = code
    RETURN path
    LIMIT 20
    """.format(p=p, code=code))
    
    g = g.bind(edge_title="type")
    g = g.bind(point_title="term")
    g = g.settings(url_params={
    'play': 2000, 'showPointsOfInterest': True, 'showPointsOfInterestLabel': True, 'showLabelPropertiesOnHover': False,
    'pointsOfInterestMax': 50
    })
    g = g.layout_settings(strong_gravity=True, gravity=0.75)
    g = g.addStyle(logo={'url': 'https://upload.wikimedia.org/wikipedia/commons/4/48/BLANK_ICON.png'})
    iframe_url = g.plot(render=False)
    return iframe_url
