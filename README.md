Some of the tools here are useful, although mostly specific to my networks and configurations. But expect some crazy shit, too. One might discover three different implementations of an obscure protocol from 1980's or something just as useless.

(Everything is licensed under WTFPL v2 <http://sam.zoy.org/wtfpl/> unless declared otherwise in specific files. I might switch the default license to MIT, but still not sure about it.)

 * `bin` contains symlinks to all scripts, for my $PATH.
 * `dist` has scripts dealing with this repository itself.
 * `obj` is where compiled binaries for C tools go, to allow sharing `~/code` over NFS.
 * `tools` contains stuff that will, some day, be cleaned up and put in the right place.

The useful stuff:

 * `music/gnome-mpris-inhibit` – disable idle-suspend in GNOME while music is playing
 * `music/mpris` – control MPRIS2-capable players
 * `net/tapchown` – change owner of tun/tap network interfaces (Linux)
 * `x11/dbus-name` – list, activate, wait for DBus names
 * `x11/gnome-inhibit` – set and list idle inhibitors in GNOME

The somewhat useful stuff:

 * `misc/motd` – notify about changes in /etc/motd
 * `kerberos/kl` – a better *klist*
 * `kerberos/pklist` – list Kerberos tickets in easy-to-parse form
 * `kerberos/kc` – manage multiple Kerberos credential caches
 * `misc/envcp` – borrow the environment of another process
 * `net/getpaste` – dump raw text of pastebin posts
 * `net/mc-presence` – control Empathy IM status
 * `net/rdt` – recursive rDNS trace
 * `security/git-credential-lib` – read Git credentials from GNOME Keyring or Windows Credential Manager

The not-really-useful stuff:

 * `lib/python/nullroute/authorized_keys` – parse `authorized_keys`
 * `lib/python/nullroute/sexp` – parse Ron Rivest's S-expressions
 * meh
