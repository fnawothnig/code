#!/usr/bin/env python3
import socket
import os
import sys
from pprint import pprint as pp
import math
from urllib.parse import unquote
import termios

DEBUG = os.environ.get("DEBUG", False)

def format_size(nbytes, si=False):
    prefixes = ".kMGTPE"
    div = 1000 if si else 1024
    exp = int(math.log(nbytes, div))
    if exp == 0:
        return "%.2f B" % quot
    elif exp < len(prefixes):
        quot = nbytes / div**exp
        return "%.2f %sB" % (quot, prefixes[exp])
    else:
        exp = len(prefixes) - 1
        quot = nbytes / div**exp
        return "%f %sB" % (quot, prefixes[exp])
    return str(nbytes)

def truncate(text, width, pad=False):
    if len(text) > width:
        text = text[:width-1] + "…"
    if pad:
        text = "%-*s" % (width, text)
    return text

def get_uri_filename(uri):
    vec = uri.split("/")
    return unquote("-".join(vec[1:]))

def colored(c, s):
    return "\033[%sm%s\033[m" % (c, s)

def get_screen_size_wxh():
    def GWINSZ(fd):
        import fcntl, termios, struct
        try:
            cr = struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "\0\0\0\0"))
        except:
            return None
        else:
            return cr

    cr = GWINSZ(0) or GWINSZ(1)

    return cr[1], cr[0]

class Block():
    Full    = "█"
    Lower   = " ▁▂▃▄▅▆▇█"
    Shade   = " ░▒▓█"
    Rect    = "▯▮"

class Glyph():
    Check   = "✅✓✔"
    Cross   = "✕✖✗✘"
    Up      = "↑⇈"
    Down    = "↓⬇↻⇅⇊"

class Color():
    Red     = 31
    Green   = 32
    Yellow  = 33
    Blue    = 34
    Magenta = 35
    Cyan    = 36
    White   = 37

class Invisible(object):
    def __init__(self, text=""):
        self.text = str(text)

    def __repr__(self):
        return "Invisible(%r)" % self.text

    def __str__(self):
        return self.text

    def __len__(self):
        return 0

class Format(Invisible):
    def __init__(self, text=""):
        if isinstance(text, list):
            self.text = ";".join(text)
        else:
            self.text = str(text)

    def __repr__(self):
        return "Format(%r)" % self.text

    def __str__(self):
        return "\033[%sm" % self.text

class Item(list):
    def __repr__(self):
        return "Item(%r)" % list(self)

    def __str__(self):
        return "".join(str(x) for x in self)

    def __len__(self):
        return sum(len(x) for x in self)

    def __add__(self, other):
        if isinstance(other, list):
            return Item(list(self) + list(other))
        else:
            return NotImplemented
            #return str(self) + str(other)

    def __radd__(self, other):
        if isinstance(other, list):
            return Item(list(other) + list(self))
        else:
            return NotImplemented
            #return str(other) + str(self)

    def __iadd__(self, other):
        if isinstance(other, list):
            self.extend(list(other))
        else:
            self.append(other)
        return self

    @property
    def plain(self):
        return "".join(str(x) for x in self if not isinstance(x, Invisible))

    def padding(self, width):
        return " " * max(0, width - len(self))

    def lpad(self, width):
        return Item([self.padding(width)] + self)

    def rpad(self, width):
        return Item(self + [self.padding(width)])

