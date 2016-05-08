BareMail
========

A Pure Python Email Service
===========================
BareMail implements functional email servers for the POP3 and SMTP protocols.
Using a minimum of system resources it provides the function of a mail submission
agent, mail transfer agent, and mail delivery agent for a local system.
It can run from its source directory without modification or configuration.
The source is pure Python using only the standard libraries. No external packages are required.

Rationale
---------
Many long running services and daemons present on desktop and server machines use email to
notify the administrator of critical events.  The majority of desktop users and casual system
administrators don't take advantage of this capability to monitor the health of the systems
under their control.  Either the mail messages are discarded silently or they sit collecting
virtual dust in the local mail spool.  Here, listed in no particular order, are some of the
reasons for this state of affairs:

* Getting sendmail (or its functional equivalent) working is non-trivial.
* The daemon doesn't support the security features required to directly submit email to the server.
* The daemon doesn't support any other port that the standard SMTP port 25.
* There are concerns about having email credentials stored in plain text for each daemon's configuration file.
* There are no easy ways to get most email clients to look in a local mail spool.

BareMail solves this problem by requiring no little or no setup itself and by allowing
the daemon's email parameters to be very forgiving.  It accomplishes this by throwing away any
and all sense of security and doing away with individual accounts.  The name BareMail
comes from being "naked" to the world in terms of security and from being the bare minimum
of functionality to accomplish the task.

On either the POP3 or SMTP interface, BareMail will accept **any** user name and password.  As
a matter of fact, it will quite happily render service with no login at all.

.. warning::
   BareMail provides **NO SECURITY** whatsoever.  The SMTP and POP3 ports
   should never be opened on an interface attached to any untrusted network.
   It is intended to run behind a firewall and serve either a single machine on
   the ``localhost`` interface or be exposed to a LAN shared only by trusted users.

What It Does
------------
* Accepts email submissions on the SMTP port
* Stores email in a maildir folder
* Serves those emails to POP3 clients

What It Doesn't
---------------
* Provide individual email accounts
* Have any security features.  Anyone can submit or retreive email.
* Perform more than minimal checking to verify the structure of the submitted emails.

Lesser Warnings
---------------
The developer is an embedded systems engineer not a Pythonista.  You won't find any list comprehension or
decorators within.

This is alpha code.  There is a great deal of todo to be done.

This code is tested and run on an Ubuntu base system using the Thunderbird client.  A broader
test base is needed.

Running
-------
Clone or unzip the repository to a local directory.  Change directory to the baremail directory and run:
    src/baremail.py ../config/high_port.json

This will open servers available only to localhost at ports 2025 for SMTP and 2110 for POP3.

Alternatively you can run BareMail using sudo to open the standard ports:
    sudo src/baremail.py ../config/standard_port.json

After opening ports 25 and 587 for SMTP and opening 110 for POP3, BareMail will drop root privileges
and continue to run as the original user.

.. note::
    BareMail will not run directly from the root account.

To access BareMail over a LAN, copy one of the configuration files and modify the 'host' parameters
in the network settings to the name of the machine on which it's running.  Each of the servers can be
configured individually so it's possible to have SMTP listen on a LAN interface but have POP3 only
available to localhost.

At this time, BareMail runs in the foreground attached to a terminal.  Proper
daemonification is high on the todo list.

An Alternative to BareMail
--------------------------
For a fully functional and secure email system, the combination of Dovecot and DragonFly Mail Agent is
easily installable on most distributions and both servers have good support from the community.  Both
have relatively small memory footprints and are not CPU intensive.  These servers can be exposed to
the Internet with as much safety as can be expected in today's high threat world.
Configuration requires more knowlege of the details of POP3 and SMTP but should be doable for anyone
with a bit of patience and perserverance.

.. note::
    Dragonfly does not listen for connections on the SMPT port 25.  This may be a problem for
    older daemons that expect the submit email at this port.

* http://dovecot.org/
* https://github.com/corecode/dma#dma----dragonfly-mail-agent

