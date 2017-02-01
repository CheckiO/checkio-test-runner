import json
import sys

from twisted.internet import  reactor, protocol
from twisted.application import service, internet
from twisted.protocols import basic

import settings




class EchoProtocol(basic.LineReceiver):
    """
        @attributes:
            connection_id of current instance
            prefix of process

    """
    delimiter = b'\0'
    MAX_LENGTH = 10000000
    connection_id = None
    prefix = '-'

    def test_get_send(self):
        command, self.test_expect = settings.TEST_COMMAND_PIPELINE.pop(0)
        return command

    def test_has_more(self):
        return len(settings.TEST_COMMAND_PIPELINE)

    def connectionMade(self):
        print('Connected')

    def lineReceived(self, line):
        line = line.decode('utf8')
        print('RECEIVED:{}'.format(line))
        data = json.loads(line)
        looking_method = 'do_' + data['do']

        return getattr(self, looking_method)(data)

    def do_connect(self, data):
        self.sendData(self.test_get_send())

    def do_done(self, data):
        if self.test_expect is not None:
            assert data == self.test_expect

        if self.test_has_more():
            self.sendData(self.test_get_send())
        else:
            reactor.stop()

    do_exec_fail = do_run_fail = do_exec_done = do_done

    def sendData(self, data):
        print('SEND:{}'.format(data))
        return self.sendLine(str.encode(json.dumps(data)))

class EchoServerFactory(protocol.ServerFactory):
    protocol = EchoProtocol

class ControlRun(protocol.ProcessProtocol):
    def makeConnection(self, trans):
        print('Process launched')

    def outReceived(self, data):
        print('STDOUT:{}'.format(data.decode('utf8')))

    def errReceived(self,data):
        print('STDERR:{}'.format(data.decode('utf8')))

    def processEnded(self, reason):
        print("Process killed, {}".format(reason))


reactor.listenTCP(settings.CHAT_SERVICE_PORT, EchoServerFactory())
reactor.spawnProcess(ControlRun(),
                         settings.PATH_TO_INTER,
                         args=[settings.PATH_TO_INTER, settings.PATH_TO_SCRIPT,
                         settings.TEST_CONNECTION_ID,
                         settings.TEST_PREFIX,
                         str(settings.CHAT_SERVICE_PORT)],
                         env=settings.INTER_ENVS)
reactor.run()


