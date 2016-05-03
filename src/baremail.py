#!/usr/bin/env python

import asyncore
import json
import logging
import logging.config
import mailbox
import sys

from baremail_pop3 import pop3_server
from baremail_smtp import smtp_server


def run_server(configuration_file):
    print('Config file {}'.format(configuration_file))
    try:
        cfile = open(configuration_file, 'r')
        cfgdict = json.load(cfile)
        print('daemon config - {}'.format(cfgdict['daemon']))
        print('network config - {}'.format(cfgdict['network']))
    except Exception, msg:
        print('Configuration file error - {}'.format(msg))
        return 1

    try:
        logging.config.dictConfig(cfgdict['logger_config'])
        # create logger
        log = logging.getLogger('baremail')
    except Exception, msg:
        print('Server logging initialization error - {}'.format(msg))
        return 1

    try:
        log.info('Mailbox directory {}'.format(cfgdict['daemon']['maildir']))
        mb = mailbox.Maildir(cfgdict['daemon']['maildir'], factory=None, create=True)
        p_server = pop3_server(cfgdict['network']['pop3_host'],
                               cfgdict['network']['pop3_port'],
                               mb)
        p_server = smtp_server(cfgdict['network']['smtp_host'],
                               cfgdict['network']['smtp_port'],
                               mb)
        asyncore.loop()
    except KeyboardInterrupt:
        log.info('cleaning up')
    except Exception, msg:
        print('Server initialization error - {}'.format(msg))
        return 1

if __name__ == '__main__':
    try:
        cfile_name = sys.argv[1]
    except:
        print('Error: missing configuration file name')
        print('Usage: {} <config_file>'.format(sys.argv[0]))
        sys.exit(1)
    else:
        sys.exit(run_server(cfile_name))