class Interface(object):
    def __init__(self):
        self.last_id = None
        self.last_kind = None

    def display_progress(self, reqid, cooldown=False, failed=False):
        if cooldown and not (self.last_id == reqid and self.last_kind == "progress"):
            return

        screen_width, _ = get_screen_size_wxh()
        remaining_width = screen_width

        data = c.data[reqid]

        num_total   = int(data["Total"])
        num_needed  = int(data["Required"])
        num_success = int(data["Succeeded"])
        num_failed  = int(data["Failed"])

        job_type    = data.get("JobType", "get")
        realtime    = data.get("RealTime", "false") == "true"

        progress    = num_success / num_needed
        failures    = num_failed / (num_total - num_success) if num_total > num_success else 0

        # create items

        bar_width    = math.floor(screen_width / 3)
        bar_color_fg = Color.Green
        bar_color_bg = None

        i_progress  = math.floor(progress * bar_width)
        i_failures  = math.ceil(failures * bar_width)

        if job_type == "put":
            bar_color_fg = Color.Cyan
        elif not data.get("FinalizedTotal", "false") == "true":
            bar_color_fg = Color.Blue
        elif failed:
            bar_color_bg = Color.Red
        elif cooldown:
            bar_color_fg = Color.Yellow
        else:
            bar_color_fg = Color.Green

        item_failbar = Item([Format("31"),
                             "…" * i_failures,
                             Format()])

        item_mainbar = Item([Format(bar_color_fg),
                             Block.Shade[4] * i_progress,
                             Format(bar_color_bg or bar_color_fg),
                             Block.Shade[1] * (bar_width - i_progress),
                             Format()])

        remaining_width -= len(item_mainbar)

        # create numeric indicators

        if job_type == "get":
            arrow = Glyph.Down[4 if realtime else 0]
        elif job_type == "put":
            arrow = Glyph.Up[1 if realtime else 0]

        _indicator_ = lambda color, char, num: \
                      Item([str(num), Format(color), char, Format()])

        item_remain  = _indicator_(Color.Yellow,
                                   arrow,
                                   num_needed - num_success)

        item_success = _indicator_(Color.Green,
                                   Glyph.Check[2],
                                   num_success)

        item_failed  = _indicator_(Color.Red,
                                   "!",
                                   num_failed)

        item_indicators = Item()
        if remaining_width >= 37:
            item_indicators += item_remain.lpad(6)
        if remaining_width >= 45:
            item_indicators += item_success.lpad(6)
        if remaining_width >= 60:
            item_indicators += item_failed.lpad(6)

        remaining_width -= len(item_indicators)

        # create progress indicator

        tmp_progress = math.ceil(progress * 1000)
        if tmp_progress == 1000:
            str_progress = "100%"
        else:
            str_progress = "%.1f%%" % (tmp_progress / 10)

        item_progress = Item(["%6s" % str_progress])

        remaining_width -= len(item_progress)

        # create reqid item

        item_rightside = Item(item_indicators + [" "] + item_mainbar + item_progress)

        remaining_width -= len(" ")

        id_short = truncate(reqid, remaining_width, pad=True)

        # create final output

        item_status = Item([id_short] + item_indicators + [" "])

        row = Item()
        if self.last_id == reqid and self.last_kind == "progress":
            row += Invisible("\033[2F" "\033[G" "\033[K")
        row += " " * len(item_status)
        row += item_failbar
        row += "\n"
        row += item_status
        row += item_mainbar
        row += item_progress

        print(row)

        self.last_id = reqid
        self.last_kind = "progress"

    def putstatus(self, reqid, status, comment=None, color=""):
        items = ['\033[1;%sm%s\033[m' % (color, reqid),
                 '\033[%sm%s\033[m' % (color, status)]
        if comment:
            items.append("(%s)" % comment)

        if not (self.last_id == reqid and self.last_kind == status):
            print()
        print(*items)
        self.last_id, self.last_kind = reqid, "status"

    def puts(self, reqid, *args):
        print(*args)
        self.last_id, self.last_kind = reqid, "status"

