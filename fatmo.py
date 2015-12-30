#!/bin/python3
import requests
import configparser
import signal
import sys
from json import loads
from time import time, sleep
from os.path import realpath, expanduser, exists
from os import makedirs, geteuid, getenv
from shutil import rmtree

#Change this!
APP_ID="[APP ID]"
APP_SECRET="[APP SECRET]"
if geteuid() == 0:
    CFG_FILE='/etc/fatmo.ini'
    BLOCK_DIR='/netatmo/'
else:
    CFG_FILE=getenv('XDG_CONFIG_HOME', expanduser('~') + '/.config') + '/fatmo.ini'
    BLOCK_DIR='/tmp/netatmo/'

SLEEP=60*10 #10 minute intervals

shouldRun = True

def getAuthToken(email,password):
    data = {
        "grant_type":"password",
        "client_id":APP_ID,
        "client_secret":APP_SECRET,
        "username":email,
        "password":password,
        "scope":"read_station read_thermostat read_camera"
    }
    r = requests.post("https://api.netatmo.net/oauth2/token",data=data)
    status = loads(r.text)
    return r.status_code, status

def getStationData(token):
    r = requests.get("https://api.netatmo.net/api/getstationsdata?access_token="+token)
    data = loads(r.text)
    return data

def refreshToken(rtoken):
    data = {
        "grant_type":"refresh_token",
        "client_id":APP_ID,
        "client_secret":APP_SECRET,
        "refresh_token":rtoken
    }
    r = requests.post("https://api.netatmo.net/oauth2/token",data=data)
    status = loads(r.text)
    return r.status_code, status

def loadConfig():
    config = configparser.ConfigParser()
    if len(config.read(CFG_FILE)) == 0:
        #Create a config file
        config['Auth'] = {
            'atoken':'',
            'rtoken':'',
            'expires':''
        }
        print("Netatmo will require your email and password (we won't store this):")
        status = 400
        data = None
        while(status != 200):
            status, data = getAuthToken(input("E-Mail:"),input("Password:"))
            if status != 200:
                print("Either your E-Mail or Password was incorrect. Please retry.")

        config['Auth']['atoken'] = data['access_token']
        config['Auth']['rtoken'] = data['refresh_token']
        config['Auth']['expires'] = str(int(data['expires_in']) + int(time()))

        with open(CFG_FILE, 'w') as configfile:
            config.write(configfile)
    return config

def writeData(path,data):
    f = open(path,'w')
    f.write(str(data))
    f.close()

def mkdir(directory):
    if not exists(directory):
        makedirs(directory)

def writeToBlock(data):
    for device in data["body"]["devices"]:
        devdir = BLOCK_DIR+device["station_name"]+'/'
        mkdir(devdir)
        writeData(devdir+'type',device['type'])
        writeData(devdir+'wifi_status',device['wifi_status'])
        writeData(devdir+'firmware',device['firmware'])
        for key, value in device["dashboard_data"].items():
            writeData(devdir+key,value)
        for module in device["modules"]:
            moddir = devdir + "/modules/" + module["module_name"] + "/"
            mkdir(moddir)
            writeData(moddir+'battery_percent',module['battery_percent'])
            writeData(moddir+'firmware',module['firmware'])
            writeData(moddir+'type',module['type'])
            writeData(moddir+'last_seen',module['last_seen'])
            writeData(moddir+'rf_status',module['rf_status'])
            for key, value in module["dashboard_data"].items():
                writeData(moddir+key,value)


def cleanup():
    rmtree(BLOCK_DIR)
    sys.exit(0)

if __name__ == "__main__":
    #Check that the user has added their ids
    if APP_ID == "[APP ID]":
        print("Due to clientside applications requiring a secret, I can't share my application in the source file.")
        print("You need to create a netatmo app and set your ID and SECRET in",__file__)
        print("If you think this is dumb, go complain to netatmo so I don't have to do this stupid stuff.")
        sys.exit(1)

    def signal_handler(signal, frame):
        cleanup()
    signal.signal(signal.SIGINT, signal_handler)
    #Load config
    config = loadConfig()
    #Check for expirery

    mkdir(BLOCK_DIR)

    while(True):
        if int(time()) >= int(config['Auth']['expires']):
            status, tdata = refreshToken(config['Auth']['rtoken'])
            if status != 200:
                print("Token is out of date and could not be refreshed. Consider deleting",CFG_FILE)
                break;
            else:
                config['Auth']['atoken'] = tdata['access_token']
                config['Auth']['rtoken'] = tdata['refresh_token']
                config['Auth']['expires'] = str(int(tdata['expires_in']) + int(time()))
                with open(CFG_FILE, 'w') as configfile: #Save config
                    config.write(configfile)

        data = getStationData(config['Auth']['atoken'])
        writeToBlock(data)
        for i in range(SLEEP):
            sleep(1)
    cleanup()
