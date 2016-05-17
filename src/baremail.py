#!/usr/bin/env python
"""A pure Python email server

BareMail provides servers for SMTP and POP3 to provide
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
import os
import pwd
import sys

from baremail_pop3 import pop3_server
from baremail_smtp import smtp_server

def config_logging(cfgdict):
    """Configure logging from dictionary.

    Logging configuration is included in the configuration file as a
    JSON object.  When loaded, this yields a dictionary suitable
    for use with dictConfig().
    """
    global log

    try: #configure logging
        logging.config.dictConfig(cfgdict)
        # create logger
        log = logging.getLogger('baremail')
    except Exception as msg:
        print(('Server logging initialization error - {}'.format(msg)))
        return 1

def config_servers(cfgdict):
    global server_list

    try: # instantiate servers
        server_list = []
        server_list.append(pop3_server(cfgdict['POP3']['host'],
                                       cfgdict['POP3']['port'],
                                       cfgdict['maildir']))
        for server in cfgdict['SMTP']:
            server_list.append(smtp_server(server['host'],
                                           server['port'],
                                           cfgdict['maildir']))
    except Exception as msg:
        log.exception('server initialization error - {}'.format(msg))
        return 1
    return 0


def set_user(cfgdict=None):
    if os.getuid() == 0: # running as root, see if priv can be dropped
        if cfgdict is not None:
            if cfgdict["group"] == 'root':
                log.error('group root not allowed')
                return 1
            if cfgdict["user"] == 'root':
                log.error('user root not allowed')
                return 1
            try:
                os.setgid(cfgdict["group"])
                os.setuid(cfgdict["user"])
            except Exception as msg:
                log.exception('Unable to set user - {}'.format(msg))
                return 1
        else:
            try: # try to drop to login user
                login_name = os.getlogin()
                if login_name == 'root':
                    log.error('user root not allowed')
                    return 1
                pw_info = pwd.getpwnam(login_name)
                os.setgid(pw_info[3])
                os.setuid(pw_info[2])
            except Exception as msg:
                log.exception('Unable to set user - {}'.format(msg))
                return 1
    else:
        log.info('Not started as root.  Not setting user')
    return 0

def daemonize(cfgdict):
    try:
        import daemon
        daemon.WORKDIR = cfgdict['working_dir']
        daemon.createDaemon()
        pidfile = open(cfgdict['pid_file'], 'w')
        pidfile.write(os.getpid())
        pidfile.close()
        return 0
    except Exception, e:
        print('Error daemonizing - {}'.format(e))
        return 1

def run_server():
    """Run service loop"""
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        log.info('cleaning up')
        for server in server_list:
            server.close()
        logging.shutdown()
        return 0
    except Exception as msg:
        log.exception('uncaught server exception - {}'.format(msg))
        return 1

if __name__ == '__main__':
    try:
        cfile_name = sys.argv[1]
    except:
        print('Error: missing configuration file name')
        print(('Usage: {} <config_file>'.format(sys.argv[0])))
        sys.exit(1)
    try:
        cfile = open(cfile_name, 'r')
        cfgdict = json.load(cfile)
    except Exception as msg:
        print(('Configuration file error - {}'.format(msg)))

    if cfgdict.has_key("daemon"):
        if daemonize(cfgdict["daemon"]) != 0:
            sys.exit(1)
    if config_logging(cfgdict['logger_config']) != 0:
        sys.exit(1)
    log.info('logging configured')
    log.info('PID {}'.format(os.getpid()))
    if config_servers(cfgdict['servers']) != 0:
        sys.exit(1)
    log.info('server configuration done')
    if cfgdict.has_key("user_group"):
        if set_user(cfgdict["user_group"]) != 0:
            sys.exit(1)
    else:
        if set_user() != 0:
            sys.exit(1)
    sys.exit(run_server(cfgdict))