class Message(dict):
    def __init__(self, name=None, **kwargs):
        self.name = name
        for k, v in kwargs.items():
            k = k.replace("_", ".")
            self[k] = v

    def __str__(self):
        out = "%s\n" % self.name
        for k, v in self.items():
            if type(v) == bool:
                v = "true" if v else "false"
            out += "%s=%s\n" % (k, v)
        out += "EndMessage\n"
        return out

    def __repr__(self):
        fields = ["%s=%r" % (k, v) for k, v in self.items()]
        fields.sort()
        return "<[%s]: %s>" % (self.name, ", ".join(fields))

    @property
    def name(self):
        return self["!Name"]

    @name.setter
    def name(self, value):
        self["!Name"] = value

    @property
    def s(self):
        return str(self)

    @property
    def b(self):
        return str(self).encode("utf-8")

    @classmethod
    def parse(self, raw):
        raw = raw.splitlines()
        msg = self()
        for i, line in enumerate(raw):
            if i == 0:
                msg.name = line
            elif line == "EndMessage":
                break
            else:
                k, v = line.split("=", 1)
                msg[k] = v
        return msg

class QueuedMessage(object):
    def __init__(self, message, events):
        self.message = message
        self.events = events

class Client(object):
    def __init__(self, name="PyFreenet"):
        self._dda_cleanup = []
        self.dda_path = None
        self.dda_can_read = False
        self.dda_can_write = False
        self.dda_queue = []
        self.queue = []
        self.data = dict()
        self.waiting = set()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", socket.getservbyname("freenet-fcp")))
        self.bufio = self.sock.makefile("rw")
        self.reader = self.recvall()
        self.send(Message("ClientHello",
                Name=name,
                ExpectedVersion="2.0"))

    def send(self, msg):
        if DEBUG: print("sending:", msg.s)
        self.bufio.write(msg.s)
        self.bufio.flush()

    def sendall(self, msgv):
        for msg in msgv:
            if DEBUG: print("sending:", msg.s)
            self.bufio.write(msg.s)
        self.bufio.flush()

    def recv(self):
        for msg in self.recvall(limit=1):
            return msg

    def recvall(self, limit=None):
        first = True
        msg = None
        count = 0
        for line in self.bufio:
            line = line.rstrip("\n")
            if first:
                first = False
                msg = Message(line)
            elif line == "EndMessage":
                if DEBUG: pp(msg), print(), print()
                yield msg
                count += 1
                if limit and count >= limit:
                    return
                first = True
                msg = None
            elif "=" in line:
                k, v = line.split("=", 1)
                msg[k] = v
            else:
                print("Malformed line: %r" % line)

    def enable_dda(self, path):
        if path.endswith("/"):
            path = path[:-1]
        self.dda_path = path

        c.send(Message("TestDDARequest",
                Directory=path,
                WantReadDirectory=True,
                WantWriteDirectory=True))
        self.add_wait("dda", path)

    def handle_response(self, msg):
        if msg.name == "TestDDAReply":
            out = Message("TestDDAResponse",
                    Directory=msg["Directory"])
            if "ReadFilename" in msg:
                with open(msg["ReadFilename"], "r") as fh:
                    out["ReadContent"] = fh.read()
            if "WriteFilename" in msg:
                with open(msg["WriteFilename"], "w") as fh:
                    fh.write(msg["ContentToWrite"])
                self._dda_cleanup.append(msg["WriteFilename"])
            self.send(out)
        elif msg.name == "TestDDAComplete":
            self.dda_path = msg["Directory"]
            self.remove_wait("dda", self.dda_path)
            while self._dda_cleanup:
                os.unlink(self._dda_cleanup.pop())
            self.dequeue_messages("dda-enabled")

    def queue_messages(self, messages, events):
        for msg in messages:
            self.queue.append(QueuedMessage(msg, events.copy()))

    def dequeue_messages(self, event):
        for qmsg in self.queue[:]:
            if event not in qmsg.events:
                continue
            qmsg.events.discard(event)
            if not qmsg.events:
                self.send(qmsg.message)
                self.queue.remove(qmsg)

    def add_wait(self, *args):
        self.waiting.add(args)

    def remove_wait(self, *args):
        self.waiting.discard(args)

    def waiting_for(self, reqid):
        return (... in self.waiting) or (reqid in self.waiting)

    def update(self, msg, **extra):
        reqid = msg["Identifier"]
        if reqid in self.data:
            self.data[reqid].update(msg)
        else:
            self.data[reqid] = msg.copy()

        if extra:
            self.data[reqid].update(extra)

        return self.data[reqid]

    def forget(self, reqid):
        if reqid in self.data:
            del self.data[reqid]

