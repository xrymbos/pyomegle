from urllib import request, parse
from json import loads
from socket import timeout
import re

from threading import Thread

log_file = open("omegle.log", "w")

#This simply cuts the extra characters to isolate the ID
def fmtId( string ):
    return string[1:len( string ) - 1]

def getParamString(params):
    return bytes(parse.urlencode(params), 'utf-8')

def doNothing():
    return 0

def redden(string):
    return '\033[01;31m{}\033[01;30m'.format(string)

class DummyOmegleClient(object):
    def __init__(self):
        self.connected = False

    def showTyping(self):
        print("bot: stranger typing...")

    def sendMessage(self, message):
        print("bot: recieved {}".format(message))

    def printOutgoingMessages(self):
        print("bot: printing outgoing messages")

class ClientPool(object):
    def __init__(self, size):
        self.dummy_client = DummyOmegleClient()
        self.clients = []
        for i in range(size):
            client = OmegleClient(i, self.dummy_client)
            client.start()
            self.clients.append(client)

    def findFreeClient(self):
        #TODO: get lock on self.client
        for client in self.clients:
            if client.connected and not client.partner.connected:
                return client
        return self.dummy_client

class OmegleClient(Thread):
    def __init__(self, name="", partner=DummyOmegleClient(), pool=ClientPool(0)):
        Thread.__init__(self)
        self.messages = []
        self.name = name
        self.partner = partner
        self.connected = False

    def getNewPartner(self):
        self.partner = self.pool.findFreeClient()

    def printDebug(self, message, file=""):
        out = "{}: {}".format(self.name, message)
        if file != "":
            file.write(out + "\n")
        else:
            print(out)

    def run(self):
        self.omegleConnect()

    def showTyping(self):
        #Show the server that we're typing
        data = getParamString({"id" : self.id})
        typing = request.urlopen('http://omegle.com/typing', data)
        typing.close()

    def sendMessage(self, message):
        data = getParamString({"msg":message, "id":self.id})
        msgReq = request.urlopen('http://omegle.com/send', data)
        msgReq.close()

    def printOutgoingMessages(self):
        self.printDebug("printing outgoing messages")
        while len(self.messages) > 0:
            message = self.messages.pop(0)
            self.partner.sendMessage(message)
            self.printDebug("resent {}".format(message))

    def markConnected(self):
        if not self.connected:
            self.printDebug('Connected')
            self.connected = True
            self.partner.printOutgoingMessages()

    def markDisconnected(self):
        if self.connected:
            self.printDebug('Disconnected')
            self.connected = False

    def __receivedMessage(self, message):
        self.printDebug(redden(message))
        self.markConnected()
        if self.partner.connected:
            self.printOutgoingMessages()
            self.partner.sendMessage(message)
        else:
            self.printDebug("appending message {} for later".format(message))
            self.messages.append(message)

    #This is where all the magic happens, we listen constantly to the page for events
    def listenServer(self):
        while True:

            max_response_time = 10
            if self.connected:
                max_response_time = 120;
            try:
                site = request.urlopen(self.req, timeout=max_response_time)
            except Exception:
                break
            #We read the HTTP output to get what's going on
            full_response = site.read().decode('utf-8')
            if (full_response == 'null'):
                break
            self.printDebug("raw response: {}".format(full_response), log_file)
            rec = loads(full_response)[0]
            self.printDebug("got response {}".format(rec))

            if rec[0] == 'connected':
                self.markConnected()

            elif rec[0] == 'waiting':
                self.markDisconnected()

            elif rec[0] == 'typing':
                self.markConnected()
                self.partner.showTyping()

            elif rec[0] == 'strangerDisconnected':
                self.markDisconnected()
                #We start the whole process again
                self.omegleConnect()

            #When we receive a message, print it and execute the talk function
            elif rec[0] == 'gotMessage':
                self.markConnected()
                self.__receivedMessage(rec[1])

        self.omegleConnect()

#Here we listen to the start page to acquire the ID, then we "clean" the string to isolate the ID
    def omegleConnect(self):
        self.markDisconnected()
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

def fiddleMessage(message):
    result = message.lower()
    #replace m with f and vice versa
    #rep = {r"\bm\b": "f here", r"\bf\b": "m"}
    #reg_lookup = {"m":r"\bm\b", "f":r"\bf\b"}
    #robj = re.compile("|".join(rep.keys()))
    #result = robj.sub(lambda m: rep[reg_lookup[m.group(0)]], message)
    rep = {
        r"\bhi\b": "Good day!",
        r"\bi'm\b": "i am",
        r"\b\d*m\d*\b": "f here",
        r"\bhey\b": "Good day!",
        r"\b(penis|cock|dick)\b": "pussy",
        r"\bkik\b": "skype",
        r"\b(no|nah|nope)\b": "yesyes",
        r"\b(yes|yeah|yea)\b": "no",
        r"\byesyes\b": "yes",
        r"\basl\b": "Greetings! Whereabouts are you from?",
        r"\blol\b": "Ha ha ha! I do find that amusing!"}
    for search, replace in rep.items():
        result = re.sub(search, replace, result)
    return result


pool = ClientPool(5)

alice = OmegleClient(name = "Alice", pool=pool)
alice.start()
