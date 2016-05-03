import asyncore
import asynchat
import socket
import mailbox
import logging

# create logger
log = logging.getLogger('baremail.smtp')

CRLF = '\r\n'

class smtp_handler(asynchat.async_chat):
    STATE_COMMAND = 0
    STATE_DATA = 1

    def __init__(self, sock, mbx):
        asynchat.async_chat.__init__(self, sock=sock)
        self.dispatch = dict(EHLO=self.handleEhlo, HELO=self.handleHelo,
                             MAIL=self.handleMail, RCPT=self.handleRcpt,
                             DATA=self.handleData, RSET=self.handleRset,
                             NOOP=self.handleNoop, QUIT=self.handleQuit)
        self.fqdn = socket.getfqdn()
        self.mbx = mbx
        self.set_terminator(CRLF)
        self.buffer = []
        self.data = []
        self.state = self.STATE_COMMAND
        self.push('220 {}'.format(self.fqdn))

    def collect_incoming_data(self, data):
        self.buffer.append(data)

    def found_terminator(self):
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

    # Overrides base class for convenience
    def push(self, msg):
        asynchat.async_chat.push(self, msg + CRLF)

    def runData(self, msg):
        ret_str = ''
        log.debug('C: {}'.format(msg))
        if msg == '.':
            text = CRLF.join(self.data)
            # write to mailbox
            msg = mailbox.MaildirMessage(text)
            msg_id = self.mbx.add(msg)
            self.data = []
            self.state = self.STATE_COMMAND
            ret_str = '250 Ok: queued as {}'.format(msg_id)
        elif msg and msg[0] == '.':
            self.data.append(msg[1:])
        else:
            self.data.append(msg)
        return ret_str

    def handleEhlo(self, cmd, args):
        return '250 {} {}'.format(self.fqdn, args)
        
    def handleHelo(self, cmd, args):
        return '250 {} {}'.format(self.fqdn, args)

    def handleMail(self, cmd, args):
        return '250 Ok'

    def handleRcpt(self, cmd, args):
        return '250 Ok'

    def handleData(self, cmd, args):
        self.data = []
        self.state = self.STATE_DATA
        return '354 End data with <CR><LF>.<CR><LF>'

    def handleRset(self, cmd, args):
        self.data = []

    def handleNoop(self, cmd, args):
        return '250 Ok'

    def handleQuit(self, cmd, args):
        return '221 Bye'

class smtp_server(asyncore.dispatcher):
    def __init__(self, host, port, mb):
        log.info('Serving SMTP on {}:{}'.format(host, port))
        asyncore.dispatcher.__init__(self)
        self.mbx = mb
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            log.info('Incoming SMTP connection from %s' % repr(addr))
            handler = smtp_handler(sock, self.mbx)


