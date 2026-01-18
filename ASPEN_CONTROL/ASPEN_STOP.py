'''
(c) 2025 Politecnico di Milano

   ###       #####     #####      #######    #     # 
  #   #     #     #    #    #     #          ##    # 
 #     #    #          #    #     #          # #   # 
 #######     #####     #####      #####      #  #  # 
 #     #          #    #          #          #   # # 
 #     #    #     #    #          #          #    ## 
 #     #     #####     #          #######    #     # 

  #####     #######     #####     #####   
 #     #       #       #     #    #    #  
 #             #       #     #    #    #  
  #####        #       #     #    #####   
       #       #       #     #    #       
 #     #       #       #     #    #       
  #####        #        #####     #
 
'''

import socket

# Server configuration
SERVER_IP = "192.168.4.1"  # IP address of the Access Point created by Arduino
SERVER_PORT = 80           # Server port
BUFFER_SIZE = 1024         # Maximum buffer size for receiving messages

def main():
    # Create a socket to connect to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            print(f"Connecting to server {SERVER_IP}:{SERVER_PORT}...")
            client_socket.connect((SERVER_IP, SERVER_PORT))
            print("Connection established.")

            # Immediately send the bit '0' to the server
            bit = "0"
            message = f"bit={bit}"
            client_socket.sendall(message.encode())
            print(f"Sent: {message}")

            # Receive a confirmation from the server
            response = client_socket.recv(BUFFER_SIZE).decode()
            print(f"Server response: {response}")

        except Exception as e:
            print(f"Error during communication: {e}")
        finally:
            print("Connection closed.")

if __name__ == "__main__":
    main()
