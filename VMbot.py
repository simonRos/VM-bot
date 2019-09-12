#!/usr/bin/env python3
"""
Basic command and response slackbot
"""
__author__ = "Simon Rosner"
__credits__ = ["Simon Rosner"]
__version__ = "2018.8.30"
__maintainer__ = "Simon Rosner"
__email__ = ""

#   SLACK_BOT_TOKEN must be set as enviroment variable

import os
import time
import re
import sqlite3
#import multiproccesing
from slackclient import SlackClient
from vagrant_API import *

#instantiate Slack Client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
#myBot's user ID in Slack:
bot_id = None
bot_name = '@VMbot'

#constants
import constants
SERVICE = constants.SERVICE
DATABASE = constants.DATABASE
BOX = constants.BOX
RTM_READ_DELAY = constants.READ_DELAY
MENTION_REGEX = constants.MENTION_REGEX
MAX_VM_PER_USER = constants.MAX_VM_PER_USER

def get_user_name(uid):
    users = slack_client.api_call("auth.test")["users.list"]["members"]
    for user in users:
        if user["id"] == uid:
            return user["real_name"]

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def parse_bot_commands(slack_events):
    """
    Parse list of events coming from Slack RTM API to find bot commands.
    If bot command found: return tuple (command, event)
    Else: return (None, None)
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == bot_id:
                return message, event
    return None, None

def parse_direct_mention(message_text):
    """
    Finds a direct mention (at beginning) in message text
    returns user ID of mentioned person or None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains username. second ground contains rest
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def helpWith(com = None):
    """
    Return helptext for various commands
    """
    """
    Dict format:
    {command:[command,description,adminOnly]
    }
    """
    comDict = {}     
    comDict['build'] = ["Build new VM",
                        "Creates a new virtual machine assigned to the current user",
                        False]
    comDict['claim user'] = ["Claim user [user]",
                             "Pairs current service (slack,hipchat,etc) account to a VMbot account",
                             False]
    comDict['claim user with vm'] = ["Claim user with VM [vm]",
                                     "Pairs current service account to VMbot account which owns the specified virtual machine",
                                     False]
    comDict['claim vm'] = ["Claim VM [vm]",
                           "Changes virtual machine so that it is owned by current user",
                           False]
    comDict['deactivate'] = ["Remove user [user]",
                             "Marks a user as innactive. For use when a user leaves the company",
                             True]
    comDict['does own'] = ["Does [user] own [vm]",
                           "Checks if specified user owns specified virtual machine",
                           False]
    comDict['get user id'] = ["Get ID for user [user]",
                              "Get VMbot id for specified user",
                              False]
    comDict['get vm id'] = ["Get ID for VM [vm]",
                            "Get id for specified virtual machine",
                            False]
    comDict['guess user id'] = ["Guess ID for [user]",
                                "Enter a user name. If any names in the system are close, \
their full name and ID will be returned",
                                False]
    comDict['help'] = ["Help [admin|command| ]",
                       "Get help text for admin commands, commands like [command] or standard commands",
                       False]
    comDict['is admin'] = ["Is [user] an admin?",
                           "Checks if a specified user is an admin",
                           False]
    comDict['list users'] = ["List users",
                             "Lists all active users",
                             False]
    comDict['list vms'] = ["List virtual machines",
                           "List all active virtual machines",
                           False]
    comDict['provision'] = ["Provision vm [vm]",
                            "Rerun Virtual Machine setup without destroying it first. Some data may be destroyed anyway.",
                            False]
    comDict['register'] = ["Register",
                           "Creates a new VMbot account and pairs the current service user account to it",
                           False]
    comDict['rebuild'] = ["Rebuild vm [vm]",
                          "Rebuilds the specified virtual machine. Reverts it to it's default state",
                          False]
    comDict['my id'] = ["What is my ID?",
                        "Get the VMbot account id of the current user",
                        False]
    #admin commands
    comDict['block'] = ["Block command: [command]",
                        "Add a command to the list of blocked commands",
                        True]
    comDict['clean'] = ["Clean",
                        "Deactivates virtual machines owned by innactive users. Prunes vagrant global-list",
                        True]
    comDict['delete'] = ["Delete|Remove|Nuke VM [vm]",
                         "Destroy a virtual machine and remove it's record from the database. Do not use this unless absolutely nescessary",
                         True]
    comDict['logs'] = ["Get logs since [time]",
                       "Get event logs since specified datetime. \
It is recommended that you get logs directly from the database instead of running this command",
                       True]
    comDict['make admin'] = ["Make [user] admin",
                             "Grant the specified user full admin powers. This cannot be reversed through bot commands",
                             True]
    comDict['reactivate'] = ["Reactivate user [user]",
                             "Marks a removed user as active",
                             True]
    comDict['server'] = ["server [command]",
                         "Send a command directly to the server. \
It is recommended that you execute commands directly on the server instead of through this command",
                         True]
    comDict['vagrant'] = ["vagrant [command]",
                          "Sends a vagrant command directly to the server. Use with care",
                          True]
    helpText = ''
    for k,v in comDict.items():
        if com == None:
            if v[2] == False:
                helpText+= "*"+v[0]+"*\n\t"+v[1]+"\n"
        elif com.lower() == 'admin':       
            if v[2] == True:
                helpText+= "*"+v[0]+"*\n\t"+v[1]+"\n"
        elif com is not None:
            if com.lower() in k:
                helpText+= "*"+v[0]+"*\n\t"+v[1]+"\n"               
    return helpText
            
