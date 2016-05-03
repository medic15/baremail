# BareMail
### A Pure Python Email Service
BareMail implements rudimentary email servers for the POP3 and SMTP protocols.
It can run from its source directory without modification or configuration.
The source is pure Python and no external libraries or modules are required.

## Rationale
I use serveral daemon services on different machines around my home office.  Most of these
services have a capability to send notifications via email.  There are several factors that
combine to prevent me from making use of those features:
  * The daemon doesn't support the security features required by my email provider.
  * Email is the last item to be configured and, by the time I've gotten to that point, I've
  run out of time to configure and test.
  * I'm hesitant to put my email credentials in a plain text file.
  * I live near the beach.

Since email is the one thing I check throughout the day, that seems a waste.  As things are, I
find out a service is down when I go to use it and it's not there.  This is especially problematic
when that service happens to be my back up system.

BareMail solves this problem by requiring no little or no setup itself and by allowing
the daemon's email parameters to be very forgiving.  It accomplishes this by throwing away any
and all sense of security and doing away with individual accounts.  The name BareMail
comes from being "naked" to the world in terms of security and from being the bare minimum
of functionality to accomplish the task.

On either the POP3 or SMTP interface, BareMail will accept **any** user name and password.  As
a matter of fact, it will quite happily render service with no login at all.

## Warning
BareMail offers **no security** whatsoever.  It is intended to run behind a firewall and serving
either a single machine on the localhost interface or exposed to a LAN shared by trusted users.

## What It Does
  * Accept email submissions on the SMPT port
  * Store email in a maildir folder
  * Serve those emails out the POP3 port

## What It Doesn't
  * Provide individual email accounts
  * Have any security features.  Anyone can submit or retreive email.
  * Perform more than minimal checking to verify the structure of the submitted emails.

## Lesser Warnings
I'm an embedded systems engineer not a Pythonista.  You won't find any list comprehension or
decorators within.

This is alpha code.  There are a ton of todo items to be done.  I'll be tackling those as time allows.

## Running
Clone the repo.  CD to the src directory and run:
python baremail.py ../baremail_cfg.json

You can modify the JSON file to set the location of the mail directory, the host interface, and
port numbers.  At this time, BareMail runs in the foreground attached to a terminal.  Proper
daemonification is high on the todo list.
