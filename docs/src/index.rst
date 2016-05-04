.. BareMail documentation master file, created by
   sphinx-quickstart on Tue May  3 13:48:49 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

BareMail
========

A Pure Python Email Service
===========================
BareMail implements functional email servers for the POP3 and SMTP protocols.
Using a minimum of system resources it provides the function of a mail submission
agent, mail transfer agent, and mail delivery agent for a local system.
It can run from its source directory without modification or configuration.
The source is pure Python and no external libraries or modules are required.

Rationale
=========
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
============
* Accepts email submissions on the SMTP port
* Stores email in a maildir folder
* Serves those emails to POP3 clients

What It Doesn't
===============
* Provide individual email accounts
* Have any security features.  Anyone can submit or retreive email.
* Perform more than minimal checking to verify the structure of the submitted emails.

Lesser Warnings
===============
The developer is an embedded systems engineer not a Pythonista.  You won't find any list comprehension or
decorators within.

This is alpha code.  There is a great deal of todo to be done.

This code is tested and run on an Ubuntu base system using the Thunderbird client.  A broader
test base is needed.

Running
=======
Clone the repo.  CD to the src directory and run:
python baremail.py ../baremail_cfg.json

You can modify the JSON file to set the location of the mail directory, the host interface, and
port numbers.  At this time, BareMail runs in the foreground attached to a terminal.  Proper
daemonification is high on the todo list.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Source Documentation
====================

.. toctree::
   :maxdepth: 2

   modules

