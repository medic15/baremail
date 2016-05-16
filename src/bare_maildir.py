import logging
import os
import os.path
import tempfile

# create logger
log = logging.getLogger('baremail.maildir')

def _sync_flush(f):
    """Ensure changes to file f are physically on disk."""
    f.flush()
    if hasattr(os, 'fsync'):
        os.fsync(f.fileno())

def _sync_close(f):
    """Close file f, ensuring all changes are physically on disk."""
    _sync_flush(f)
    f.close()

def _moveto(name, dest):
    try:
        if hasattr(os, 'link'):
            os.link(name, dest)
            os.remove(name)
        else:
            os.rename(name, dest)
    except OSError:
        log.exception('_moveto')
        os.remove(name)
        raise

class BareMessage():
    def __init__(self, message):
        self.delete = False
        if isinstance(message, str):
            log.debug('Create msg from string')
            self.path = None
            self.basename = None
            self.length = len(message)
        elif isinstance(message, file):
            log.debug('Create msg from file - {}'.format(message.name))
            self.path = message.name
            self.basename = os.path.basename(message.name)
            s = message.read()
            self.length = len(s)
        else:
            raise TypeError('Invalid message type: %s' % type(message))

class BareMaildir():
    """A qmail-style Maildir mailbox."""

    colon = ':'

    def __init__(self, dirname):
        """Initialize a Maildir instance."""
        self.entries = []
        self._path = dirname
        if not os.path.exists(self._path):
            os.mkdir(self._path, 0o700)
            log.debug('creating directory {}'.format(self._path))
        for fname in os.listdir(dirname):
            log.debug('adding file {}'.format(fname))
            path = os.path.join(dirname, fname)
            log.debug('adding file {}'.format(path))
            msgfile = open(path, 'rb')
            msg = BareMessage(msgfile)
            self.entries.append(msg)
            msgfile.close()

    def add(self, msg_str):
        """Add message string and return assigned key."""
        tmp_file = tempfile.NamedTemporaryFile(prefix='bare', delete=False)
        log.debug('add message from string - {}'.format(tmp_file.name))
        try:
            tmp_file.file.write(msg_str)
        except Exception:
            tmp_file.close()
            os.remove(tmp_file.name)
            raise
        _sync_close(tmp_file)
        uniq = os.path.basename(tmp_file.name)
        dest = os.path.join(self._path, uniq)
        _moveto(tmp_file.name, dest)
        msg = BareMessage(msg_str)
        msg.path = dest
        msg.basename = uniq
        msg.length = len(msg_str)
        self.entries.append(msg)
        return uniq

    def items(self):
        """Return a list of (key, message) tuples. Memory intensive."""
        return self.entries

    def delete(self, msg_num):
        self.entries[msg_num].delete = True

    def get_string(self, msg_num):
        f = open(self.entries[msg_num].path, 'rb')
        return f.read()

    def reset(self):
        for m in self.entries:
            m.delete = False

    def close(self):
        for m in self.entries:
            if m.delete:
                try:
                    os.unlink(m.path)
                except Exception:
                    raise
