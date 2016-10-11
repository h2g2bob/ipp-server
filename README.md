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

It works well enough to print the test page on my Linux box with CUPS 1.7.5.

It doesn't implement all of the IPP spec and takes some, er, short-cuts.

There are currently some major omissions. Printing a one-page document works
fine, but printing a document with multiple pages will cause cups to
repeatedly ask for the job status.
