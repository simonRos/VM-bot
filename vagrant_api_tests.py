#!/usr/bin/env python3
"""
unit tests for vagrant_API.py
"""
__author__ = "Simon Rosner"
__credits__ = ["Simon Rosner"]
__version__ = "2018.8.23"
__maintainer__ = "Simon Rosner"
__email__ = ""

#add vagrant_API.py parent directory to path for importing
import sys
import unittest
import sqlite3
import shutil
import os
import time
from vagrant_API import *

SERVICE = "testChat"
DB = "testDB.db"
BOX = "ubuntu/trusty32"

class settings(unittest.TestCase):
    """
    setup and teardown for all test classes
    """
    @classmethod
    def setUpClass(cls):
        shutil.copy2("testDBBackup.db","testDB.db")
        cls.v = V_API(SERVICE, DB, BOX)

    @classmethod
    def tearDownClass(cls):
        os.remove("testDB.db")
        cls.v = None
    
class TestAdminChecks(settings):
    """
    Test methods relating to admin checks
    and admin assigning
    """   
    def test_adminCheck(self):
        """
        Check if admins can correctly be identified
        """
        self.assertTrue(self.v.adminCheck(75))
        self.assertFalse(self.v.adminCheck(74))
        
    def test_adminCheckThroughService(self):
        """
        Check if admins can correctly be identified through service
        """
        self.assertTrue(self.v.adminCheckThroughService('abc123'))
        self.assertFalse(self.v.adminCheckThroughService('xyz789'))
        
    def test_makeAdmin(self):
        """
        Check ability to grant admin rights.
        Only admins should be able to grant admin.
        """
        self.assertFalse(self.v.makeAdmin(76,77))
        self.assertFalse(self.v.adminCheck(77))
        self.assertTrue(self.v.makeAdmin(75,74))
        self.assertTrue(self.v.adminCheck(74))

class TestBuild(settings):
    """
    Test methods relating to building VMs
    """
    def test_buildThroughService(self):
        #essentially an alias for buildVM
        #if buildVM and getUserID work this will work
        pass
    def test_buildVagrantFile(self):
        #must run properly for builds to run
        pass
    def test_buildVM(self):
        #this cannot accurately be tested without a Vsphere cluster
        results = self.v.buildVM(78)
        #print(results)
        vmList = self.v.listVMs()
        #print(vmList)
        self.assertTrue(('nyc-vm-d80', '10.20.6.', 'Test McTester') in vmList)
   
    def test_destroyVM(self):
        """
        Test ability to destroy a VM
        MUST BE RUN SEQUENTIALLY
        """
        results = self.v.destroyVM(80)
        #print(results)
        vmList = self.v.listVMs()
        self.assertFalse(('nyc-vm-d80', '10.20.6.', 'Test McTester') in vmList)

    def test_rebuildVM(self):
        """
        MUST BE RUN SEQUENTIALLY
        """
        results = self.v.rebuildVM(80)
        #print(results)
        vmList = self.v.listVMs()
        #print(vmList)
        self.assertTrue(('nyc-vm-d80', '10.20.6.', 'Test McTester') in vmList)
        shutil.rmtree(os.path.join(self.v.parentPath, str(80)))

    def test_deleteVM(self):
        """
        Test ability to remove VM
        from the database entirely
        """
        vmList = self.v.listVMs()
        self.assertTrue(('nyc-vm-d80', '10.20.6.', 'Test McTester') in vmList)
        vmid = self.v.getIDbyHostname("nyc-vm-d80")
        self.v.deleteVM(vmid)
        vmList = self.v.listVMs()
        self.assertFalse(('nyc-vm-d80', '10.20.6.', 'Test McTester') in vmList)
        

