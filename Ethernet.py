import socket
import sys

# Set IP address and port number according to server IP address and port number
SERVER_IP_ADDRESS = "192.168.1.77"
PORT_NUMBER = 6000
BUFFER_SIZE = 255

def main():
    try:
        # Create a socket object
        # AF_INET: IPv4 address family
        # SOCK_STREAM: TCP socket type
        comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Socket created successfully\n")
        
    except socket.error as err:
        print(f"Socket creation failed with error: {err}")
        sys.exit(1)
    
    try:
        # Connect to the server
        # Tuple format: (IP_ADDRESS, PORT_NUMBER)
        comm_socket.connect((SERVER_IP_ADDRESS, PORT_NUMBER))
        print("Connected to server successfully\n")
        
    except socket.error as err:
        print(f"Could not connect to server with error: {err}")
        comm_socket.close()
        sys.exit(1)
    
    print("Demo program to receive data over LAN\n")
    print("Listening for incoming messages from server...\n")
    
    try:
        while True:
            # Receive data from server
            data = comm_socket.recv(BUFFER_SIZE)
            
            if data:
                print(f"Message received: {data.decode('utf-8')}")
            else:
                print("Server disconnected")
                break
                
    except socket.error as err:
        print(f"Could not receive from server with error: {err}")
    except KeyboardInterrupt:
        print("\n\nReceiving interrupted by user")
    
    # Close the socket connection
    comm_socket.close()
    print("Socket closed. Connection terminated.")

if __name__ == "__main__":
    main()