import urllib
import httplib2 as http
import json
import socket

from threading import Thread

#This simply cuts the extra characters to isolate the ID
def fmtId( string ):
    return string[1:len( string ) - 1]

def getParamString(params):
    return bytes(urllib.parse.urlencode(params), 'ascii')

class OmegleClient(Thread):
    def __init__(self, message_callback = print):
        Thread.__init__(self)
        self.message_callback = message_callback

    def run(self):
        self.omegleConnect()

#Talk to people
    def sendMessage(self, message):

        #Show the server that we're typing
        data = getParamString({"id" : self.id})
        typing = urllib.request.urlopen('http://omegle.com/typing', data)
        typing.close()

        #Send the string to the stranger ID
        data = getParamString({"msg":message, "id":self.id})
        msgReq = urllib.request.urlopen('http://omegle.com/send', data)

        #Close the connection
        msgReq.close()


#This is where all the magic happens, we listen constantly to the page for events
    def listenServer(self):
        while True:

            try:
                site = urllib.request.urlopen(self.req, timeout=10)
            except socket.timeout:
                break
            #We read the HTTP output to get what's going on
            rec = json.loads(site.read().decode('ascii'))[0]

            if rec[0] == 'connected':
                print('Found one')
                #print(self.id)
                #Since this isn't threaded yet, it executes the talk function (yeah, turn by turn)
                
            elif rec[0] == 'strangerDisconnected':
                print('He is gone')
                #We start the whole process again
                self.omegleConnect()

            #When we receive a message, print it and execute the talk function            
            elif rec[0] == 'gotMessage':
                self.message_callback(rec[1])
                #print(rec[16:len( rec ) - 2])
        self.omegleConnect()

#Here we listen to the start page to acquire the ID, then we "clean" the string to isolate the ID
    def omegleConnect(self):
        self.messages = []
        site = urllib.request.urlopen('http://omegle.com/start')
        self.id = fmtId( site.read() )
        print(self.id)
        data = getParamString({'id':self.id}) #, 'topics':'''["test"]'''})
        self.req = urllib.request.Request('http://omegle.com/events', data)
        print('Gotta find one')

        #Then we open our ears to the wonders of the events page, where we know if anything happens
        #We have to pass two arguments: the ID and the events page.
        self.listenServer()


alice = OmegleClient()
bob = OmegleClient()

def printAlice(message):
    print("Alice: {}".format(message))
    bob.sendMessage(message)

def printBob(message):
    print("Bob: {}".format(message))
    alice.sendMessage(message)

alice.message_callback = printAlice
bob.message_callback = printBob

alice.start()
bob.start()

#while True:
    #alice.sendMessage(input(">"))