class Want(object):
    SimpleProgress      = 1 << 0
    SendingToNetwork    = 1 << 1
    CompatibilityMode   = 1 << 2
    ExpectedHashes      = 1 << 3
    ExpectedMIME        = 1 << 5
    ExpectedDataLength  = 1 << 6

def add_downloads(uris, queue=False):
    global get_options
    global self_initiated_get_ids

    msgs = []
    ids = set()
    for uri in uris:
        filename = get_uri_filename(uri)
        reqid = "foo-%s" % filename
        ids.add(reqid)
        msg = Message("ClientGet",
                      URI=uri,
                      Identifier=reqid,
                      Filename=os.path.join(c.dda_path, filename),
                      Verbosity=fetchverbosity,
                      **get_options)
        msgs.append(msg)
    if queue:
        c.queue_messages(msgs, {"dda-enabled"})
    else:
        c.sendall(msgs)
    self_initiated_get_ids |= ids
    return ids

def del_downloads(ids):
    msgs = []
    for reqid in ids:
        msg = Message("RemoveRequest",
                      Identifier=reqid,
                      Global="true")
        msgs.append(msg)
    c.sendall(msgs)
    return set(ids)

fetchverbosity = Want.SimpleProgress | Want.ExpectedHashes

opt_watch_ids = set()
opt_download_uris = []
opt_cancel_ids = set()
opt_get_options = dict()
opt_get_persistent = False

self_initiated_get_ids = set()

args = sys.argv[1:]
if args:
    uri_prefix = "http://localhost:8888/"
    uri_scheme = "freenet:"
    def is_url(text):
        return text.startswith((uri_prefix, uri_scheme, "CHK@", "KSK@", "SSK@", "USK@"))
    for arg in args:
        if is_url(arg):
            if arg.startswith(uri_prefix):
                arg = arg[len(uri_prefix):]
            if arg.startswith(uri_scheme):
                arg = arg[len(uri_scheme):]
            opt_download_uris.append(arg)
        elif arg == "+persist":
            opt_get_persistent = True
        elif arg.startswith("+"):
            k, v = arg[1:].split("=", 1)
            opt_get_options[k] = v
        elif "=" in arg:
            k, v = arg.split("=", 1)
            if k == "cancel":
                opt_cancel_ids.add(v)
        else:
            opt_watch_ids.add(arg)

get_options = dict(PriorityClass="4",
                   RealTimeFlag="true")
if opt_get_persistent:
    get_options.update(dict(
        Global="true",
        Persistence="reboot",
        ReturnType="disk",
    ))
else:
    get_options.update(dict(
        Persistence="connection",
        ReturnType="none",
    ))
get_options.update(opt_get_options)

ui = Interface()

c = Client("PyFreenet" if opt_download_uris else "PyFreenet-monitor-%d" % os.getpid())
c.send(Message("WatchGlobal"))
c.enable_dda("/home/grawity/Private/freenet/downloads")

if opt_download_uris:
    opt_watch_ids |= add_downloads(opt_download_uris, queue=True)

if opt_cancel_ids:
    opt_watch_ids |= del_downloads(opt_cancel_ids)

if opt_watch_ids:
    c.waiting |= opt_watch_ids
else:
    c.waiting.add(...)