class TestClaims(settings):
    """
    Test methods relating to claiming user ownership
    """
    def test_claimUser(self):
        self.assertIsNone(self.v.claimUser(78, 'J.J.', 'jq456'))
        q = "SELECT Users.ID, ThirdPartyAccount.username, ThirdPartyAccount.serviceID "
        q+= "FROM Users "
        q+= "INNER JOIN ThirdPartyAccount "
        q+= "ON Users.ID = ThirdPartyAccount.userID "
        q+= "And ThirdPartyAccount.service LIKE 'testChat'"
        testChatUserList = self.v.queryDB(q,[])
        self.assertTrue((78,'J.J.','jq456') in testChatUserList)
        
    def test_claimByVM(self):
        claim = self.v.claimByVM(79, 'Tester007','test007')
        self.assertIsNone(claim)
        q = "SELECT VM.ownerID, ThirdPartyAccount.username, ThirdPartyAccount.serviceID "
        q+= "FROM VM "
        q+= "INNER JOIN ThirdPartyAccount "
        q+= "ON VM.ownerID = ThirdPartyAccount.userID "
        q+= "And ThirdPartyAccount.service LIKE 'testChat'"
        testChatUserList = self.v.queryDB(q,[])
        self.assertTrue((78,'Tester007','test007') in testChatUserList)
        
    def test_userOwnsVM(self):
        self.assertTrue(self.v.userOwnsVM(60,60))
        self.assertFalse(self.v.userOwnsVM(60,1))

    def test_claimVM(self):
        self.assertFalse(self.v.userOwnsVM(60,78))
        self.assertIsNone(self.v.claimVM(78,60))
        self.assertTrue(self.v.userOwnsVM(60,78))
        
class TestClean(settings):
    """
    Test ability to remove abandonded VMs
    """
    def cleanVMs(self):
        cleaned = self.v.cleanVMs()
        self.assertTrue((77,) in cleaned)

class TestIdentity(settings):
    """
    Test methods relating to
    determining user identity
    """
    def test_getIDbyName(self):
        """
        Test ability to identify users by name
        """
        self.assertEqual(self.v.getIDbyName("Test McTester")[0][1],78)

    def test_getIDbyHostname(self):
        """
        Test ability to identify VM by hostname
        """
        self.assertEqual(self.v.getIDbyHostname("test-vm-02")[0][1],79)
        
    def test_getUserID(self):
        """
        Test ability to identify users by serviceID
        """
        self.assertEqual(self.v.getUserID("test000"),78)
        
    def test_guessIDbyName(self):
        """
        Test ability to return user info
        based on approximate name
        """
        self.assertTrue(4 <= len(self.v.guessIDbyName("est")))
        
    def test_listUsers(self):
        """
        Test ability to list all users
        who currently work here
        """
        uList = self.v.listUsers()
        self.assertFalse(("Awol Absentpants",82) in uList)
        self.assertTrue(("Test McTester", 78) in uList)
        
    def test_listVMs(self):
        """
        Test ability to list all VMs
        Which may be active
        """
        vmList = self.v.listVMs()
        self.assertFalse(('junk-VM-01', '10.20.6.202', 'Test McTester') in vmList)
        self.assertTrue(('owned-by-non-employee', '10.20.6.105', 'E. X. Employee') in vmList)
        self.assertTrue(('nyc-cbmweb-d31', '10.20.6.231', 'Simon Rosner') in vmList)

    def test_createServiceUser(self):
        """
        Test ability to create service users
        """
        uid = self.v.getIDbyName("Test McTester")[0][1]
        self.v.createServiceUser("TTT",uid,"Ten10Ten")
        servUList = self.v.queryDB("Select * from ThirdPartyAccount",[])
        self.assertTrue((uid,"TTT","Ten10Ten","testChat") in servUList)

    def test_createUser(self):
        """
        Test ability to create new internal user
        """
        uList = self.v.queryDB("Select name from Users",[])
        self.assertFalse(("Anne Anyone",) in uList)
        self.v.createUser("Anne Anyone")
        uList = self.v.listUsers()
        AAid = self.v.getIDbyName("Anne Anyone")[0][1]
        self.assertTrue(("Anne Anyone",AAid) in uList)

    def test_removeUser(self):
        """
        Test ability to remove user
        """
        self.v.createUser("Super Temp")
        STid = self.v.getIDbyName("Super Temp")[0][1]
        #0 is the System's User id
        self.assertTrue(self.v.removeUser(0,STid))
        uList = self.v.listUsers()
        self.assertFalse(("Super Temp",STid) in uList)

    def test_reactivateUser(self):
        """
        Test ability to reactivate user
        """
        self.v.createUser("Mid Temp")
        uid = self.v.getIDbyName("Mid Temp")[0][1]
        self.assertTrue(self.v.removeUser(0,uid))
        self.assertTrue(self.v.reactivateUser(0,uid))
        uList = self.v.listUsers()
        self.assertTrue(("Mid Temp",uid) in uList)
        

