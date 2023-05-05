import socket 

HEADSIZE =10
print(" see",socket.AF_INET,socket.SOCK_STREAM,socket.gethostname())
s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("dhcp-v047-111.mobile.uci.edu",1241))
while True:
    full_msg=' '
    new_msg=True 
    while True:
        msg = s.recv(16)
        full_msg+=msg.decode("utf-8")
        print(full_msg[HEADSIZE:])
