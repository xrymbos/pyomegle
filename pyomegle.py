from urllib import request, parse
from json import loads
from socket import timeout
import re

from threading import Thread

#This simply cuts the extra characters to isolate the ID
def fmtId( string ):
    return string[1:len( string ) - 1]

def getParamString(params):
    return bytes(parse.urlencode(params), 'utf-8')

def doNothing():
    return 0

class OmegleClient(Thread):
    def __init__(self, message_callback = print, typing_callback = doNothing, name=""):
        Thread.__init__(self)
        self.messages = []
        self.message_callback = message_callback
        self.name = name

    def printDebug(self, message):
        print("{}: {}".format(self.name, message))

    def run(self):
        self.omegleConnect()

    def showTyping(self):
        #Show the server that we're typing
        data = getParamString({"id" : self.id})
        typing = request.urlopen('http://omegle.com/typing', data)
        typing.close()


    def sendMessage(self, message):
        self.printDebug("sending message {} to {}".format(message, self.name))
        if self.connected:
            #Send the string to the stranger ID
            data = getParamString({"msg":message, "id":self.id})
            msgReq = request.urlopen('http://omegle.com/send', data)

            #Close the connection
            msgReq.close()
        else:
            self.printDebug("queuing message {} to {} for later".format(message, self.name))
            self.messages.append(message)

    def printQueuedMessages(self):
        while len(self.messages) > 0:
            message = self.messages.pop()
            self.sendMessage(message)
            self.printDebug("resent {}".format(message))

    #This is where all the magic happens, we listen constantly to the page for events
    def listenServer(self):
        while True:

            max_response_time = 10
            if self.connected:
                max_response_time = 30;
            try:
                site = request.urlopen(self.req, timeout=max_response_time)
            except Exception:
                break
            #We read the HTTP output to get what's going on
            full_response = site.read().decode('utf-8')
            rec = loads(full_response)[0]
            self.printDebug("got response {}".format(rec))

            if rec[0] == 'connected':
                self.connected = True
                self.printQueuedMessages()
                self.printDebug('Found one')
                self.printDebug('other info: {}'.format(full_response))

            elif rec[0] == 'waiting':
                self.connected = False

            elif rec[0] == 'typing':
                self.connected = True
                self.printQueuedMessages()
                self.typing_callback()

            elif rec[0] == 'strangerDisconnected':
                self.printDebug('He is gone')
                #We start the whole process again
                self.omegleConnect()

            #When we receive a message, print it and execute the talk function
            elif rec[0] == 'gotMessage':
                self.connected = True
                self.printQueuedMessages()
                self.message_callback(rec[1])
                #print(rec[16:len( rec ) - 2])
        self.omegleConnect()

#Here we listen to the start page to acquire the ID, then we "clean" the string to isolate the ID
    def omegleConnect(self):
        self.connected = False
        data = parse.urlencode({'lang':'en', 'spid':'', 'rcs':'1'})#, 'topics':'''["sports"]'''})
        self.printDebug(data)
        site = request.urlopen('http://omegle.com/start?'+data)
        response = site.read().decode('utf-8')
        self.printDebug("site response: {}".format(response))
        self.id = fmtId(response)
        data = getParamString({'id':self.id})
        self.req = request.Request('http://omegle.com/events', data)
        self.printDebug('\033[01;31mSearching...\033[01;30m')

        #Then we open our ears to the wonders of the events page, where we know if anything happens
        #We have to pass two arguments: the ID and the events page.
        self.listenServer()


alice = OmegleClient(name = "Alice")
bob = OmegleClient(name = "Bob")

def fiddleMessage(message):
    message = message.lower()
    #replace m with f
    rep = {r"\bm\b": "f here", r"\bf\b": "m"}
    reg_lookup = {"m":r"\bm\b", "f":r"\bf\b"}
    robj = re.compile("|".join(rep.keys()))
    result = robj.sub(lambda m: rep[reg_lookup[m.group(0)]], message)
    rep = {
        r"\bhi\b": "Good day!",
        r"\bhey\b": "Good day!",
        r"\bkik\b": "naked pictures",
        r"\basl\b": "Greetings! Whereabouts are you from?",
        r"\blol\b": "Ha ha ha! I do find that amusing!"}
    for search, replace in rep.items():
        result = re.sub(search, replace, result)
    return result

def printAlice(message):
    message = fiddleMessage(message)
    print("\033[01;31mAlice: {}\033[01;30m".format(message))
    bob.sendMessage(message)

def printBob(message):
    message = fiddleMessage(message)
    print("\033[01;31mBob: {}\033[01;30m".format(message))
    alice.sendMessage(message)

def typingAlice():
    bob.showTyping()

def typingBob():
    alice.showTyping()

alice.message_callback = printAlice
bob.message_callback = printBob
alice.typing_callback = typingAlice
bob.typing_callback = typingBob

alice.start()
bob.start()

#while True:
    #alice.sendMessage(input(">"))
