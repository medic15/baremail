import asyncore
import asynchat
import socket
import mailbox
import logging

# create logger
log = logging.getLogger('baremail.pop3')

CRLF = '\r\n'

class pop3_handler(asynchat.async_chat):
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
        try:
            for message_id, message in self.mbx.iteritems():
                if message.get_subdir() == 'new':
                    self.add_new_messages(message_id)
                id_number += 1
                self.msg_index.append(message_id)
            log.debug('S: +OK POP3 server ready')
            self.push('+OK POP3 server ready')
        except mailbox.Error:
            log.error('-ERR Error reading mailbox')
            self.push('-ERR Error reading mailbox')
            self.close()

    def collect_incoming_data(self, data):
        self.buffer.append(data)

    def found_terminator(self):
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

    # Overrides base class for convenience
    def push(self, msg):
        asynchat.async_chat.push(self, msg + CRLF)

    def handleQuit(self, cmd, args):
        for id in self.delete_list:
            log.debug('Delete key {}'.format(id))
            try:
                self.mbx.discard(id)
            except Exception, exmsg:
                log.error('Quit error - {}'.format(exmsg))

        return '+OK POP3 server signing off'

    def handleStat(self, cmd, args):
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
        return '{} {}'.format(msg_num, len(self.mbx.get_string(self.msg_index[msg_num])))

    def handleList(self, cmd, args):
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
        return '+OK'

    def handleRset(self, cmd, args):
        self.delete_list = []
        return '+OK'

    def getUidlListing(self, msg_num):
        return '{} {}'.format(msg_num, self.msg_index[msg_num])

    def handleUidl(self, cmd, args):
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
        caps_list = ['+OK List follows']
        caps_list.append('USER')
        caps_list.append('PASS')
        caps_list.append('UIDL')
        caps_list.append('.')
        return CRLF.join(caps_list)

    def add_new_messages(self, message_id):
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
    def __init__(self, host, port, mb):
        log.info('Serving POP3 on {}:{}'.format(host, port))
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
            log.info('Incoming POP3 connection from %s' % repr(addr))
            handler = pop3_handler(sock, self.mbx)


