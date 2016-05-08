#!/usr/bin/env python
"""A pure Python email server

BareMail provides servers for SMTP and POP3 to serve as
a simple mail system for local email messages.  It is intended primarily
to service daemon processes that report events via email messages.  Daemon
SMTP setup is greatly simplified since BareMail is extremely promiscuous,
accepting any user name and password as valid.

.. warning::
   BareMail provides **NO SECURITY** whatsoever.  The SMTP and POP3 ports
   should never be opened on an interface attached to any untrusted network.
"""

import asyncore
import json
import logging
import logging.config
import mailbox
import os
import pwd
import sys

from baremail_pop3 import pop3_server
from baremail_smtp import smtp_server

def run_server(cfgdict=None):
    """Configure and run the email servers.

    Reads configuration from a JSON file and initializes the servers and
    logging classes.  Logging configuration is included in the configuration
    file as a JSON object.  When loaded, this yields a dictionary suitable
    for use with dictConfig().

    :rtype: integer 0 for keyboard interrupt or 1 for failure at startup
    """
    try: #configure logging
        logging.config.dictConfig(cfgdict['logger_config'])
        # create logger
        log = logging.getLogger('baremail')
    except Exception, msg:
        print('Server logging initialization error - {}'.format(msg))
        return 1

    try: # instantiate servers
        server_list = []
        server_list.append(pop3_server(cfgdict['network']['POP3']['host'],
                                       cfgdict['network']['POP3']['port']))
        for server in cfgdict['network']['SMTP']:
            server_list.append(smtp_server(server['host'], server['port']))
    except Exception, msg:
        log.exception('server initialization error - {}'.format(msg))

    if os.getuid() == 0: # running as root, see if priv can be dropped
        log.info('pid {}'.format(os.getpid()))
        try:
            login_name = os.getlogin()
            pw_info = pwd.getpwnam(login_name)
            os.setgid(pw_info[3])
            os.setuid(pw_info[2])
        except Exception, msg:
            log.exception('Unable to set user - {}'.format(msg))
            return 1

    try:
        mb = mailbox.Maildir(cfgdict['global']['maildir'], factory=None, create=True)
        log.info('Mailbox directory {}'.format(cfgdict['global']['maildir']))
        for server in server_list:
            server.set_mailbox(mb)
    except Exception, msg:
        log.exception('mailbox initialization error - {}'.format(msg))
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        log.info('cleaning up')
        return 0
    except Exception, msg:
        log.exception('uncaught server exception - {}'.format(msg))
        return 1

if __name__ == '__main__':
    try:
        cfile_name = sys.argv[1]
    except:
        print('Error: missing configuration file name')
        print('Usage: {} <config_file>'.format(sys.argv[0]))
        sys.exit(1)
    try:
        cfile = open(cfile_name, 'r')
        cfgdict = json.load(cfile)
    except Exception, msg:
        print('Configuration file error - {}'.format(msg))
    else:
        sys.exit(run_server(cfgdict))

