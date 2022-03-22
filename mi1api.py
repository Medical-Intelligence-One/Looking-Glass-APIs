import flask
from flask_cors import CORS
from flask import Flask, redirect , url_for, render_template, request, jsonify
from flask.wrappers import Response
from numpy import roots
import fetchData
from flask import request, jsonify, Response
import json
import requests
import pandas as pd
import time

app = Flask(__name__)
CORS(app)
app.config["DEBUG"] = True

@app.route('/', methods=['GET'])
def home():
    return '''<h1>MI-1 Sherlock</h1>
<p>A prototype API for Medical Intelligence One's cognitive computing platform.</p>'''

@app.route('/api/autocompleteProblems', methods=['GET', 'POST'])
def api_autocompleteProblems(): 
    data = request.data
    parsed = json.loads(data)
    startingtext = parsed['startsWith'][0]['startsWith']
    
    apidata = fetchData.autocompleteProblems(startingtext)
    result = apidata.to_json(orient="records")
    parsed = json.loads(result)
    result_data = jsonify(parsed)
    # result_data.headers.add("Access-Control-Allow-Origin", "*")
    return result_data

@app.route('/api/PotentialComorbidities', methods=['GET', 'POST'])
def api_PotentialComorbidities(): 
    pproblem = request.data
    parsed = json.loads(pproblem)
    cui_prob_list=[]
    for item in parsed['CUIs']:
        cui_prob_list.append(item['CUI'])
    
    apidata = fetchData.PotentialComorbidities(cui_prob_list)

    # Handle empty results
    if(apidata.empty):
        return jsonify([])
    else:
        result = apidata.to_json(orient="records")
        parsed = json.loads(result) 
        result_data = jsonify(parsed)
    # result_data.headers.add("Access-Control-Allow-Origin", "*")
        return result_data

@app.route('/api/AssocOrders', methods=['GET', 'POST'])
def api_AssocOrders(): 
    pproblem = request.data
    parsed = json.loads(pproblem)
    cui_prob_list=[]
    for item in parsed['CUIs']:
        cui_prob_list.append(item['CUI'])
    
    apidata = fetchData.AssocOrders(cui_prob_list)
    result = apidata.to_json(orient="records")
    parsed = json.loads(result)
    result_data = jsonify(parsed)
    # result_data.headers.add("Access-Control-Allow-Origin", "*")
    return result_data

@app.route('/api/LikelyOrders', methods=['GET', 'POST']) 
def api_LikelyOrders(): 
    pproblem = request.data
    parsed = json.loads(pproblem)
    cui_prob_list=[]
    for item in parsed['CUIs']:
        cui_prob_list.append(item['CUI'])
    
    rx, lab, procedures = fetchData.LikelyOrders(cui_prob_list)
    # Parse labs into json
    result_lab = lab.to_json(orient="records")
    parsed_lab = json.loads(result_lab)
    
    # Parse prescriptions into json
    result_rx = rx.to_json(orient="records")
    parsed_rx = json.loads(result_rx)
    
    # Parse procedures into json
    result_proc = procedures.to_json(orient="records")
    parsed_proc = json.loads(result_proc)
    
    result_data = jsonify(prescriptions=parsed_rx, labs=parsed_lab, procedures=parsed_proc)
    # result_data.headers.add("Access-Control-Allow-Origin", "*")
    return result_data

@app.route('/nodedisplay', methods=['GET', 'POST'])
def api_nodedisplay():
    try:
        start_time = time.time()
        apidata = fetchData.nodedisplay()
        end_time = time.time()
        if request.args.get('kp'):
            kp = list(request.args.get('kp').split(","))
        else:
            kp = None
        
        if request.args.get('p'):
            p = list(request.args.get('p').split(","))
        else:
            p = None
        #p = list(request.args.get('p', default = "").split(","))
        code = request.args.get('code')
        type = request.args.get('type')
        varprint = "<p>kp: " + str(kp) + "<br>" + "p: " + str(p) + "<br>" + "code: " + str(code) + "<br>" + "type: " + str(type) + "<br></p>"
        apidata = varprint + str(end_time - start_time) + " time " + apidata 

#         response.headers.add("Access-Control-Allow-Origin", "*")
        return render_template("nodetemplate.html",content=apidata)
    except Exception as e:
#         response.headers.add("Access-Control-Allow-Origin", "*")
        return str(e)

    
@app.route('/graphdisplay', methods=['GET', 'POST'])
def graphdisplay():
    iframe_url = fetchData.graphdisplay()
#     response.headers.add("Access-Control-Allow-Origin", "*")
    return f'<iframe src={iframe_url} name="iframe_a" height="100%" width="100%" title="Iframe Example"></iframe>'

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
#    app.run(host="76.251.77.235", port=5000) #host="0.0.0.0" will make the page accessable
                            #by going to http://[ip]:5000/ on any computer in 
                            #the network.
