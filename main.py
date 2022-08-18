import sys
import socket
import os
import random
import string
import time


class Server():
    def __init__(self, port):
        self.location = os.getcwd()
        self.port = port
        self.users = []
        self.user_path = ''
        self.path = os.getcwd()
        self.time = ''
        self.serial = ''
        self.is_new = False
        self.current_directory = ''
        self.main_folder_on_server = ''
        self.client_socket = ''
        self.current_client_name = ''
        self.clients_book = {}  # ->  # self.serial: {self.current_client_name: []}
        self.originals = []

    def print_server(self):
        print(f'location: {self.location}')
        print(f'path: {self.path}')
        print(f'user_path: {self.user_path}')
        print(f'current_directory: {self.current_directory}')
        print(f'main_folder_on_server: {self.main_folder_on_server}')

        # send dirs to server to write folders

    def send_dirs(self, path, dirs, client_socket):
        if len(dirs) == 0:
            text = "no dirs"
            message_size = str(len(text)).zfill(10)
            client_socket.send(bytes(message_size, encoding='utf-8'))
            # client_socket.recv(3)  # get the ok
            client_socket.send(b'no dirs')
            # client_socket.recv(3)  # waiting for ok message
            return
        folder_path = path[len(self.path):]
        if folder_path == "":
            folder_path = self.serial
        text_to_send = ""
        for dir in dirs:
            text_to_send += dir + SEPERATOR
        text_to_send += folder_path
        message_size = str(len(text_to_send)).zfill(10)  # get the message size
        client_socket.send(bytes(message_size, encoding='utf-8'))  # send the length of the new message
        client_socket.send(bytes(text_to_send, encoding='utf-8'))  # sending folders to write at serve

    def send_folders_to_client(self, client_socket):
        for path, dirs, files in os.walk(self.path + '/' + self.serial, topdown=True):
            # sending folders to create at client
            self.send_dirs(path, dirs, client_socket)
            # at this point client created all folders
            # starting sending files to client
        text = "done"
        message_length = str(len(text)).zfill(10)  # send the message size
        client_socket.send(bytes(message_length, encoding='utf-8'))  # send the text info
        client_socket.send(b'done')
        # print("finished sending folders to client")

    # create new serial randomly to users that don't have serial number
    # need to return to original state
    def checkSerial(self):
        # check if serial number is 128X0000 if so supply new random
        if self.serial == '0' * 128:
            self.is_new = True
            newId = ""
            newId = 'G8xIhhRv4YxiBu67nKFJF1U5DDKkBUjhQZ1GCFeSnw9M4gDWs3HE7ZwtSrMQU2JA4tTgUtZUhYkbRofgHNLKwPc1EuXkwyZvozcjlY0cCXghyqXRNwOV48GJvQ8AFm8k'
            # bag = string.ascii_letters
            # bag += string.digits
            # for i in range(128):
            #     newId += bag[random.randint(0, len(bag) - 1)]
            self.serial = newId
            self.current_directory = self.path + '/' + self.current_directory

    # function that handles the folder text
    def handle_folders(self, text):
        if text == 'no dirs':
            return
        # split the text
        text_splited = text.split(SEPERATOR)
        # print(text_splited)
        # get the main folder as field
        main_folder = text_splited.pop()
        # if it's new directory
        if self.is_new:
            # create new dir with the main folder
            os.makedirs(main_folder)
            # print("creating folder :" + main_folder)
            # change directory
            os.chdir(main_folder)
            # get the path to the current directory
            self.path = os.getcwd()
            # iterate through the folders in the text files
            for folder in text_splited:
                # create folders - another function
                os.makedirs(folder)
            # set new directory to False
            self.is_new = False
        else:
            # change dir to the main folder
            os.chdir(self.path + main_folder)
            # make dirs
            for folder in text_splited:
                try:
                    os.makedirs(folder)
                except FileExistsError:
                    print(f'got error with folder {folder}')
        text_splited.clear()

    # create new folder at server side, creating all sub-folders
    def create_new_folder(self, client):
        while True:
            message_size = client.recv(10).decode()  # get the size of the message, max size of digits is 10
            # print("message size is " + message_size)  # sending message size
            folder_text = client.recv(int(message_size))
            # print(folder_text)
            folder_text = folder_text.decode()  # getting the folders info
            if folder_text == 'done':
                break
            self.handle_folders(folder_text)  # handle folder_text, creating folders

    # function that gets the new files to the server
    def get_new_files(self, client_socket):
        while True:
            message_size_before = client_socket.recv(10)  # get the size of the message, max size of digits is 10
            # print(message_size_before)
            message_size = message_size_before.decode()
            # print("message size is " + message_size)  # sending message size
            files_text = ""
            files_text += client_socket.recv(int(message_size)).decode()  # getting the files info
            if files_text == 'done':
                break
            self.handle_files(files_text, client_socket)  # handle folder_text, creating folders

    def send_files_to_client(self, client_socket):
        for path, dirs, files in os.walk(self.path + '/' + self.serial, topdown=True):
            for file in files:
                text_to_send = path + SEPERATOR
                text_to_send += file + SEPERATOR + str(
                    os.path.getsize(path + '/' + file)) + SEPERATOR  # get the file info
                message_length = str(len(text_to_send)).zfill(10)
                client_socket.send(bytes(message_length, encoding='utf-8'))  # send the text length
                client_socket.send(bytes(text_to_send, encoding='utf-8'))  # send the text info
                with open(path + '/' + file, 'rb') as file:
                    data = file.read()
                    client_socket.send(data)  # send data file

        text = 'done'
        message_length = str(len(text)).zfill(10)
        client_socket.send(bytes(message_length, encoding='utf-8'))  # send the text length
        client_socket.send(b'done')

    # function that handle file - after getting info from text (one file only)
    def handle_files(self, text, client_socket):
        # split, pop as usual
        files_list = text.split(SEPERATOR)
        files_list.pop()
        # print(f'files_list: {files_list}')
        # if file path is the main directory
        file_path = files_list.pop(0)[len(self.user_path):]
        # means main folder
        if file_path == "":
            # convert main directory to self.path
            file_path = self.path
        else:
            # if its not in main directory put it where it belongs lol
            backup_path = file_path
            file_path = self.path + '/' + backup_path
        # print("waiting for " + files_list[1] + " data")
        total_size_file_to_get = files_list[1]
        data = client_socket.recv(int(files_list[1]))  # because file list is [text.txt,10]
        # print("sent ok message for the file")
        # write file
        total_size = int(total_size_file_to_get)
        with open(file_path + '/' + files_list[0], 'wb') as file:
            while total_size > 0:
                file.write(data)
                total_size -= len(data)
                data = client_socket.recv(total_size)
            file.close()

    def handle_command(self, text):
        # save text in dictionary
        computers = self.clients_book[self.serial]
        text_splitted = text.split(SEPERATOR)
        command = text_splitted[0]
        for computer in computers:
            if self.current_client_name in computer.keys():
                if command == "moved":
                    computer[self.current_client_name].append(
                        text_splitted[0] + SEPERATOR + text_splitted[1][len(self.user_path):] + SEPERATOR +
                        text_splitted[2][len(self.user_path):])
                else:
                    computer[self.current_client_name].append(
                        text_splitted[0] + SEPERATOR + text_splitted[1][len(self.user_path):])

        if command == 'delete':
            file_to_delete = text_splitted[1][len(self.user_path):]
            self.delete_function(file_to_delete)

        elif command == 'created':
            path = text_splitted[1][len(self.user_path):]  # getting the path to write the files
            self.create_function(path)

        elif command == 'moved':
            path_to_delete = text_splitted[1][len(self.user_path):]  # getting the path
            path_to_write = text_splitted[2][len(self.user_path):]
            self.move_function(path_to_delete, path_to_write)

    def create_function(self, path_to_write):
        total_size = int(self.client_socket.recv(10).decode())  # getting the size of the file
        data = self.client_socket.recv(total_size)  # getting first data
        print(f'path to write is {path_to_write}')
        fPath = self.path+os.sep+self.serial+path_to_write
        with open(fPath, 'wb') as file:
            while total_size > 0:  # for big files
                file.write(data)
                total_size -= len(data)
                data = self.client_socket.recv(total_size)
            file.close()

    def deleteFolder(self, path_to_remove_dir):
        for root, directories, files in os.walk(path_to_remove_dir, topdown=False):
            # remove files
            for name in files:
                os.remove(os.path.join(root, name))
            for name in directories:
                os.rmdir(os.path.join(root, name))
        os.rmdir(path_to_remove_dir)

    def delete_function(self, path_to_delete):
        try:
            print(f'path in the beginning is  {path_to_delete}')
            path_to_delete_file = self.location + os.sep + self.serial + path_to_delete
            if os.path.isdir(path_to_delete_file):
                print(f'in dir')
                self.deleteFolder(path_to_delete_file)
            else:
                print(f'deleting {path_to_delete_file}')
                os.remove(path_to_delete_file)
            print("file/dir removed")
        except FileExistsError:
            return
        except FileNotFoundError:
            return

    def move_function(self, path_to_delete, path_to_write):
        self.create_function(path_to_write)
        self.delete_function(path_to_delete)

    # main loop
    def main_loop(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket
        server_socket.bind(('', self.port))
        server_socket.listen()
        while True:
            client_socket, client_address = server_socket.accept()
            self.client_socket = client_socket
            mode = self.client_socket.recv(2).decode()  # get the mode from the server
            if mode == '01':
                self.serial = client_socket.recv(128).decode('utf-8')  # get the serial number from the client
                self.checkSerial()  # check if serial number is valid
                client_socket.send(bytes(self.serial, encoding='utf-8'))  # send the new serial number

                message_size = client_socket.recv(10).decode()  # get the text_length for user path
                self.user_path = client_socket.recv(int(message_size)).decode()  # get the user path

                message_size = str(len(self.path)).zfill(10)
                client_socket.send(bytes(message_size, encoding='utf-8'))  # send text_length length to server
                client_socket.send(bytes(self.path, encoding='utf-8'))  # send text_length length to server

                message_size = client_socket.recv(10).decode()  # get the time length
                self.time = client_socket.recv(int(message_size)).decode()  # get time

                message_size = int(client_socket.recv(10).decode())  # get the name of the client
                self.current_client_name = client_socket.recv(message_size).decode()  # save him

                if self.is_new:
                    print("New ID: " + self.serial)
                    self.create_new_folder(client_socket)  # create new folder at server sid
                    self.get_new_files(client_socket)  # copy the files to the server
                    self.clients_book[self.serial] = [{self.current_client_name: []}]  # add client to clients book
                    self.path = self.location  # add the position to the server
                    self.originals.append(self.current_client_name)  # add the client original to the clients book

                else:
                    # sending files to client
                    self.main_folder_on_server = self.serial  # add the main folder as the serial
                    self.send_folders_to_client(client_socket)  # send folders to client
                    self.send_files_to_client(client_socket)  # send files to client
                    self.path = self.location  # put self.path as the self.location

                    try:  # try to add the client to the clients book
                        self.clients_book[self.serial].append({self.current_client_name: []})
                    except KeyError:
                        self.clients_book[self.serial] = [{self.current_client_name: []}]
                # print(self.clients_book)
                self.client_socket.close()

            elif mode == '02':  # means client is updating the server about changing
                self.serial = client_socket.recv(128).decode('utf-8')  # get the serial number from the client
                message_size = client_socket.recv(10).decode()  # get the text_length for user path
                self.user_path = client_socket.recv(int(message_size)).decode()  # get the user path
                message_size = int(client_socket.recv(10).decode())  # get the name of the client
                self.current_client_name = client_socket.recv(message_size).decode()  # save him

                if self.current_client_name not in self.originals:  # if client is not original add the path as
                    # user_path
                    self.user_path = self.user_path + os.sep + self.serial
                watchdog_command_length = client_socket.recv(10)  # get the command which need to update at server
                command_length = int(watchdog_command_length.decode())
                command = client_socket.recv(command_length).decode()  # get the command
                self.handle_command(command)  # calling command
                self.client_socket.close()  # close the socket

            elif mode == '03':  # client connects to get updates
                self.serial = client_socket.recv(128).decode('utf-8')  # get the serial number from the client
                message_size = client_socket.recv(10).decode()  # get the text_length for user path
                self.user_path = client_socket.recv(int(message_size)).decode()  # get the user path
                message_size = int(client_socket.recv(10).decode())  # get the name of the client
                self.current_client_name = client_socket.recv(message_size).decode()
                if self.current_client_name in self.originals:  # if client socket is new send him 01 else 02
                    self.client_socket.send(b'01')
                else:
                    self.client_socket.send(b'02')
                # sending the commands to client
                dictionary_computers = self.clients_book[self.serial]  # gets the id dict

                for computer in dictionary_computers:  # get the list of the computers ids
                    if self.current_client_name in computer.keys():  # iterate through the computers
                        continue
                    commands_list = None
                    for key in computer.keys():  # get the command of the current computer
                        print(f'for {key}')
                        commands_list = computer[key]
                    print(f'command list is {commands_list}')
                    for command in commands_list:  # sending the commands to client
                        message_size_text = str(len(command)).zfill(10)
                        self.client_socket.send(bytes(message_size_text, encoding='utf-8'))  # send the length of the
                        # command
                        try:
                            self.client_socket.send(bytes(command, encoding='utf-8'))  # send the command to client
                        except ConnectionResetError as e:
                            print(f'got error {e}')

                # gets the text
                text_done = 'done'
                print(f'sending done length')
                message_size_text = str(len(text_done)).zfill(10)
                self.client_socket.send(bytes(message_size_text, encoding='utf-8'))  # send the length of the
                self.client_socket.send(b'done')
                self.client_socket.close()

            elif mode == '04':  # server needs to send file to client
                self.serial = self.client_socket.recv(128).decode()
                message_size = self.client_socket.recv(10).decode()  # get the text_length for user path
                prev_file_path = self.client_socket.recv(int(message_size)).decode()  # get the user path file
                print(f'prev file path {prev_file_path}')
                file_path = self.path + os.sep + self.serial + prev_file_path  # get the file path on server
                file_size = os.path.getsize(file_path)  # get the file size
                file_length_to_send = str(file_size).zfill(10)
                self.client_socket.send(str.encode(file_length_to_send))  # send to client the size of the path
                print(f'file path is {file_path}')
                with open(file_path, 'rb') as file:  # send file to client
                    data = file.read()
                    self.client_socket.send(data)
                file.close()
                self.client_socket.close()

            elif mode == '05':  # server needs to get folders from client (create_folder), getting folders only
                self.serial = self.client_socket.recv(128).decode()
                message_size = self.client_socket.recv(10).decode()  # get the user path
                self.user_path = self.client_socket.recv(int(message_size))
                # need to get computer name
                message_size = self.client_socket.recv(10).decode()
                self.current_client_name = self.client_socket.recv(int(message_size)).decode()  # get the client name
                command_name = "create_folder"
                while True:  # getting folders
                    try:
                        message_size = int(self.client_socket.recv(10).decode())
                        text = self.client_socket.recv(message_size).decode()  # get the folder path from server
                        if text == "no dirs":
                            continue
                        if text == "done":
                            self.client_socket.close()
                            break
                        if self.current_client_name not in self.originals:
                            realtive_path = text[len(self.user_path)+129:] # get relative path over the id
                        else:
                            realtive_path = text[len(self.user_path):]  # get the realtive path of the folder
                        if realtive_path == "":  # means noo dirs
                            continue
                        server_path_to_create_folder = self.path + os.sep + self.serial + realtive_path
                        print(f'created folder: {server_path_to_create_folder}')
                        # adding the command to the commands lists of clients
                        computers = self.clients_book[self.serial]
                        for computer in computers:
                            if self.current_client_name in computer.keys():
                                # add the command to the list
                                computer[self.current_client_name].append(command_name + SEPERATOR + realtive_path)
                                print(f'adding {command_name + SEPERATOR + realtive_path}')
                        os.makedirs(server_path_to_create_folder)
                    except ValueError as e:
                        print(e)
                        break
                    except FileExistsError as e:
                        print(e)
                        break


SEPERATOR = "$"
try:
    PORT = int(sys.argv[1])
except Exception:
    print("wrong port")
try:
    server = Server(PORT)
    server.main_loop()
except KeyboardInterrupt:
    print("Existing")
    print(server.clients_book)
