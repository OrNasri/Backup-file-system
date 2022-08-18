# Backup-file-system
project made in Communication Networks course, in Linux.
written in Python using Watchdog library.

#client.py - the client side.
need to run it with arguments:
1. server's IP address
2. server's port
3. directory to monitor and back-up files
4. user's ID (optional) - if it is an existing user - it means that he has an directory created on server. if there is no input, it creates new directory on server and copy the data from the client's directory.

#server.py - the server side.
need to run it with argument:
server's port.

The server accept client by client and listen to changes, gets all the data about the changes from the client. The changes are being notified to the server that updates the directory where the server code appears.
