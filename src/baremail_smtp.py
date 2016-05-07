"""BareMail SMTP server

Implements a simple SMTP server.  Commands implementing login or security
features always return positive responses.
"""

import asyncore
import asynchat
import socket
import mailbox
import logging

# create logger
log = logging.getLogger('baremail.smtp')

CRLF = '\r\n'

class smtp_handler(asynchat.async_chat):
    """Service an individual POP3 connection.

    Very little internal state is maintained during each session.  Two states
    are implemented: COMMAND and DATA.  COMMAND is the default state.  DATA
    is entered upon receipt of the DATA command.  The state returns to COMMAND
    when the messages terminator '<CRLF>.<CRLF>' is received.
    """
    STATE_COMMAND = 0
    STATE_DATA = 1

    def __init__(self, sock, mbx):
        """Initialize minimal state and return greeting to client
        """
        asynchat.async_chat.__init__(self, sock=sock)
        self.dispatch = dict(EHLO=self.handleHelo, HELO=self.handleHelo,
                             MAIL=self.handleOK, RCPT=self.handleOK,
                             DATA=self.handleData, RSET=self.handleOK,
                             NOOP=self.handleOK, QUIT=self.handleQuit)
        self.fqdn = socket.getfqdn()
        self.mbx = mbx
        self.set_terminator(CRLF)
        self.buffer = []
        self.data = []
        self.state = self.STATE_COMMAND
        self.push('220 {}'.format(self.fqdn))

    def collect_incoming_data(self, data):
        """Marshal data chunks into buffer
        """
        self.buffer.append(data)

    def found_terminator(self):
        """Process client command or data

        In the COMMAND state, parses incoming client commands
        and dispatches them to the appropriate handler.  The
        command QUIT causes the handler to close after the response
        is sent to the client.

        In the DATA state, client input lines are handed off to runData()
        to be marshalled into a message for the mailbox.
        """
        msg = ''.join(self.buffer)
        if self.state == self.STATE_COMMAND:
            args = ''
            if msg:
                command = msg.split(None, 1)
                cmd = command[0].upper()
                if len(command) > 1:
                    args = command[1]
                log.debug('C: {} {}'.format(cmd, args))
                try:
                    smtp_cmd = self.dispatch[cmd]
                except KeyError:
                    log.debug('S: 502 Command not implemented')
                    self.push('502 Command not implemented')
                else:
                    ret_str = smtp_cmd(cmd, args)
                    log.debug('S: {}'.format(ret_str))
                    self.push(ret_str)
                    if smtp_cmd == self.handleQuit:
                        log.info('Closing connection')
                        self.close_when_done()
            else:
                self.push('500 Invalid command syntax')
        elif self.state == self.STATE_DATA:
            ret_str = self.runData(msg)
            if ret_str:
                log.debug('S: {}'.format(ret_str))
                self.push(ret_str)
        else:
            self.push('451 Internal confusion')
            self.state = self.STATE_COMMAND
            self.data = []
        self.buffer = []

    def push(self, msg):
        """Overrides base class for convenience

        Every response to client ends in CRLF.  Adding it here
        ensures consistency.
        """
        asynchat.async_chat.push(self, msg + CRLF)

    def runData(self, msg):
        """Process received message line from client

        In the DATA state, the client is sending the messages one line at
        a time.  Here the individual lines are collected until the message
        terminator is received.  At that time, the message is converted to
        the mail box format and stored then the state is returned to COMMAND
        mode.
        """
        ret_str = ''
        log.debug('C: {}'.format(msg))
        if msg == '.':
            text = CRLF.join(self.data)
            # write to mailbox
            msg = mailbox.MaildirMessage(text)
            try:
                log.info('accessing mbx in runData()')
                msg_id = self.mbx.add(msg)
                ret_str = '250 Ok: queued as {}'.format(msg_id)
            except Exception, e:
                ret_str = '451 could not save message {}'.format(msg_id)
                log.exception('Error writing mailbox {}'.format(e))
                msg_id = 'Error!!'
            self.data = []
            self.state = self.STATE_COMMAND
        elif msg and msg[0] == '.':
            self.data.append(msg[1:])
        else:
            self.data.append(msg)
        return ret_str

    def handleHelo(self, cmd, args):
        """Acknowlege client with this server's domain name
        """
        return '250 {} {}'.format(self.fqdn, args)

    def handleOK(self, cmd, args):
        """Acknowlege client
        """
        return '250 Ok'

    def handleData(self, cmd, args):
        """Enter state DATA and acknowlege client with termination
        instruction.
        """
        self.data = []
        self.state = self.STATE_DATA
        return '354 End data with <CR><LF>.<CR><LF>'

    def handleQuit(self, cmd, args):
        return '221 Bye'

class smtp_server(asyncore.dispatcher):
    """Listens on SMTP port and launch SMTP handler on connection.
    """
    def __init__(self, host, port, mb):
        log.info('Serving SMTP on {}:{}'.format(host, port))
        asyncore.dispatcher.__init__(self)
        self.mbx = mb
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        """Creates handler for each SMTP connection.
        """
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            log.info('Incoming SMTP connection from %s' % repr(addr))
            handler = smtp_handler(sock, self.mbx)


