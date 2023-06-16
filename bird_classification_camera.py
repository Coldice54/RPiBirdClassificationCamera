#!/usr/bin/env python3

import argparse
import contextlib
import os
import datetime
import json
import io
import pushNotifs

from aiy.vision.inference import CameraInference
from aiy.vision.annotator import Annotator
from aiy.vision.models import image_classification
from aiy.vision.models import inaturalist_classification
from picamera import PiCamera

allFrames= []
lastModifiedSettings = 0
settings = {"threshold": 0.5, 'frameCount': 15}
lastClassName = ""

def classes_info(classes):
    return ', '.join('%s (%.2f)' % pair for pair in classes)

@contextlib.contextmanager

def CameraPreview(camera, enabled):
    if enabled:
        camera.start_preview()
    try:
        yield
    finally:
        if enabled:
            camera.stop_preview()

def getBestClassFromSpan(allFrames):
    classesInAllFrames = {}
    for i,classes in enumerate(allFrames):
       for c in classes:
            className = c[0]
            score = c[1]
            if className in classesInAllFrames: #if the class is already in the dict
                classesInAllFrames[className] += score #add the probability to the existing probability
            else:
                classesInAllFrames[className] = score
    #get the max class in the window
    if (len(classesInAllFrames) == 0):
        return (None,0)
    print("========allFramesResult===========:")
    for classes in classesInAllFrames:
        print("classes:"+classes+" score:"+str(classesInAllFrames[classes]))
    topClass = max(classesInAllFrames, key=classesInAllFrames.get)
    return (topClass,classesInAllFrames[topClass])

def isNewVisit(classesInCurrentFrame, multiFrameThreshold):
    global lastClassName
    if (len(allFrames) == settings["frameCount"]):
        allFrames.pop(0)
    allFrames.append(classesInCurrentFrame)
    if (len(allFrames) == settings["frameCount"]):
        className,score = getBestClassFromSpan(allFrames)
        if (className == None or  className == 'background'):
            return (None,0)
        elif score > multiFrameThreshold:
            if className == lastClassName:
                print('Visit detected but same bird: ' + className)
                return (None,0)
            lastClassName = className
            allFrames.clear()
            return (className,score)
    return (None,0)


def checkSettings():
    global lastModifiedSettings
    global settings

    lastModified = os.path.getmtime('settings.json')
    if (lastModified > lastModifiedSettings):
        lastModifiedSettings = lastModified
        #read settings
        with open('settings.json', 'r') as f:
            print("settings changed - reloading")
            settings = json.load(f)
            print("settings reloaded")

def loadIncludedBirds():
    inclusions = {}
    with io.open('includedbirds.txt', 'r', encoding='utf-8') as f:
        for line in f.readlines():
            inclusions[line] = 1
    return inclusions

pushToken = "ExponentPushToken[Blah]"
lastModifiedToken = 0
def checkToken():
    global lastModifiedToken
    global pushToken
    if (not os.path.exists('pushToken.txt')):
        return
    lastModified = os.path.getmtime('pushToken.txt');
    if (lastModified > lastModifiedToken):
        lastModifiedToken = lastModified
        #read settings
        with open('pushToken.txt', 'r') as f:
            pushToken = f.readline()

def main():
    absolute_path = os.path.dirname(os.path.abspath(__file__))
    print(absolute_path)
    if not os.path.exists(os.path.join(absolute_path,'static')):
        os.makedirs(os.path.join(absolute_path,'static'))
    if not os.path.exists(os.path.join(absolute_path,'static/birdcaptures')):
        os.makedirs(os.path.join(absolute_path,'static/birdcaptures'))
    parser = argparse.ArgumentParser('Bird Classification Camera.')
    parser.add_argument('--bounds', '-b', type=tuple, dest='bounds', default=(820, 616, 1640, 1232),
        help='Sets the bounds in which predictions are made. A 4-tuple consisting of the x and y coordinates of\nthe center and the x and y dimensions of the bounds.')
    args = parser.parse_args()
    includedBirds = loadIncludedBirds()
    # Annotator renders in software so use a smaller size and scale results
    # for increased performace.
    
    with PiCamera(sensor_mode=4, framerate=15) as camera, \
        CameraPreview(camera, enabled=True), \
        CameraInference(inaturalist_classification.model(inaturalist_classification.BIRDS)) as inference:
        
        scale_x = 320 / 1640
        scale_y = 240 / 1232
        
        # Incoming boxes are of the form (x, y, width, height). Scale and
        # transform to the form (x1, y1, x2, y2).
        def transform(bounding_box):
            x, y, width, height = bounding_box
            return (scale_x * x, scale_y * y, scale_x * (x + width),
                    scale_y * (y + height))
        for result in inference.run():
            checkSettings()
            tresholdForAllFrames = settings["threshold"]*settings["frameCount"]
            classes = inaturalist_classification.get_classes(result, top_k=5, threshold=0.1)
            
            print(classes_info(classes))
            className,classConfidence = isNewVisit(classes,tresholdForAllFrames)
            #forceCap = True
            if (className != None and className in includedBirds):
                fileName = (className
                + '*$*' + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
                + '*$*' + str(classConfidence)[2:] + '.jpg').replace(' ','-')
                fullFileName = (absolute_path + '/static/birdcaptures/' + fileName)
                camera.capture(fullFileName)
                checkToken()
                pushNotifs.push(pushToken, "A "+ className+ " visited you!")  
                #print(className, classConfidence, str(classes))
                print("bird detected: " + className)
                print((className
                + '*$*' + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
                + '*$*' + str(classConfidence)[2:] + '.jpg').replace(' ','-'))
            else:
                print("no bird detected")
            
                
                    

            


if __name__ == '__main__':
    main()
