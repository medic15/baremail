"""BareMail POP3 server

Implements a simple POP3 server.  Commands implementing login or security
features return positive responses to the client regardless of the
state of the connection.

Very little internal state is maintained during each session.  Only the state
needed to identify messages for retreival or deletion is kept.
"""

import asynchat
import asyncore
import logging
import mailbox
import mutex
import socket

# create logger
log = logging.getLogger('baremail.pop3')

CRLF = '\r\n'

pop3_mutex = mutex.mutex()

class pop3_handler(asynchat.async_chat):
    """Service an individual POP3 connection.

    Enforces a limit of one connected client at a time.  Supports
    leaving messages in the mailbox until deleted by client.  This
    allows multiple clients to retrieve copies of the messages.

    The SMTP server places received messages in the mail directory's 'new' folder.
    Those messages are normalized and transferred to the 'cur' directory to
    be made available to the client.  This process occurs only once at the start of
    each client connection.  Messages received after that point will not be visible
    to the client until the next connection occurs.
    """
    def __init__(self, sock, mbx):
        asynchat.async_chat.__init__(self, sock=sock)
        self.dispatch = dict(QUIT=self.handleQuit, STAT=self.handleStat,
                             LIST=self.handleList, RETR=self.handleRetr,
                             DELE=self.handleDele, NOOP=self.handleOK,
                             RSET=self.handleRset, USER=self.handleOK,
                             PASS=self.handleOK, APOP=self.handleOK,
                             UIDL=self.handleUidl, CAPA=self.handleCapa)
        self.mbx = mbx
        self.set_terminator(CRLF)
        self.buffer = []
        self.msg_index = []
        self.delete_list = []
        id_number = 0;

        self.mbx_lock = pop3_mutex.testandset()
        if not self.mbx_lock:
            log.info('S: -ERR Mailbox busy.  Try again later.')
            self.push('-ERR Mailbox busy.  Try again later.')
            self.close_when_done()
            return

        try:
            for message_id, message in self.mbx.iteritems():
                if message.get_subdir() == 'new':
                    self.add_new_messages(message_id)
                id_number += 1
                self.msg_index.append(message_id)
            log.debug('S: +OK POP3 server ready')
            self.push('+OK POP3 server ready')
        except mailbox.Error:
            log.error('S: -ERR Error reading mailbox')
            self.push('-ERR Error reading mailbox')
            self.close_when_done()

    def collect_incoming_data(self, data):
        """Marshal data chunks into buffer
        """
        self.buffer.append(data)

    def found_terminator(self):
        """Process client command

        All client commands are contained in a single line and some
        include arguments after the command.  Here we dispatch the commands
        and arguments to the appropriate handlers.  Unrecognized commands
        generate an error response.

        The QUIT command causes this handler to close after issuing the
        response to the client.
        """
        msg = ''.join(self.buffer)
        args = ''
        if msg:
            command = msg.split(None, 1)
            cmd = command[0].upper()
            if len(command) > 1:
                args = command[1]
        else:
            cmd = ''
        log.debug('C: {} {}'.format(cmd, args))
        try:
            pop_cmd = self.dispatch[cmd]
        except KeyError:
            log.info('S: -ERR unknown command')
            self.push('-ERR unknown command')
        else:
            ret_str = pop_cmd(cmd, args)
            log.debug('S: {}'.format(ret_str))
            self.push(ret_str)
            if pop_cmd == self.handleQuit:
                self.close_when_done()
        self.buffer = []

    def handle_close(self):
        """Perform cleanup before closing this handler.

        This method is called when the handler is closing for any
        reason.  The single handler lock is released here to ensure
        that it is available to the next client connection.
        """
        log.info('POP3 Connection closed')
        asynchat.async_chat.handle_close(self)
        if self.mbx_lock:
            pop3_mutex.unlock()

    def push(self, msg):
        """Overrides base class for convenience

        Every response to client ends in CRLF.  Adding it here
        ensures consistency.
        """
        asynchat.async_chat.push(self, msg + CRLF)

    def handleQuit(self, cmd, args):
        """Delete messages marked for such by this client

        The RFC states that deletion of messages occurs only at the controlled
        termination of a client session.  The messages marked for deletion by
        the client are removed from the mail directory here before the response
        is issued to the client.
        """
        for id in self.delete_list:
            log.debug('Delete key {}'.format(id))
            try:
                self.mbx.discard(id)
            except Exception, exmsg:
                log.error('Quit error - {}'.format(exmsg))

        return '+OK POP3 server signing off'

    def handleStat(self, cmd, args):
        """Return mailbox statistics to client

        Returns the number of messages and a total messages sizes in octets
        """
        num_msgs = 0;
        mb_size = 0;
        try:
            for k in self.msg_index:
                try:
                    s = self.mbx.get_string(k)
                    num_msgs += 1
                    mb_size += len(s)
                except mailbox.Error:
                    pass
        except Exception, exmsg:
            log.error('Unhandled exception {}'.format(exmsg))
            return '-ERR Internal Error'
        else:
            return '+OK {} {}'.format(num_msgs, mb_size)

    def getScanListing(self, msg_num):
        """Return a message index and size for a single message
        """
        return '{} {}'.format(msg_num, len(self.mbx.get_string(self.msg_index[msg_num])))

    def handleList(self, cmd, args):
        """Return a listing of messages in the mailbox
        """
        if args:
            try:
                msg_num = int(args.split()[0])
                ret_msg = '+OK {}'.format(self.getScanListing(msg_num))
            except:
                ret_msg = '-ERR invalid index {}'.format(args)
        else:
            try:
                ret_msg_array = ['+OK {} messages'.format(len(self.msg_index))]
                for n in range(len(self.msg_index)):
                    ret_msg_array.append(self.getScanListing(n))
                ret_msg_array.append('.')
                ret_msg = CRLF.join(ret_msg_array)
            except Exception, exmsg:
                log.error('handleList error - {}'.format(exmsg))
                ret_msg = '-ERR Interal server error'
        return ret_msg

    def handleRetr(self, cmd, args):
        """Return the contents of a message
        """
        try:
            msg_num = int(args.split()[0])
            msg_string = self.mbx.get_string(self.msg_index[msg_num])
        except Exception, exmsg:
            log.error('handleRetr error - {}'.format(exmsg))
            ret_msg = '-ERR invalid index {}'.format(msg_num)
        else:
            ret_msg_array = ['+OK {} octets'.format(len(msg_string))]
            ret_msg_array.append(msg_string)
            ret_msg_array.append('.')
            ret_msg = CRLF.join(ret_msg_array)
        return ret_msg

    def handleDele(self, cmd, args):
        """Mark a message for deletion
        """
        try:
            msg_num = int(args.split()[0])
            msg_key = self.msg_index[msg_num]
        except Exception, exmsg:
            log.error('handleDele error - {}'.format(exmsg))
            ret_msg = '-ERR invalid index {}'.format(msg_num)
        else:
            self.delete_list.append(msg_key)
            ret_msg = '+OK message {} deleted'.format(msg_num)
        return ret_msg

    def handleOK(self, cmd, args):
        """Return a positive response to the client
        """
        return '+OK'

    def handleRset(self, cmd, args):
        """Unmarks messages tagged for deletion
        """
        self.delete_list = []
        return '+OK'

    def getUidlListing(self, msg_num):
        """Return the index and unique identifier for an individual message

        The unique identifier returned here is simply the file name of the
        message in the mail directory.
        """
        return '{} {}'.format(msg_num, self.msg_index[msg_num])

    def handleUidl(self, cmd, args):
        """Return a UIDL listing for a single message or for all messages

        Returns UIDL for a single message if a message index argument is submitted
        by the client.  Otherwise returns a list of all message UIDLs for the
        mailbox.
        """
        if args:
            try:
                msg_num = int(args.split()[0])
                ret_msg = '+OK {}'.format(self.getUidlListing(msg_num))
            except:
                ret_msg = '-ERR invalid index {}'.format(args)
        else:
            try:
                ret_msg_array = ['+OK {} messages'.format(len(self.msg_index))]
                for n in range(len(self.msg_index)):
                    ret_msg_array.append(self.getUidlListing(n))
                ret_msg_array.append('.')
                ret_msg = CRLF.join(ret_msg_array)
            except Exception, exmsg:
                log.error('handleList error - {}'.format(exmsg))
                ret_msg = '-ERR Interal server error'
        return ret_msg

    def handleCapa(self, cmd, args):
        """Return a capabilities list to the client
        """
        caps_list = ['+OK List follows']
        caps_list.append('USER')
        caps_list.append('PASS')
        caps_list.append('UIDL')
        caps_list.append('.')
        return CRLF.join(caps_list)

    def add_new_messages(self, message_id):
        """Normalize and add a message to the mailbox

        POP3 requires that the statistics for file size reflect the number of
        octets that will be sent in response to a RETR command.  To take in to
        account the two octet CRLF at the end of each line, we process each newly
        submitted message such that the lines are properly terminated for retreival.

        Also, any lines in the message that begin with a '.' are byte stuffed
        to avoid being mistaken for the message terminator.  This is per the
        RFC specifying the message syntax.
        """
        norm_array = []
        msg_array = self.mbx.get_string(message_id).splitlines()
        for line in msg_array:
            if line == '.':
                line = '..'
            norm_array.append(line)
        msg_string = '\r\n'.join(norm_array)
        new_message = mailbox.MaildirMessage(msg_string)
        new_message.set_subdir('cur')
        self.mbx[message_id] = new_message

class pop3_server(asyncore.dispatcher):
    """Listens on POP3 port and launch pop3 handler on connection.
    """
    def __init__(self, host, port, mb):
        log.info('Serving POP3 on {}:{}'.format(host, port))
        asyncore.dispatcher.__init__(self)
        self.mbx = mb
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        """Creates handler for each POP3 connection.
        """
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            log.info('Incoming POP3 connection from %s' % repr(addr))
            handler = pop3_handler(sock, self.mbx)


