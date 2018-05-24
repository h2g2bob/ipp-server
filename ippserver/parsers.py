from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import struct

def read_struct(f, fmt):
    sz = struct.calcsize(fmt)
    string = f.read(sz)
    return struct.unpack(fmt, string)

def write_struct(f, fmt, *args):
    data = struct.pack(fmt, *args)
    f.write(data)

class Value(object):
    @classmethod
    def from_bytes(cls, _data):
        raise NotImplementedError()
    def bytes(self):
        raise NotImplementedError()
    def __bytes__(self):
        return self.bytes()

class Boolean(Value):
    def __init__(self, value):
        assert type(value) is bool
        self.boolean = value
        Value.__init__(self)
    @classmethod
    def from_bytes(cls, data):
        val, = struct.unpack(b'>b', data)
        return cls([False, True][val])
    def bytes(self):
        return struct.pack(b'>b', 1 if self.boolean else 0)

class Integer(Value):
    def __init__(self, value):
        assert type(value) is int
        self.integer = value
        Value.__init__(self)
    @classmethod
    def from_bytes(cls, data):
        val, = struct.unpack(b'>i', data)
        return cls(val)
    def bytes(self):
        return struct.pack(b'>i', self.integer)

class Enum(Integer):
    pass
