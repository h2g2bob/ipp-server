
def read_http(f):
	first_line = f.readine()
	if not first_line.startswith(b'POST / HTTP/'):
		raise ValueError('Invalid request')
	for line in f.readline():
		if line.rstrip(b'\r\n') == '':
			break

def write_http(f):
	f.write(b'\r\n'.join((
		b'HTTP/1.1 200 OK',
		b'Server: ipp-server',
		b'')))
