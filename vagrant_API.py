#!/usr/bin/env python3
"""
API between a chat bot and vagrant
"""
__author__ = "Simon Rosner"
__credits__ = ["Simon Rosner"]
__version__ = "2018.8.30"
__maintainer__ = "Simon Rosner"
__email__ = ""

error_log_file = "custom_command_error.log"

import subprocess
import datetime
import sqlite3
import time
import os
import shutil
#TODO revisit multiproccessing implementation
#import multiproccesing
from jinja2 import Environment, FileSystemLoader, Template
from functools import wraps

class V_API:
    def __init__(self, service, db, defaultBox):
        """
        Initialization requires
        the name of the service being used (ex: slack, hipchat),
        the sqlite3 database file path,
        and the name of the vagrant box
        """
        self.db = db    #path to sqlite3 database
        self.service = service  #name of chat service
        self.defaultBox = defaultBox    #name of default vagrant box
        self.myPath = os.path.abspath(os.path.realpath(__file__))
        self.parentPath = os.path.dirname(self.myPath)
        self.templatesPath = os.path.join(self.parentPath,'templates')
        blockedCommands = self.queryDB("Select * From BlockedCommands", [])
        self.blocked_commands = []  #list of blocked commands
        for b in blockedCommands:
            self.blocked_commands.append(b[0].lower())

    def _returnToDir(the_func):
        """
        Some functions change the working directory
        This decorator is used to ensure that
        the orig working dir is returned to
        """
        @wraps(the_func)
        def wrapTheFunction(*args, **kwargs):
            lastPath = os.getcwd()
            output = None
            #return whatever wrapped function returns
            try:
                output = the_func(*args, **kwargs)
            except:
                pass
            os.chdir(lastPath)
            if output != None:
                return output
        return wrapTheFunction

    def _log(the_func):
        """
        Records activity as generic records
        with the user noted as "System"
        """
        @wraps(the_func)
        def wrapper(*args, **kwargs):
            #function name
            eventDescription = the_func.__name__ + str(args[1:])
            #args[0] will always be self
            #   Kind of a hack but it works
            args[0].logEvent(eventDescription,[0])
            output = None
            try:
                output = the_func(*args, **kwargs)
            except:
                pass
            if output != None:
                return output
        return wrapper
        
    @_log    
    def addBlockedCommand(self, com):
        """
        Adds to the list of commands that
        will not be processed under any circumstances
        """
        self.queryDB("Insert into BlockedCommands(commands) values(?)",[com])
        self.blocked_commands.append(com.lower())
        
    @_log
    def adminCheck(self, uid):
        """
        Checks if ID is tied to admin user
        """
        adminQuery = "Select Count(*) from Admins "
        adminQuery += "where worksHere = 1 "
        adminQuery += "and ID like ?"
        queryArgs = [uid]
        numValidAdmins = self.queryDB(adminQuery,queryArgs)
        if numValidAdmins[0][0] >= 1:
            return True
        else:
            return False
        
    @_log
    def adminCheckThroughService(self, serviceID):
        """
        Checks if the serviceID provided
        is tied to an admin user
        """
        adminQuery = "Select Count(*) from ThirdPartyAccount "
        adminQuery += "Inner Join Admins on Admins.ID = ThirdPartyAccount.userID "
        adminQuery += "where worksHere = 1 "
        adminQuery += "and service like ? "
        adminQuery += "and serviceId like ?"
        queryArgs = [self.service, serviceID]
        numValidAdmins = self.queryDB(adminQuery,queryArgs)
        if numValidAdmins[0][0] >= 1:
            return True
        else:
            return False

    @_log #may be redundant here
    def buildThroughService(self, serviceID, box = None):
        """
        Create a new VM through a service
        """
        return self.buildVM(self.getUserID(serviceID),box);

    #@_log 
    @_returnToDir
    def buildVagrantFile(self, VMid):
        """
        Uses Jinja2 to build VagrantFile      
        """
        hostname = "nyc-vm-d" + str(VMid)
        #TODO ip generation
        ip = "xx.xx.x."
        data = {'ip': ip,
                'id': VMid,
                'hostname' : hostname}
        #copy over template files
        templateFiles = os.listdir(self.templatesPath)
        targetFolder = os.path.join(self.parentPath,str(VMid))
        for file in templateFiles:
            tempFile = os.path.join(self.templatesPath,file)
            shutil.copy2(tempFile,targetFolder)
        #get text of template file
        j2Location = os.path.join(self.templatesPath,'Vagrantfile.j2')
        with open(j2Location, 'r') as tFile:
            tText=tFile.read()
        #templatize it
        template = Template(tText)
        #fill out template with data
        rText = template.render(data)
        #write data into Vagrantfile
        with open('Vagrantfile', 'w') as vFile:
            vFile.write(rText)
        #put new Vagrantfile with other templateFiles
        dest = os.path.join(targetFolder,'Vagrantfile')
        shutil.move('Vagrantfile',dest)
        return data

    @_log 
    @_returnToDir
    def buildVM(self, userID, box=None):
        """
        Makes a VM and
        pairs it to a user
        """
        #build initial insert query
        query = "Insert into VM(hostname,ownerID,initDate,lastBuildDate,box) "
        query+= "Values(?,?,?,?,?)"
        curTime = round(time.time(),2)
        if box == None:
            box = self.defaultBox
        #know that any record in the db with this hostname is
        #   an instance of this method failing halfway through
        tempName = 'underConstruction' + str(curTime)
        queryArgs = [tempName, userID, curTime, curTime, box]
        self.queryDB(query, queryArgs)
        #get id of new VM record
        idQuery = "Select VM.ID from VM Where "
        idQuery+= "hostname like ? and "
        idQuery+= "ownerID = ? and "
        idQuery+= "initDate = ? and "
        idQuery+= "lastBuildDate = ? and "
        idQuery+= "box = ?"
        VMid = self.queryDB(idQuery, queryArgs)[0][0] #reuse args
        #made directory
        dirPath = os.path.join(self.parentPath,str(VMid))
        if not os.path.exists(dirPath):
            os.mkdir(dirPath, mode=0o777)
        #build the vagrant file
        data = self.buildVagrantFile(VMid)
        #take data and fill out the rest of the record
        finishQuery = "Update VM set hostname = ?, "
        finishQuery+= "ip = ?, "
        finishQuery+= "active = ? "
        finishQuery+= "Where VM.ID = ?"
        lastQuargs = [data["hostname"],data["ip"],1,data["id"]]
        errCheck = self.queryDB(finishQuery, lastQuargs)
        results = ""
        if 'failed' in errCheck:
            results = errCheck+' '
        #vagrant commands   
        #vagrant commands must be called from the dir where it lives
        os.chdir(dirPath)
        command1 = ['vagrant','up']
        #command2 = ['vagrant','provision']
        try:
            results+= str(subprocess.check_output(command1))
            #results+= str(subprocess.check_output(command2))
        except subprocess.CalledProcessError as e:
            results+= str(e)
        return results

    @_log 
    def claimUser(self, targetID, username, serviceID):
        """
        directly pair a user to a service account
        """
        query = "Insert into ThirdPartyAccount(userID, username, serviceID, service) "
        query+= "Values(?,?,?,?)"
        queryArgs = [targetID, username, serviceID, self.service]
        try:
            self.queryDB(query,queryArgs)
        except Exception as e:
            return e
        return None

    @_log 
    def claimByVM(self, targetVMid, serviceUsername, serviceID):
        """
        Pair VM to service account
        and pairs VM owner to account
        """
        VMquery = "Select VM.ownerID from VM where ID = ?"
        uid = self.queryDB(VMquery, [targetVMid])[0][0]
        
        query = "Insert into ThirdPartyAccount(userID, username, serviceID, service) "
        query+= "Values(?,?,?,?)"
        queryArgs = [uid, serviceUsername, serviceID, self.service]
        try:
            self.queryDB(query,queryArgs)
        except Exception as e:
            return e
        return None
    
    @_log
    def claimVM(self, targetVMid, userid):
        """
        Take over ownership of a VM
        Without pairing VM owner to account
        """
        query = "Update VM set ownerID = ? where ID = ?"
        quargs = [userid, targetVMid]
        try:
            self.queryDB(query,quargs)
        except Exception as e:
            return e
        return None

    @_log 
    @_returnToDir
    def cleanVMs(self):
        """
        Destroy VMs which belong to users
        who are not employed here
        """
        #get all VMs that are innactive or owned by defunct users
        cleanList = ""
        junkQuery = "Select VM.hostname, VM.ID from VM "
        junkQuery+= "join Users on User.ID = VM.ownerID "
        junkQuery+= "Where Users.worksHere = 0 "
        junkQuery+= "Or VM.active = 0"
        badVMs = self.queryDB(junkQuery, [])
        for vm in badVMs:
            cleanList = vm+' '
            self.destroyVM(vm)
        pruneCommand = ['vagrant','global-status','--prune']
        subprocess.check_output(pruneCommand)
        return cleanList.rstrip()    

    @_log 
    def createServiceUser(self, username, realID, serviceID):
        """
        Creates a service user and pairs it to a regular user
        These are needed to allow third party integration
        """
        query = "Insert into ThirdPartyAccount(userID,username,serviceID,service)"
        query += "Values(?,?,?,?)"
        queryArgs = [realID, username, serviceID, self.service]
        self.queryDB(query,queryArgs)

    @_log 
    def createUser(self, name):
        """
        Creates a user and returns their ID.
        It's a good idea to pair users
        to at least 1 third party service account.
        """
        query = "Insert into Users(name) Values(?)"
        queryArgs = [name]
        try:
            self.queryDB(query,queryArgs)
        except Exception as e:
            return e
        q2 = "Select ID FROM Users WHERE name like ? Order by desc Limit 1"
        newID = self.queryDB(q2,queryArgs)
        return newID

    @_log
    def deleteVM(self, VMid):
        """
        Destroy a VM and remove it's record from the database
        """
        output = self.destroyVM(VMid)
        query = "DELETE from VM where VM.ID = ?"
        self.queryDB(query,[VMid])
        return output

    @_returnToDir
    def destroyVM(self, VMid):
        """
        Destroys a VM and marks it as
        not active in database
        """
        removalQuery = "Update VM set active = 0 "
        removalQuery+= "Where VM.ID = ?"
        queryArgs = [VMid]
        self.queryDB(removalQuery,queryArgs)
        
        results = ''
        lastPath = os.getcwd()
        targetDir = os.path.join(self.parentPath,str(VMid))
        os.chdir(targetDir)
        destroyCommand = ['vagrant','destroy','-f'] #do not require prompt
        try:
            results+= subprocess.check_output(destroyCommand)
        except subprocess.CalledProcessError as e:
            results = e.output
        return results

    @_log 
    def getIDbyName(self, name):
        """
        Get user ID from name.
        Duplicate names may be problematic
        """
        query = "Select Users.name, Users.ID from Users where name like ?"
        quargs = [name]
        uid = self.queryDB(query, quargs)
        return uid

    @_log
    def getIDbyHostname(self, hostname):
        """
        Get VM ID from hostname
        Do not rely on hostnames being meaningful
        """
        query = "Select VM.hostname, VM.ID from VM where hostname like ?"
        quargs = [hostname]
        vmid = self.queryDB(query, quargs)
        return vmid

    @_log 
    def getLogsSince(self, pointInTime):
        """
        Returns all logged Events since a given
        date: UNIX timestamp
        """
        #I know this is ugly and violates PEP,
        #it is also more efficient than importing dateparser
        #everytime the API is instantiated
        import dateparser
        cleanTime = 0
        try:
            #This has the annoying side effect of rounding the decimal
            #revisit later?
            cleanTime = time.mktime(
                dateparser.parse(str(pointInTime))
                .timetuple())
        except Exception as e:
            return e.output
        query = "Select Events.description, Events.timestamp, "
        query+= "Users.name from Events "
        query+= "Join Actors on Events.ID = Actors.eventID "
        query+= "Join Users on Actors.actorID = Users.ID "
        query+= "Where Events.timestamp >= ? "
        query+= "ORDER BY timestamp ASC"
        quargs = [cleanTime]
        results = self.queryDB(query,quargs)
        return results

    @_log 
    def getUserID(self, serviceID):
        """
        Returns the true userID based on their serviceID
        Ex: passing a slackID and getting back a userID
        """
        query = "Select ID from ThirdPartyAccount "
        query+= "Inner Join Users on Users.ID = ThirdPartyAccount.userID "
        query+= "and service like ? "
        query+= "and serviceId like ?"
        queryArgs = [self.service, serviceID]
        userID = self.queryDB(query,queryArgs)
        return userID[0][0]

    @_log
    def getUserVMCount(self, userID):
        """
        Get the number of VMs registered
        to specified user
        """
        query = "Select COUNT(VM.ID) from VM "
        query+= "Where VM.ownerID = ?"
        queryArgs = [userID]
        vmCount = self.queryDB(query, queryArgs)[0][0]
        return vmCount

    @_log 
    def guessIDbyName(self, name):
        """
        Get user ID from closest name.
        Duplicate names may be problematic
        """
        wildname = '%' + name + '%'
        query = "Select Users.name, Users.ID from Users where name like ?"
        quargs = [wildname]
        guesses = self.queryDB(query, quargs)
        return guesses

    @_log 
    def listUsers(self):
        """
        Return a list of users who are currently employed here.
        """
        query = "Select name, ID From Users "
        query+= "Where worksHere = 1 "
        query+= "Order by name"
        users = self.queryDB(query, [])
        return users

    @_log 
    def listVMs(self):
        """
        Returns a list of active VMs
        """
        query = "Select VM.hostname, VM.ip, Users.name From VM "
        query+= "Left Join Users on VM.ownerID = Users.ID "
        query+= "Where VM.active IS NULL "
        query+= "OR VM.active = 1 "
        query+= "Order by VM.hostname"
        vms = self.queryDB(query, [])
        return vms

    #Never _log this - infinite loop 
    def logEvent(self, description, actors):
        """
        Creates a historical record of an event
        in the database and
        attaches relevant users to the record

        Note that all methods and their arguments
        will be recorded as generic events with the
        actor recorded as "System"
        This is done by the _log decorator

        For more detailed or specific logging
        the logEvent method must be used explicitly
        """
        eventInsert = "Insert into Events(description, timestamp) "
        eventInsert+= "Values(?,?)"
        theNow = str(round(time.time(),2))
        eventArgs = [str(description), theNow]
        self.queryDB(eventInsert, eventArgs)
        #get ID from new event
        getID = "Select Events.ID from Events "
        getID+= "Where Events.description like ? "
        getID+= "And Events.timestamp = ?"
        eventID = self.queryDB(getID, eventArgs)[0][0]
        #add actors
        for actor in actors:
            addActor = "Insert into Actors(eventID, actorID) "
            addActor+= "Values(?,?)"
            actArgs = [eventID, actor]
            self.queryDB(addActor, actArgs)

    @_log 
    def makeAdmin(self, myID, targetID):
        """
        Grant a user admin status
        """
        if (self.adminCheck(myID) == True
            or self.adminCheckThroughService(myID) == True):
            query = "Update Users Set isAdmin = 1 "
            query+= "Where Users.ID = ?"
            quargs = [targetID]
            self.queryDB(query, quargs)
            return True
        else:
            return False
        
    @_log 
    @_returnToDir
    def other(self, args):
        """
        executes any string as a VBoxManage command
        """
        results = None
        command = args.split(" ")
        try:
            results = subprocess.check_output(command).decode('ascii')
        except subprocess.CalledProcessError as e:
            results = e.output
            with open(error_log_file, 'a+') as error_log:
                time = str(datetime.datetime.now())
                error_log.write(time+": "+str(e)+'\n')
        return results

    @_log
    @_returnToDir
    def provisionVM(self, VMid):
        """
        Activated the provisioner for the VM
        """
        dirPath = os.path.join(self.parentPath,str(VMid))
        if not os.path.exists(dirPath):
            return "VM does not exist"
        results = ""
        #vagrant commands   
        #vagrant commands must be called from the dir where it lives
        os.chdir(dirPath)
        command = ['vagrant','provision']
        try:
            results+= str(subprocess.check_output(command))
        except subprocess.CalledProcessError as e:
            results+= str(e)
        return results      
    
    #Never _log this - infinite loop 
    def queryDB(self, query, quargs):
        """
        Shortcut method for querying the database. Requires
        query string
        list of arguments
        """
        connection = sqlite3.connect(self.db,isolation_level=None)
        c = connection.cursor()
        out = None
        try:
            c.execute(query,quargs)
            out = c.fetchall()
        except Exception as e:
            out = str(e)
        c.close
        return out

    @_log
    def reactivateUser(self, myID, targetID):
        """
        Reactivate a user
        """
        if self.adminCheck(myID) == True or self.adminCheckThroughService(myID) == True:
            rquery = "Update Users set worksHere = 1 "
            rquery+= "Where Users.ID = ?"
            rargs = [targetID]
            self.queryDB(rquery, rargs)
            return True
        else:
            return False
    
    @_log 
    @_returnToDir
    def rebuildVM(self, VMid):
        """
        destory and then build an existing VM
        """
        query = "Update VM Set active = 1 "
        query+= "Where VM.ID = ?"
        queryArgs = [VMid]
        self.queryDB(query,queryArgs)
        
        targetDir = os.path.join(self.parentPath,str(VMid))
        os.chdir(targetDir)
        destroyCommand = ['vagrant','destroy']
        destroyResults=''
        try:
            destroyResutls = str(subprocess.check_output(destroyCommand))
        except subprocess.CalledProcessError as de:
            destroyResutls+= str(de)
        command1 = ['vagrant','up']
        #command2 = ['vagrant','provision']
        reupResults = ''
        try:
            reupResults+= str(subprocess.check_output(command1))
            #reupResults+= str(subprocess.check_output(command2))
        except subprocess.CalledProcessError as e:
            reupResults+= str(e)
        reupResults = subprocess.check_output(reupCommand)
        results = destroyResults + "\n" + reupResults
        return results

    @_log
    def removeUser(self, myID, targetID):
        """
        Sets a user as not working here
        does not automatically deactivate
        their VMs
        """
        if self.adminCheck(myID) == True or self.adminCheckThroughService(myID) == True:
            rquery = "Update Users set worksHere = 0 "
            rquery+= "Where Users.ID = ?"
            rargs = [targetID]
            self.queryDB(rquery, rargs)
            return True
        else:
            return False
            
    #Security checks must be logged
    #   the lack of a check where there should be one is a red flag
    @_log
    def securityCheck(self, args):
        """
        Fill in the blocked_commands list with
        keywords  and commands which should not
        be run under any circumstances
        """
        command = args.split(" ")
        for c in command:
            if c.lower() in self.blocked_commands or command in self.blocked_commands:
                return False
        return True

    @_log 
    def userOwnsVM(self, uid, vid):
        """
        Check if a given user owns a given Vm
        """
        query = "Select count(*) from VM "
        query+= "Join Users on VM.ownerID = Users.ID "
        query+= "Where Users.ID = ? "
        query+= "and VM.ID = ?"
        queryArgs = [uid, vid]
        result = self.queryDB(query, queryArgs)[0][0]
        if result > 0:
            return True
        else:
            return False
    
