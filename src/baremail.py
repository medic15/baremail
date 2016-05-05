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
import pwd
import os
import sys

from baremail_pop3 import pop3_server
from baremail_smtp import smtp_server
from b_daemon import createDaemon

def run_server(configuration_file):
    """Configure and run the email servers.

    Reads configuration from a JSON file and initializes the servers and
    logging classes.  Logging configuration is included in the configuration
    file as a JSON object.  When loaded, this yields a dictionary suitable
    for use with dictConfig().

    :param configuration_file: string path to JSON configuration file
    :rtype: integer 0 for keyboard interrupt or 1 for failure at startup
    """
    try: #process configuration file
        cfile = open(configuration_file, 'r')
        cfgdict = json.load(cfile)
    except Exception, msg:
        print('Configuration file error - {}'.format(msg))
        return 1

    try: #configure logging
        logging.config.dictConfig(cfgdict['logger_config'])
        # create logger
        log = logging.getLogger('baremail')
    except Exception, msg:
        print('Server logging initialization error - {}'.format(msg))
        return 1

    # daemonize if specified
    if cfgdict['global']['daemon']:
        try:
            createDaemon()
        except Exception, msg:
            log.error('Unable to detach to daemon - {}'.format(msg))
            return 1

        try:
            fp = open(cfgdict['global']['PID_file'])
            fp.writeline('{}\n'.format(os.getpid()))
            fp.close()
        except Exception, msg:
            log.error('Unable to open PID file - {}'.format(msg))
            return 1

    try: #initialize servers
        server_list = []
        server_list.append(pop3_server(cfgdict['network']['POP3']['host'],
                                       cfgdict['network']['POP3']['port']))
        for server in cfgdict['network']['SMTP']:
            server_list.append(smtp_server(server['host'], server['port']))
    except Exception, msg:
        log.error('Server initialization error - {}'.format(msg))
        return 1

    # Can only setuid if currently running as root
    if os.getuid() == 0:
        if cfgdict['global']['user']: # a user was specified
            # try to get the uid
            try:
                pwd_struct = pwd.getpwnam(cfgdict['global']['user'])
            except KeyError, e:
                log.error('No such user {} - {}'.format(cfgdict['global']['user'], e))
                return 1
            if pwd_struct[2] != 0: # we're already root
                try: # Try setting the new gid
                    os.setgid(pwd_struct[3])
                except OSError, e:
                    log.error('Could not set effective group id: %s' % e)
                    return 1
                try: # Try setting the new uid
                    os.setuid(pwd_struct[2])
                except OSError, e:
                    log.error('Could not set effective user id: %s' % e)
                    return 1
        else: # no user specified, try to drop back to original user
            try:
                pwd_struct = pwd.getpwnam(os.getlogin())
            except KeyError, e:
                log.error('Unable to determin user - {}'.format(e))
                return 1
            if pwd_struct[2] != 0: # we're already root
                try: # Try setting the new gid
                    os.setgid(pwd_struct[3])
                except OSError, e:
                    log.error('Could not set effective group id: %s' % e)
                    return 1
                try: # Try setting the new uid
                    os.setuid(pwd_struct[2])
                except OSError, e:
                    log.error('Could not set effective user id: %s' % e)
                    return 1
        log.info('Running as user {}'.format(pwd_struct[0]))

    # Mailbox creation is alway performed as an unprivileged user.  User must have
    # permissions sufficient to create the mailbox in the given directory.
    try: # create/open mailbox and add it to the servers
        log.info('Mailbox directory {}'.format(cfgdict['global']['maildir']))
        mb = mailbox.Maildir(cfgdict['global']['maildir'], factory=None, create=True)
        for server in server_list:
            server.set_mailbox(mb)
    except Exception, msg:
        log.error('Mailbox creation error - {}'.format(msg))
        

    try: # start processing
        asyncore.loop()
    except KeyboardInterrupt:
        log.info('cleaning up')

if __name__ == '__main__':
    try:
        cfile_name = sys.argv[1]
    except:
        print('Error: missing configuration file name')
        print('Usage: {} <config_file>'.format(sys.argv[0]))
        sys.exit(1)
    else:
        sys.exit(run_server(cfile_name))
