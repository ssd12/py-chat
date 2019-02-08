import socket, json

cmdList=['join','list','talk','quit','error','genText']


def create_socket(host, port, backlog):
  # create a TCP socket (SOCK_STREAM)
  s = socket.socket(socket.AF_INET,     # socket domain: internet=AF_INET, bluetooth=AF_BLUETOOTH
                  socket.SOCK_STREAM)        # tcp=SOCK_STREAM, udp=SOCK_DGRAM
                  # proto=0           i.e. protocol within socket family
  print('Socket created')

  # make it non blocking i.e multiple clients can interact > server dies immediately
  # server_sock.setblocking(0)
  # server_sock.settimeout(0.5)
  s.setsockopt(
      socket.SOL_SOCKET,
      socket.SO_REUSEADDR,
      1)

  # bind to host, port
  s.bind((host, port))

  # start listening - backlog = no. of unaccepted conns before refusing
  s.listen(backlog)
  return s


# add delimiter based on protocol to content
#   client_sock.send(res.encode('utf-8')) # (bytes(ctime(), 'utf-8')
def send_content(s, c, delimiter = '\0'):
  c += delimiter
  s.sendall(c.encode('utf-8'))


# message is cont so separate using delimiter into
#   full and partial messages
def parse_payloads(mixed_payload, delimiter = b'\0'):
  payloads = mixed_payload.split(delimiter)
  full_payloads = payloads[:-1]    # all complete payloads
  partial_payload = payloads[-1]   # last incomplete payload
  return (full_payloads, partial_payload)

def createPayload(to,sender,content,error=None):
  p={}
  p['to']=to
  p['sender']=sender
  p['content']=content
  p['error']=error
  return json.dumps(p)

# load mixed payload at socket - mixed_payloads passed from prev
# and can contain partial payload
def get_content_from_payloads(s, mixed_payloads, size = 4096, delimiter = b'\0'):
  full_payloads = []
  while not full_payloads:
    payload_batch = s.recv(size)
    if not payload_batch:
      raise ConnectionError()

    mixed_payloads = mixed_payloads + payload_batch
    (full_payloads, partial_payload) = parse_payloads(mixed_payloads, delimiter)

  full_payloads = [payload.decode('utf-8') for payload in full_payloads]
  return (full_payloads, partial_payload)

