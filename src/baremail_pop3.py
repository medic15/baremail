"""BareMail POP3 server

Implements a simple POP3 server.  Commands implementing login or security
features return positive responses to the client regardless of the
state of the connection.

Very little internal state is maintained during each session.  Only the state
needed to identify messages for retreival or deletion is kept.
"""

import asynchat
import asyncore
import bare_maildir
import logging
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
    def __init__(self, sock, mb_name):
        asynchat.async_chat.__init__(self, sock=sock)
        self.dispatch = dict(QUIT=self.handleQuit, STAT=self.handleStat,
                             LIST=self.handleList, RETR=self.handleRetr,
                             DELE=self.handleDele, NOOP=self.handleOK,
                             RSET=self.handleRset, USER=self.handleOK,
                             PASS=self.handleOK, APOP=self.handleOK,
                             UIDL=self.handleUidl, CAPA=self.handleCapa)
        self.set_terminator(CRLF)
        self.buffer = []

        self.mbx_lock = pop3_mutex.testandset()
        if not self.mbx_lock:
            log.info('S: -ERR Mailbox busy.  Try again later.')
            self.push('-ERR Mailbox busy. Try again later.')
            self.close_when_done()
            return

        try:
            self.mbx = bare_maildir.BareMaildir(mb_name)
            log.debug('S: +OK POP3 server ready')
            self.push('+OK POP3 server ready')
        except Exception:
            log.exception('S: -ERR Error reading mailbox')
            self.push('-ERR Error reading mailbox')
            self.close_when_done()
        except Exception as msg:
            log.exception('Unknown mailbox access error - {}'.format(msg))

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
            log.info('S: -ERR unknown command "{}"'.format(cmd))
            self.push('-ERR unknown command "{}"'.format(cmd))
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
        try:
            self.mbx.close()
        except Exception:
            pass

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
        self.mbx.close()

        return '+OK POP3 server signing off'

    def handleStat(self, cmd, args):
        """Return mailbox statistics to client

        Returns the number of messages and a total messages sizes in octets
        """
        num_msgs = 0;
        mb_size = 0;
        try:
            messages = self.mbx.items()
            num_msgs = len(messages)
            for msg in messages:
                mb_size += msg.length
        except Exception as exmsg:
            log.exception('Unhandled exception {}'.format(exmsg))
            return '-ERR Internal Error'
        else:
            return '+OK {} {}'.format(num_msgs, mb_size)

    def getScanListing(self, msg_num, msg_list):
        """Return a message index and size for a single message
        """
        return '{} {}'.format(msg_num, msg_list[msg_num].length)

    def handleList(self, cmd, args):
        """Return a listing of messages in the mailbox
        """
        msg_list = self.mbx.items()
        if args:
            try:
                msg_num = int(args.split()[0])
                ret_msg = '+OK {}'.format(self.getScanListing(msg_num, msg_list))
            except Exception:
                ret_msg = '-ERR invalid index {}'.format(args)
        else:
            try:
                ret_msg_array = ['+OK {} messages'.format(len(msg_list))]
                for n in range(len(msg_list)):
                    ret_msg_array.append(self.getScanListing(n, msg_list))
                ret_msg_array.append('.')
                ret_msg = CRLF.join(ret_msg_array)
            except Exception as exmsg:
                log.exception('handleList error - {}'.format(exmsg))
                ret_msg = '-ERR Interal server error'
        return ret_msg

    def handleRetr(self, cmd, args):
        """Return the contents of a message
        """
        try:
            msg_num = int(args.split()[0])
            msg_string = self.mbx.get_string(msg_num)
        except Exception as exmsg:
            log.exception('handleRetr error - {}'.format(exmsg))
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
            msg_key = self.mbx.delete(msg_num)
            ret_msg = '+OK message {} deleted'.format(msg_num)
        except Exception as exmsg:
            log.exception('handleDele error - {}'.format(exmsg))
            ret_msg = '-ERR invalid index {}'.format(msg_num)
        return ret_msg

    def handleOK(self, cmd, args):
        """Return a positive response to the client
        """
        return '+OK'

    def handleRset(self, cmd, args):
        """Unmarks messages tagged for deletion
        """
        self.mbx.reset()
        return '+OK'

    def getUidlListing(self, msg_num, msg_list):
        """Return the index and unique identifier for an individual message

        The unique identifier returned here is simply the file name of the
        message in the mail directory.
        """
        return '{} {}'.format(msg_num, msg_list[msg_num].basename)

    def handleUidl(self, cmd, args):
        """Return a UIDL listing for a single message or for all messages

        Returns UIDL for a single message if a message index argument is submitted
        by the client.  Otherwise returns a list of all message UIDLs for the
        mailbox.
        """
        msg_list = self.mbx.items()
        if args:
            try:
                msg_num = int(args.split()[0])
                ret_msg = '+OK {}'.format(self.getUidlListing(msg_num))
            except:
                ret_msg = '-ERR invalid index {}'.format(args)
        else:
            try:
                ret_msg_array = ['+OK {} messages'.format(len(msg_list))]
                for n in range(len(msg_list)):
                    ret_msg_array.append(self.getUidlListing(n, msg_list))
                ret_msg_array.append('.')
                ret_msg = CRLF.join(ret_msg_array)
            except Exception as exmsg:
                log.exception('handleList error - {}'.format(exmsg))
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

class pop3_server(asyncore.dispatcher):
    """Listens on POP3 port and launch pop3 handler on connection.
    """
    def __init__(self, host, port, mb_name):
        log.info('Serving POP3 on {}:{}'.format(host, port))
        self.mb_name = mb_name
        asyncore.dispatcher.__init__(self)
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
            #handler = pop3_handler(sock, self.mb_name)
            pop3_handler(sock, self.mb_name)