def main():
    for msg in c.recvall():
        reqid = msg.get("Identifier", None)

        if msg.name in {
            "CompatibilityMode",
            #"ExpectedHashes",
            "ExpectedMIME",
            "NodeHello",
            "PersistentRequestModified",
            "SendingToNetwork",
        }:
            pass

        elif msg.name == "CloseConnectionDuplicateClientName":
            ui.puts(None, "Closing connection (duplicate client name)")

        elif msg.name == "DataFound":
            if c.waiting_for(reqid):
                c.waiting.discard(reqid)
                ui.putstatus(reqid, "downloaded", color=Color.Green)

        elif msg.name == "GetFailed":
            if c.waiting_for(reqid):
                c.waiting.discard(reqid)
                fatal = msg["Fatal"] == "true"
                if reqid in c.data:
                    ui.display_progress(reqid, failed=True)
                if "RedirectURI" in msg:
                    ui.putstatus(reqid, "redirected", msg["CodeDescription"], color=Color.Yellow)
                    ui.puts(reqid, "  Redirect: %s" % msg["RedirectURI"])
                    if reqid in self_initiated_get_ids:
                        c.waiting |= add_downloads([msg["RedirectURI"]])
                else:
                    #color = Color.Red if fatal else Color.Yellow
                    ui.putstatus(reqid, "failed", msg["CodeDescription"], color=Color.Red)
                    codes = {key.split(".")[1] for key in msg if key.startswith("Errors.")}
                    for code in codes:
                        count = int(msg["Errors.%s.Count" % code])
                        desc = msg["Errors.%s.Description" % code]
                        ui.puts(reqid, "  %4d: %s" % (count, desc))

        elif msg.name == "EnterFiniteCooldown":
            if c.waiting_for(reqid):
                ui.display_progress(reqid, cooldown=True)
                if reqid in c.waiting:
                    ui.putstatus(reqid, "in cooldown", color=Color.Yellow)

        elif msg.name == "ExpectedDataLength":
            c.update(msg)
            if reqid in c.waiting:
                size = int(msg["DataLength"])
                ui.putstatus(reqid, "size: %s" % format_size(size))

        elif msg.name == "ExpectedHashes":
            c.update(msg)
            if reqid in c.waiting:
                ui.putstatus(reqid, "hashes found")
                algos = {key.split(".")[1] for key in msg if key.startswith("Hashes.")}
                for algo in sorted(algos):
                   ehash = msg["Hashes.%s" % algo]
                   ui.puts(reqid, "  %s: %s" % (algo, ehash))

        elif msg.name == "IdentifierCollision":
            ui.putstatus(reqid, "already queued", color=Color.Yellow)

        elif msg.name == "PersistentGet":
            known = reqid in c.data
            c.update(msg, JobType="get")
            if c.waiting_for(reqid) and not known:
                ui.putstatus(reqid, "downloading", color=Color.Blue)

        elif msg.name == "PersistentPut":
            known = reqid in c.data
            c.update(msg, JobType="put")
            if c.waiting_for(reqid) and not known:
                ui.putstatus(reqid, "inserting", color=Color.Blue)

        elif msg.name == "PersistentRequestRemoved":
            c.forget(reqid)
            if c.waiting_for(reqid):
                ui.putstatus(reqid, "removed", color=Color.Yellow)
                c.waiting.discard(reqid)

        elif msg.name == "ProtocolError":
            ui.putstatus(reqid, "protocol error: %s" % msg["CodeDescription"], color=Color.Red)
            ui.puts(reqid, "  %s" % msg["ExtraDescription"])
            if reqid and c.waiting_for(reqid):
                c.waiting.discard(reqid)

        elif msg.name == "PutSuccessful":
            c.update(msg)
            if c.waiting_for(reqid):
                ui.putstatus(reqid, "inserted", color=Color.Green)
                ui.puts(reqid, "  URI: %s" % msg["URI"])
                c.waiting.discard(reqid)

        elif msg.name == "SimpleProgress":
            c.update(msg)
            if c.waiting_for(reqid):
                ui.display_progress(reqid)

        else:
            c.handle_response(msg)

        if not c.waiting:
            break

try:
   main()
except KeyboardInterrupt:
   sys.exit()
