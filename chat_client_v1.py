import argparse, sys, socket, threading, json,re
import chat_util as cu


def handle_client_io(cs):
  global isIdle
  global name
  global to
  isIdle = True
  name = ''
  to = 'server'
  print("Type messages, enter to send. 'quit' to exit  and 'bye' to quit chat")

  while True:
    payload = input() # Blocks
    contents = re.split(r'\W+', payload)
    if len(contents) > 1 and isIdle == True:#commands:join and talk
      command = contents[0]
      if (command == 'join'):
        name = contents[1]


    print("-idle ", isIdle, " -to ", to)
    try:
      if isIdle:
        cu.send_content(cs,cu.createPayload(to, name, payload))
      else:
        cu.send_content(cs,cu.createPayload(to, name, payload))

    except (BrokenPipeError, ConnectionError):
      break

    if payload == 'quit':
      cs.shutdown(socket.SHUT_RDWR)
      cs.close()
      break
    elif payload == 'bye':
      isIdle = True
      to = 'server'



def run_client(host, port):
  try:

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client_sock.connect((host, port))
    print("Connected to {} on port {}".format(host, port))

    # request thread
    t = threading.Thread(target = handle_client_io,
                         args = [client_sock],
                         daemon = True)
    t.start()

    # response
    partial_payload = bytes()
    global isIdle
    global name
    global to

    while True:
      try:
        (full_payloads, partial_payload) = cu.get_content_from_payloads(client_sock, partial_payload)
        for payload in full_payloads:
          data = json.loads(payload)
          print(data)
          if data['error'] != None:
            content = 'Error: '+data['error']
          else:
            content = data['content']
            if content == 'Start-chat':
              isIdle = False
              to = data['sender']
            elif data['content'] == 'bye': # chat between two clients ended
              isIdle = True
              to = 'server'
          print(data['sender'], ' : ',content)
      except ConnectionError:
        print('Connection to server closed')
        client_sock.close()
        break

  except socket.error as err:
    print("Failed to create a socket")
    print("Reason: %s" %str(err))
    sys.exit();


# __name__ is py's init variable
# entry point needs to compare to __main__
# imported module's __name__ is set to module name
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-host', '--host', default='127.0.0.1')
  parser.add_argument('-p', '--port', default='12345')
  args = parser.parse_args()
  run_client(args.host, int(args.port))

