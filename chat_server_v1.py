import argparse, queue, socket, threading, json, re
import chat_util as cu


# dict to store each client handle and its queue
client_res_queues = {}   # key = sock.fileno, val = q for client socket
client_names = {}        # key = client name, val = sock.fileno
client_idle = {}         # key = client name, val = True / False
lock = threading.Lock()

def handle_disconnect(sock, addr):
  """ Ensure queue is cleaned up and socket closed when a client disconnects """
  fd = sock.fileno()
  with lock:
    # Get send queue for this client
    q = client_res_queues.get(fd, None)

  # If we find a queue then this disconnect has not yet been handled
  if q:
    q.put(None)
    del(client_res_queues[fd])
    addr = sock.getpeername()
    print('Client {} disconnected'.format(addr))
    sock.close()


def broadcast_payload(payload):
  """ Add payload to each connected client's send queue """
  with lock:
    for q in client_res_queues.values():
      q.put(payload)


# func to handle a client request
def client_req_handler(cs, addr):
  client_address = str(addr)
  partial_payload = bytes()
  print("Client connected from: %s" %client_address)

  # receive req and send resp to client
  while True:
    # get request
    try:
      (full_payloads, partial_payload) = cu.get_content_from_payloads(cs, partial_payload)
    except (EOFError, ConnectionError):
      handle_disconnect(cs, addr)
      break

    for payload in full_payloads:
      data = json.loads(payload)
      print("Data: ", data)

      content = data['content']
      contents = re.split(r'\W+', content)
      if data['to'] == 'server':
        if len(contents) > 1:#commands:join and talk
          command = contents[0]
          value = contents[1]
        else:#list and quit
          command=contents[0]
        print("Server command: ", contents)
        if command == 'join':
          if value in client_names:
            resp = cu.createPayload(value,'server','','Name Exists')
          else:
            client_names[value] = cs.fileno()
            client_idle[value] = True
            resp = cu.createPayload(value,'server','Welcome '+ value)
          client_res_queues[cs.fileno()].put(resp)
        elif command == 'list':
          cl = list(client_names.keys())
          cl.remove(data['sender'])
          resp = cu.createPayload(data['sender'],'server', cl)
          client_res_queues[cs.fileno()].put(resp)
        elif command == 'quit':
          del client_names[data['sender']]
          del client_res_queues[cs.fileno()]
          del client_idle[data['sender']]
          break
        elif command == 'status':
          print(client_idle)
        elif command == 'talk':
          if client_idle[value] == True:
            # this client
            client_idle[data['sender']] = False
            resp1 = cu.createPayload(data['sender'], value, 'Start-chat')
            client_res_queues[cs.fileno()].put(resp1)
            # other client
            client_idle[value] = False
            resp2 = cu.createPayload(value, data['sender'],  'Start-chat')
            client_res_queues[client_names[value]].put(resp2)
          else:
            resp = cu.createPayload(data['sender'],'server','', value + ' is Busy')
      else:  # bypass server now and communicate directly
        if contents[0] == 'bye':
          client_idle[data['sender']] = True
          client_idle[data['to']] = True
          client_res_queues[client_names[data['to']]].put(payload)
        else:
          client_res_queues[client_names[data['to']]].put(payload)

        #future use in group membership broadcast_payload(payload)
  cs.close()



# func to handle a client response
def client_res_handler(cs, addr, q):
  """ Monitor queue for new payload, send them to client as they arrive """
  while True:
    payload = q.get()
    if payload == None:
      break

    try:
      cu.send_content(cs, payload)
    except (ConnectionError, BrokenPipe):
      handle_disconnect(sock, addr)
      break



# each new client has
#   its own queue
#     accessed from client_res_queues dict (client socket id, client queue)
#     request handler in a thread
#     response handler in a thread
def new_client(client_sock, addr):
  # create a queue for each client
  client_q = queue.Queue()

  with lock:
    # add each client socket's file descriptor in dict
    client_res_queues[client_sock.fileno()] = client_q

  # multithreaded < single threaded: client_handler(client_sock, addr)
  t_req = threading.Thread(target = client_req_handler,
                           args = [client_sock, addr],
                           daemon = True)
  t_res = threading.Thread(target = client_res_handler,
                           args = [client_sock, addr, client_q],
                           daemon = True)
  t_req.start()
  t_res.start()



def server(port):
  server_sock = cu.create_socket('localhost', port, 5)
  server_addr = server_sock.getsockname()
  try:

    while True:
      print('Server {} waiting for connection...'.format(server_addr))

      # accept a new client
      client_sock, addr = server_sock.accept()
      new_client(client_sock, addr)


    # server shutdown
    server_sock.close()
  except:
    print("Shutting server gracefully")
    server_sock.close()




if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--port', default='12345')
  args = parser.parse_args()
  server(int(args.port))