def handle_command(command, event):
    """
    Executes bot command if known
    """
    command = str(command)
    # Default response is help text for user
    default_response = "Command: *" + command + "* not recognized."

    #instantiate vagrant_api
    v = V_API(SERVICE, DATABASE, BOX)

    isAdmin = v.adminCheckThroughService(event["user"])
    notAdmin= "Only admins can do that."

    # Finds and executes the given command
    response = None
    # Implement Commands Here!
    if v.securityCheck(command) == False:
        response = "Security alert: *" +args+ "* may not be run :warning:"
    else:
        #addBlockedCommand
        if re.match(r'block command: (.*)',command, re.I)is not None:
            if isAdmin:
                try:
                    blockCom = re.match(r'block command: (.*)',command, re.I).group(1)
                    v.addBlockedCommand(blockCom)
                    response = blockCom + " has been permanently blocked"
                except Exception as e:
                    response = "Something went wrong: "+str(e)
            else:
                response = notAdmin     
        #adminCheck
        elif re.match(r'(are|am) I (an admin|admin).*', command, re.I)is not None:
            if isAdmin:
                response = "You are an admin"
            else:
                response = "You are not an admin"
        elif re.match(r'is (.*) an admin.*', command, re.I)is not None:
            userInQuestion = re.match(r'is (.*) an admin.*', command, re.I).group(1)
            userIqId = userInQuestion
            if is_number(userInQuestion) == False:
                try:
                    userIqId = v.getIDbyName(userInQuestion)[0][1]
                except Exception as e:
                    response = "Something went wrong: "+string(e)
            if v.adminCheck(userIqId) == True:
                response = userInQuestion + " is an admin"
            else:
                response = userInQuestion + " is not an admin"
        #build
        elif re.match(r'build new.*', command, re.I) is not None:
            vmCount = v.getUserVMCount(event["user"])
            tempResponse = "You have "+str(vmCount)+" virtual machines already assigned to you.\n"
            tempResponse+= "The maximum per user is: "+str(MAX_VM_PER_USER)+"\n"
            if vmCount > MAX_VM_PER_USER:
                tempResponse+= "Another virtual machine cannot be built at this time.\n"
                response = tempResponse
            else:
                tempResponse += "Building virtual machine..."
                slack_client.api_call(
                    "chat.postMessage",
                    channel=event["channel"],
                    thread_ts=event["ts"],
                    text=tempResponse
                    )
                try:
                    results = v.buildThroughService(event["user"])
                    response = results
                    print(results)
                except Exception as e:
                    response = "Something went wrong: "+str(e)
        #claim user
        elif re.match(r'claim user (.*)',command,re.I)is not None:
            targetUserID = re.match(r'claim user with id (.*)',command,re.I).group(1)
            if is_number(targetUser) == False:
                targetUserID = v.getIDbyName(targetUserID)
            worked = v.claimUser(targetUserID,
                                   get_user_name(event["user"]),
                                   event["user"])
            if worked == True:
                response = "You have succesfully paired your "
                + v.service + " account with your VMbot account"
            else:
                response = "Something went wrong"
        #claim by VM
        elif re.match(r'claim user with vm (.*)',command, re.I)is not None:
            targetVMID = re.match(r'claim user with vm (.*)',command,re.I).group(1)
            if is_number(targetUser) == False:
                targetUserID = v.getIDbyHostname(targetUserID)
            worked = v.claimUser(targetVMID,
                                   get_user_name(event["user"]),
                                   event["user"])
            if worked == True:
                response = "You have succesfully claimed VM:"
                + targetVMID + " and paired your "
                + v.service + " account with your VMbot account"
            else:
                response = "Something went wrong"
        #claim VM
        elif re.match(r'claim vm (.*)',command, re.I)is not None:
            targetVMID = re.match(r'claim vm (.*)',command,re.I).group(1)
            if is_number(targetUser) == False:
                targetUserID = v.getIDbyHostname(targetUserID)
            worked = v.claimVM(targetVMID,
                               v.getUserID(event['user']))
            if worked == True:
                response = "You have succesfully claimed VM:"
                + targetVMID
            else:
                response = "Something went wrong"
        #clean
        elif re.match(r'clean.*',command,re.I)is not None:
            if isAdmin:
                response = "The following are inactive VMs: "+str(v.cleanVMs())
                response+="\nTo remove them from the database, run the *delete* command"
            else:
                response = notAdmin
        #createUser
        elif re.match(r'register.*',command,re.I)is not None:
            if v.getUserID(event["user"]) is None:
                v.createServiceUser(get_user_name(event["user"]),
                                    v.createUser(event["user"]),
                                    event["user"])
            else:
                response = "This "+v.service+" account is already registered"
        #delete/remove
        elif re.match(r'(remove|delete|nuke) vm (.*)',command,re.I)is not None:
            if isAdmin:
                target = re.match(r'(remove|delete) vm (.*)',command,re.I).group(2)
                if is_number(targe) == False:
                    target = v.getIDbyHostname(target)
                response = v.deleteVM(target)
            else:
                response = notAdmin
        #getIDbyName
        elif re.match(r'.*id (of|for) user (.*)',command,re.I)is not None:
            name = re.match(r'.*id (of|for) user (.*)',command,re.I).group(2)
            try:
                user = v.getIDbyName(name)
                response = "ID for "+user[0][0]+" is "+str(user[0][1])
            except Exception as e:
                response = "Cannot find user. Error: "+str(e)
        #getIDbyHostname
        elif re.match(r'.*id (of|for) vm (.*)',command,re.I)is not None:
            hostname = re.match(r'.*id (of|for) vm (.*)',command,re.I).group(2)
            try:
                vm = v.getIDbyHostname(hostname)
                if len(vm) >= 1:
                    response = "ID for "+vm[0][0]+" is "+str(vm[0][1])
                else:
                    response = "Cannot find virtual machine"
            except Exception as e:
                response = "Cannot find virtual machine. Error: "+str(e)
        #getLogsSince
        elif re.match(r'.*logs since (.*)',command,re.I)is not None:
            theTime = re.match(r'.*logs since (.*)',command,re.I).group(1)
            print(theTime)
            logs = v.getLogsSince(theTime)
            print(logs)
            response = logs
        #getUserID
        elif re.match(r'what is my id.*',command,re.I)is not None:
            yourID = v.getUserID(event["user"])
            if yourID is not None:
                response = "Your ID is "+yourID
            else:
                response = "You do not have an ID yet"
        #guessIDbyName
        elif re.match(r'.*guess id (of|for) (.*)',command,re.I)is not None:
            theID = re.match(r'.*guess id (of|for) (.*)',command,re.I).group(2)
            guesses = v.guessIDbyName(theID)
            if len(guesses) >= 1:
                for guess in guesses:
                    response = str(guess[0])
                    response +='\t-\t_'
                    response += str(guess[1])
                    response +='_\n'
            else:
                response = "I need another hint. Try guessing a shorter name"
        #help
        elif command.lower().startswith('help'):
            #strip out the word 'help'
            if len(command) <= 5:
                response = helpWith()
            else:
                response = helpWith(command.split(' ',1)[1])
        #listUsers
        elif re.match(r'list users',command,re.I)is not None:
            users = v.listUsers()
            response = ""
            for user in users:
                response += user[0]
                response +='\t-\t_'
                response += str(user[1])
                response +='_\n'
        #listVMs
        elif re.match(r'list (vms|virtual machines)',command,re.I)is not None:
            vms = v.listVMs()
            response = ""
            for vm in vms:
                response += "*"
                response += vm[0]
                response += "*\n\t"
                response += vm[1]
                response += "\n\t"
                response += vm[2]
                response += '\n'
        #makeAdmin
        elif re.match(r'make (.*) an admin.*',command,re.I)is not None:
            if isAdmin:
                newAdmin = re.match(r'make (.*) an admin.*',command,re.I).group(1)
                if is_number(newAdmin) == False:
                    newAdmin = v.getIDbyName(newAdmin)
                if v.makeAdmin(v.getUserID(event['user']),newAdmin) == True:
                    response = newAdmin + " is now an Admin"
                else:
                    response = "Something went wrong"
            else:
                response = notAdmin
        #provision
        elif re.match(r'provision vm (.*)',command,re.I)is not None:
            vmInQuestion = re.match(r'provision vm (.*)',command,re.I).group(1)
            if is_number(vmInQuestion) == False:
                vmInQuestion = v.getIDbyHostname(vmInQuestion)
            uid = v.getUserID(event['user'])
            if isAdmin or v.userOwnsVM(uid,vmInQuestion):
                slack_client.api_call(
                "chat.postMessage",
                channel=event["channel"],
                thread_ts=event["ts"],
                text="Provisioning virtual machine..."
                )
                result = v.provisionVM(vmInQuestion)
                if result == True:
                    response = "VM with id: " + vmInQuestion + " has been provisioned"
                else:
                    response = "Something went wrong
            else:
                response = notAdmin
                
        #reactivate
        elif re.match(r'(reactivate|reinstate|revive) user (.*)',command,re.I)is not None:
            if isAdmin:
                userInQuestion = re.match(r'(reactivate|reinstate|revive) user (.*)',command,re.I).group(2)
                if is_number(userInQuestion) == False:
                    userInQuestion = v.getUserID(userInQuestion)
                result = v.reactivateUser(event['user'],userInQuestion)
                if result == True:
                    response = userInQuestion + " has been reactivated"
                else:
                    response = "Something went wrong"
            else:
                response = notAdmin
        #rebuild
        elif re.match(r'rebuild (vm|virtual machine) (.*)',command,re.I)is not None:
            vmInQuestion = re.match(r'rebuild (vm|virtual machine) (.*)',command,re.I).group(2)
            if is_number(vmInQuestion) == False:
                vmInQuestion = v.getIDfromHostname(vmInQuestion)
            user = v.getUserID(event['user'])
            if v.userOwnsVm(user,vmInQuestion) == True or isAdmin:
                response = v.rebuildVM(vmInQuestion)
            else:
                response = "You should not rebuild other users' virtual machines"
        #removeUser
        elif re.match(r'(deactivate|delete|remove) user (.*)',command,re.I)is not None:
            if isAdmin:
                userInQuestion = re.match(r'(deactivate|delete|remove) user (.*)',command,re.I).group(2)
                if is_number(userInQuestion) == False:
                    userInQuestion = v.getUserID(userInQuestion)
                result = v.removeUser(event['user'],userInQuestion)
                if result == True:
                    response = userInQuestion + " has been removed"
                else:
                    response = "Something went wrong"
            else:
                response = notAdmin
        #server
        #This command will not work as intended if bot is installed on Windows
        elif command.lower().startswith('server'):
            if isAdmin:
                #strip out the word 'server'
                response = v.other(command.split(' ',1)[1])
            else:
                response = "Only admins may use vagrant commands."
        #vagrant
        elif command.lower().startswith('vagrant'):
            if isAdmin:
                response = v.other(command)
            else:
                response = "Only admins may use vagrant commands."
        elif re.match(r'(Does|Do) (.*) (own|have|use|control) (.*)',command,re.I)is not None:
            inString = re.match(r'Does (.*) (own|have|use|control) (.*)',command,re.I)
            userInQuestion = inString.group(2)
            if is_number(userInQuestion) == False:
                if inString.group(userInQuestion) == "I":
                    userInQuestion = v.getUserID(event['user'])
                else:
                    userInQuestion = v.getUserID(userInQuestion)
            VMinQuestion = inString.group(4)
            if is_number(VMinQuestion) == False:
                VMinQuestion = v.getIDbyHostname(VMinQuestion)
            response = v.userOwnsVM(userInQuestion,VMinQuestion)
                    
    # Sends the response back to the channel
    slack_client.api_call(
            "chat.postMessage",
            channel=event["channel"],
            thread_ts=event["ts"],
            text=response or default_response
            )

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("VM bot connected and running.")
        # Read bot's ID by calling 'auth.test'
        bot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            try:
                command, event = parse_bot_commands(slack_client.rtm_read())
                if command:
                    handle_command(command, event)
                time.sleep(RTM_READ_DELAY)
            except Exception as ex:
                print(ex)
    else:
        print("Connection failed. Exception traceback printed above.")
