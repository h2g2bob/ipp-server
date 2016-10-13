A minimal IPP server
====================


This is a small python script which __pretends to be a printer__.


Does it work
------------

Yes, it works well enough to print documents on my Linux box with CUPS 1.7.5.

It doesn't implement the entire IPP spec: ymmv.


Usage
-----

Start running, saving postscript doucments to a directory:
```
python -m ippserver --port 1234 save /tmp/
```

Add the printer, specifying `ipp://localhost:1234/` as the printer's location.

Instead of saving the doucments, you can send them to a command. For example, send it to [hexdump(1)]:
```
python -m ippserver --port 1234 run hexdump
```

Or email yourself using [mail(1)]:
```
python -m ippserver --port 1234 run \
	mail -E \
	-a "MIME-Version 1.0" -a "Content-Type: application/postscript" \
	-s 'A printed document' some.person@example.com
```



[hexdump(1)]: https://linux.die.net/man/1/hexdump
[mail(1)]:  https://linux.die.net/man/1/mail
