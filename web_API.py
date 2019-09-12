#!/usr/bin/env python3
"""
API between a vagrant_API and web (ie: jbot)
"""
__author__ = "Simon Rosner"
__credits__ = ["Simon Rosner"]
__version__ = "2018.9.5"
__maintainer__ = "Simon Rosner"
__email__ = ""

from vagrant_API import *
from flask import Flask, jsonify, request
app = Flask(__name__)

#Constants
import constants
SERVICE = constants.SERVICE
DATABASE = constants.DATABASE
BOX = constants.BOX

def v():
    return V_API(SERVICE, DATABASE, BOX)

@app.route('/addBlockedCommand/',methods=['POST'])
def addBlockedCommand():
    """
    string:com
    int|string:userID
    """
    args = request.args.to_dict()
    v2 = v()
    if v2.adminCheck(args[userID]) or v2.adminCheckThroughService(args[userID]):
        v2.addBlockedCommand(args[com])
        return com + ' added to blocked commands'
    else:
        return 'Only admins can do that'

@app.route('/adminCheck/', methods=['GET','POST'])
def adminCheck():
    """
    int:userID
    """
    return jsonify(v().adminCheck(request.args.get('userID')))

@app.route('/adminCheckThroughService/', methods=['GET','POST'])
def adminCheckThroughService():
    """
    string:serviceID
    """
    res = v().adminCheckThroughService(request.args.get('serviceID'))
    return jsonify(res)

@app.route('/buildThroughService/', methods=['POST'])
def buildThroughService():
    """
    string:serviceID
    string:box optional
    """
    serviceID = request.args.get('serviceID',None)
    box = request.args.get('box',None)
    return jsonify(v().buildThroughService(serviceID,box))

@app.route('/buildVM/', methods=['POST'])
def buildVM():
    """
    int:userID
    string:box optional
    """
    args = request.args.get('userID',None)
    args = request.args.get('box',None)
    return jsonify(v().buildVM(userID, box))

@app.route('/claimUser/',methods=['POST'])
def claimUser():
    """
    int:targetID
    string:username
    string:serviceID
    """
    args = request.args.to_dict()
    res = v().claimUser(args[targetID],args[username],args[serviceID])   
    return jsonify(res)

@app.route('/claimByVM/', methods=['POST'])
def claimByVM():
    """
    int:targetVMid
    string:serviceUsername
    string:serviceID
    """
    args = request.args.to_dict()
    res = v().claimByVM(args[targetVMid],args[serviceUsername],args[serviceID])
    return jsonify(res)

@app.route('/claimVM/',methods=['POST'])
def claimVM():
    """
    int:targetVMid
    int:userID
    """
    targetVMid = request.args.get('targetVMid')
    userID = request.args.get('userID')
    res = v().claimVM(targetVMid,userID)
    return jsonify(res)
    
@app.route('/cleanVMs/',methods=['POST'])
def cleanVMs():
    """
    int|string:userID
    """
    uid = request.args.get('userID')
    v2 = v()
    if v2.adminCheck(userID) or v2.adminCheckThroughService(userID):
        return jsonify(v2.cleanVMs())
    else:
        return 'Only admins can do that'

@app.route('/createServiceUser/',methods=['POST'])
def createServiceUser():
    """
    string:username
    int:realID
    string:serviceID
    """
    args = request.args.to_dict()
    res = v().createServiceUser(args[username],args[realID],args[serviceID])
    return jsonify(res)

@app.route('/createUser/',methods=['POST'])
def createUser():
    """
    string:name
    """
    return jsonify(v().createUser(request.args.get('name')))

@app.route('/deleteVM/',method=['POST'])
def deleteVM():
    """
    int:VMid
    """
    vmid = request.args.get('VMid')
    res = v().deleteVM(VMid)
    return jsonify(res)