class TestLogging(settings):
    """
    Test ability to log various events
    """
    def test_genericLogging(self):
        """
        Test that events are being automatically recorded
        """
        time.sleep(1)
        start_time = round(time.time(),2)
        #some operations
        self.v.listUsers()
        self.v.listVMs()
        self.v.guessIDbyName("Simon")
        self.v.getIDbyHostname("test-vm-01")
        query = "Select Events.description, Events.timestamp "
        query+= "From Events "
        query+= "Where Events.timestamp >= ? "
        query+= "ORDER BY timestamp ASC"
        res = self.v.queryDB(query,[start_time])
        self.assertTrue(res[0][0] == "listUsers()")
        self.assertTrue(res[1][0] == "listVMs()")
        self.assertTrue(res[2][0] == "guessIDbyName('Simon',)")
        self.assertTrue(res[3][0] == "getIDbyHostname('test-vm-01',)")
        timesAreCorrect = True
        for event in res:
            if event[1] < start_time:
                timesAreCorrect = False
        self.assertTrue(timesAreCorrect)
        actors = self.v.queryDB("select * from Actors",[])
        self.assertTrue(len(actors) >= 4)
        for actor in actors:
            self.assertEqual(actor[1],0)
        
    def test_eventLogging(self):
        time.sleep(1)
        start_time2 = round(time.time(),2)
        self.v.logEvent("This is a test event", [0])
        query = "Select Events.description, "
        query+= "Users.name from Events "
        query+= "Join Actors on Events.ID = Actors.eventID "
        query+= "Join Users on Actors.actorID = Users.ID "
        query+= "Where Events.timestamp >= ? "
        query+= "ORDER BY timestamp ASC"
        res = self.v.queryDB(query,[start_time2])
        self.assertTrue(("This is a test event","System") in res)
        
    def test_getLogsSince(self):
        time.sleep(1)
        start_time3 = round(time.time(),2)
        self.v.logEvent("This is another test event", [0])
        res = self.v.getLogsSince(start_time3)
        self.assertTrue(res[0][0]=="This is another test event")
        self.assertTrue(res[0][2]=="System")
        #a record will be made of the call to .getLogsSince()
        self.assertTrue(res[1][2]=="System")

class TestSecurity(settings):
    """
    Test ability of API to absolutely
    block the use of hazardous commands
    """
    def test_addBlockedCommand(self):
        """
        Test ability to add commands
        to list of blocked commands
        """
        self.assertTrue(self.v.securityCheck("Nuke everything"))
        self.v.addBlockedCommand("nuke")
        self.assertFalse(self.v.securityCheck("Nuke everything"))
        
    def test_securityCheck(self):
        """
        Test ability to detect and block
        hazardous commands
        """
        self.assertFalse(self.v.securityCheck("DROP TABLES *"))

class TestUtilities(settings):
    """
    Test internal use methods
    """
    def test_other(self):
        """
        Test ability to pass commands,
        specifically vagrant commands,
        directly to the server the API
        lives on
        """
        res = self.v.other("vagrant -h")[:40]
        self.assertEqual("Usage: vagrant [options] <command> [<arg",res)

    def test_queryDB(self):
        """
        Test ability to query DB
        """
        query = "Select VM.hostname, VM.ip, Users.name From VM "
        query+= "Left Join Users on VM.ownerID = Users.ID "
        query+= "Where VM.active IS NULL "
        query+= "OR VM.active = 1 "
        query+= "Order by VM.hostname"
        self.assertEqual(self.v.listVMs(), self.v.queryDB(query, []))
