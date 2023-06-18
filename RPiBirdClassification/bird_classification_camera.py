#!/usr/bin/env python3
###################################################################
# Main Bird Classification Runtime
# Alexander Berkaloff 2023
################################################################
# Parts Based on the Google AIY Vision Toolkit
# Copyright 2017 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
            
# getBestClassFromSpan
# Aggregates the scores of each class over
# the last frameCount frames and
# returns the class with the highest score.
def getBestClassFromSpan(allFrames):
    classesInAllFrames = {}
    # print("getBestClassFromSpan:")
    print("==")
    for i,classes in enumerate(allFrames):
        #print("frame:"+str(i) ) #+"count:"+str(len(classes)))
        for c in classes:
            className = c[0]
            score = c[1]
            # print("className:"+className+" score:"+str(score))
            if className in classesInAllFrames: #if the class is already in the dict
                classesInAllFrames[className] += score #add the probability to the existing probability
            else:
                classesInAllFrames[className] = score
    #get the max class in the window
    if (len(classesInAllFrames) == 0):
        return (None,0)
    print("==Merged over "+str(len(allFrames))+"frames:")
    for c in classesInAllFrames:
        print("class:"+c+" score:"+str(classesInAllFrames[c]))
    topClass = max(classesInAllFrames, key=classesInAllFrames.get)
    return (topClass,classesInAllFrames[topClass])

# isNewVisit
# checks whether we are seeing a new bird
def isNewVisit(classesInCurrentFrame,multiFrameThreshold):
    global lastClassName
    
    if (len(allFrames) == settings["frameCount"]):
        allFrames.pop(0)
    allFrames.append(classesInCurrentFrame)
    if (len(allFrames) == settings["frameCount"]):
        className,score = getBestClassFromSpan(allFrames)
        if (className == None or className == 'background'):
            return (None,0)
        elif score > multiFrameThreshold:
            if className == lastClassName:
                print('Visit detected but same bird: ' + className)
                return (None,0)
            lastClassName = className #now we can save after we have tested 
            #empty the allFrames list to restart visit detection from scratch
            print("last frame-count:"+str(len(allFrames[frameCount-1])))
            for c in allFrames[frameCount-1]:
                print("className:"+c[0]+" score:"+str(c[1]))
            print('New visit detected: ' + className)
            allFrames.clear()
            return (className,score)
    return (None,0)

# checkSettings
# checks whether settings have changed
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

# loadIncludedBirds
# loads inclusion list from text file, names
# are common name with scientific name in
# parentheses, line separated
def loadIncludedBirds():
    inclusions = {}
    with io.open('includedbirds.txt', 'r', encoding='utf-8') as f:
        for line in f.readlines():
            line = line.strip('\n')
            inclusions[line] = 1
    return inclusions

# checkToken
# checks token for push notifications
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
    print(includedBirds)
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
            thresholdForAllFrames = settings["threshold"]*settings["frameCount"]
            classes = inaturalist_classification.get_classes(result, top_k=5, threshold=0.1)
            
            print(classes_info(classes))
            className,classConfidence = isNewVisit(classes,thresholdForAllFrames)
            #forceCap = True
            print('className:', className)
            print(className in includedBirds)
            if (className in includedBirds):
                fileName = (className
                + '*$*' + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
                + '*$*' + str(classConfidence)[2:] + '.jpg').replace(' ','-')
                fullFileName = (absolute_path + '/static/birdcaptures/' + fileName)
                camera.capture(fullFileName)
                checkToken()
                pushNotifs.push(pushToken, "A "+ className + " visited you!")  
                #print(className, classConfidence, str(classes))
                print("bird detected: " + className)
                print((className
                + '*$*' + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
                + '*$*' + str(classConfidence)[2:] + '.jpg').replace(' ','-'))
            else:
                print("no bird detected")
            
                
                    

            


if __name__ == '__main__':
    main()