@app.route('/destroyVM/',methods=['POST'])
def destroyVM():
    """
    int:VMid
    int:userID
    """
    args = request.args.to_dict()
    results = False
    if (v().userOwnsVM(args[userID],args[VMid])
        or v().adminCheck(args[userID])
        or v().adminCheckThroughService(args[userID])):
        results = jsonify(v().destroyVM(request.args.get('VMid')))
    return results

@app.route('/getIDbyName/',methods=['GET','POST'])
def getIDbyName():
    """
    string:name
    """
    return jsonify(v().getIDbyName(request.args.get('name')))

@app.route('/getIDbyHostname/',methods=['GET','POST'])
def getIDbyHostname():
    """
    string:hostname
    """
    return jsonify(v().getIDbyHostname(request.args.get('hostname')))

@app.route('/getLogsSince/',methods=['POST'])
def getLogsSince():
    """
    int:time
    """
    return jsonify(v().getLogsSince(request.args.get('time')))

@app.route('/getUserID/',methods=['POST'])
def getUserID():
    """
    string:serviceID
    """
    return jsonify(v().getUserID(request.args.get('serviceID')))

@app.route('/guessIDbyName/',methods=['GET','POST'])
def guessIDbyName():
    """
    string:name
    """
    return jsonify(v().guessIDbyName(request.args.get('name')))

@app.route('/listUsers/')
def listUsers():
    return jsonify(v().listUsers())

@app.route('/listVMs/')
def listVMs():
    return jsonify(v().listVMs())

@app.route('/makeAdmin/',methods=['POST'])
def makeAdmin():
    """
    int:userID
    int:targetID
    """
    args = request.args.to_dict()
    v2 = v()
    #double security
    if v2.adminCheck(args[userID]):
        return jsonify(v2.makeAdmin(args[userID],args[targetID]))
    else:
        return 'Only admins can do that'

@app.route('/provisionVM/',methods=['POST'])
def provisionVM():
    """
    int:userID
    int:VMid
    """
    args = request.args.to_dict()
    results = False
    if (v().userOwnsVM(args[userID],args[VMid])
        or v().adminCheck(args[userID])
        or v().adminCheckThroughService(args[userID])):
        results = jsonify(v().provisionVM(request.args.get('VMid')))
    return results

@app.route('/vagrant/',methods=['POST'])
def vagrant():
    """
    int:userID
    string:com
    """
    v2 = v()
    if v2.adminCheck(request.args.get('userID')):
        v_args = "vagrant " + com
        return jsonify(v2.other(v_args))
    else:
        return 'Only admins can do that'

@app.route('/custom/',methods=['POST'])
def custom():
    """
    int:userID
    string:com
    """
    v2 = v()
    if v2.adminCheck(request.args.get('userID')):
        return jsonify(v2.other(com))
    else:
        return 'Only admins can do that'

@app.route('/reactivateUser/',methods=['POST'])
def reactivateUser():
    """
    int:userID
    int:targetID
    """
    userID = request.args.get('userID')
    targetID = request.args.get('targetID')
    res = v().reactivateUser(userID,targetID)
    return jsonify(res)

@app.route('/rebuildVM/',methods=['POST'])
def rebuildVM():
    """
    int:VMid
    """
    return jsonify(v().rebuildVM(request.args.get('VMid')))

@app.route('/removeUser/',method=['POST'])
def removeUser()
    """
    int|string:userID
    int:targetID
    """
    userID = request.args.get('userID')
    targetID = request.args.get('targetID')
    v2=v()
    if v2.adminCheck(userID) or v2.adminCheckThroughService(userID):
        return jsonify(v2.removeUser(userID,targetID))
    else:
        return 'Only admins can do that'

@app.route('/userOwnsVM/',methods=['POST'])
def userOwnsVM():
    """
    int:userID
    int:VMid
    """
    args = request.args.to_dict()
    res = v().userOwnsVM(args[userID],args[VMid])
    return jsonify(res)

if __name__ == '__main__':
   app.run(debug = True)
