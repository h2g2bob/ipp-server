A minimal IPP server
====================


This is a small python script which __pretends to be a printer__.

Currently, it just saves the file into /tmp/, but you could adapt it for other purposes.


Usage
-----

Start running:
```
python -m ipp-server.server 1234
```

Add the printer, specifying `ipp://localhost:1234/` as the printer's location.


Does it work
------------

It doesn't implement all of the IPP spec, but it works well enough to print
the pages on my Linux box with CUPS 1.7.5.
