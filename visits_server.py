from flask import Flask, render_template, jsonify, request
from flask_cors import CORS, cross_origin
import json
import os

app = Flask(__name__)
cors = CORS(app)

@app.route('/settings', methods=['GET'])
def get_settings():
    #check if settings file exists
    if os.path.exists('settings.json'):
        print("settings found")
        with open('settings.json', 'r') as f:
            settings = json.load(f)
    else:
        with open('settings.json', 'w+') as f:
            print("creating settings file")
            settings = {"threshold" : 0.5, "frameCount" : 15}
            json.dump(settings, f)
    return jsonify(settings)

@app.route('/settings', methods=['POST'])
def write_settings():
    settings = request.data.decode('utf-8')
    print("received"+settings)
    with open('settings.json', 'w') as f:
        f.write(settings)
    return 'Settings written to file'

@app.route('/visits', methods=['GET', 'POST'])

def visits():
    image_names = os.listdir(os.path.dirname(__file__)+'/static/birdcaptures')
    #resp = Flask.make_response(render_template('home.html', image_names=image_names))
    #resp.headers.set('Access-Control-Allow-Origin', '*')
    
    return render_template('home.html', image_names=image_names)

@app.route('/visitsjson', methods=['GET'])

def getVisitsJson():
    image_names = os.listdir(os.path.dirname(__file__)+'/static/birdcaptures')
    result = []
    for imageName in image_names:
        imageNameNoExt = imageName.split(".")[0]
        components = imageNameNoExt.split("*$*")
        item = {}
        item['birdImage'] = imageName
        item['birdIdentification'] = components[0].replace("-"," ")
        item['identificationConfidence'] = components[2] #round to 3 digits
        item['dateTime'] = components[1]
        result.append(item)

    return jsonify(result)

@app.route('/pushToken', methods=['POST'])
def write_token():
    text = request.data.decode('utf-8')
    data = request.get_json()
    print('pushing Token')
    if 'pushToken' in data:
        with open('pushToken.txt', 'w') as f:
            f.write(data['pushToken'])
        return 'pushToken written to file'
    else:
        return 'Error: no token in request'
    