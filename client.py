import struct
import sys
import socket
import os
import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class Client():
    def __init__(self, ip, port, path, time, serial):
        self.location = os.getcwd()
        self.ip = ip
        self.port = port
        self.path = path
        self.time = time
        self.serial = serial
        self.computer_name = ''
        self.is_new = False
        if serial == '0' * 128:
            self.is_new = True
        self.first_folder = True
        self.user_path = ''
        self.client_socket = ''
        self.updates_command = []
        self.is_current_updating = False
        self.finish_command = []
        self.original = True  # if this the original client that upload the folder first time

    # send messages to server
    def send_message_to_server(text, client_socket, pre_made_number):
        text_length = (str(len(text)).zfill(pre_made_number))
        client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        client_socket.recv(3)  # get the ok message
        client_socket.send(bytes(text, encoding='utf-8'))  # send text to server
        client_socket.recv(3)  # get the ok message

    # function that handles the folder text
    def handle_folders(self, text):
        if text == 'no dirs':
            return
        # split the text
        text_splited = text.split(SEPERATOR)
        # get the main folder as field
        main_folder = text_splited.pop()
        # if it's new directory
        if self.is_new:
            # create new dir with the main folder
            os.makedirs(main_folder)
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
                    continue
        text_splited.clear()

    #  create new folder with the serial name
    def create_id_folder(self):
        try:
            os.mkdir(self.path + '/' + self.serial)
        except FileExistsError:
            pass

    # create new folder at server side, creating all sub-folders
    def create_new_folder(self, client):
        while True:
            message_size = client.recv(10).decode()  # get the size of the message, max size of digits is 10
            folder_text = client.recv(int(message_size))
            folder_text = folder_text.decode()  # getting the folders info
            if folder_text == 'done':
                break
            self.handle_folders(folder_text)  # handle folder_text, creating folders

    # send folders from client to server
    def send_folders_to_server(self, client_socket):
        for path, dirs, files in os.walk(self.path, topdown=True):
            # sending folders to create at server
            self.send_dirs(path, dirs, client_socket)
            # at this point server created all folders
            # starting sending files to server
        text = "done"
        message_length = str(len(text)).zfill(10)  # calculates done message
        client_socket.send(bytes(message_length, encoding='utf-8'))  # send the text 'done' size
        client_socket.send(b'done')  # send done

    # send files to server
    def send_files_to_server(self, client_socket):
        for path, dirs, files in os.walk(self.path, topdown=True):
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

    # send dirs to server to write folders
    def send_dirs(self, path, dirs, client_socket):
        if len(dirs) == 0:
            text = "no dirs"
            message_size = str(len(text)).zfill(10)
            client_socket.send(bytes(message_size, encoding='utf-8'))
            client_socket.send(b'no dirs')
            return
        folder_path = path[len(self.path):]
        if folder_path == "":
            folder_path = self.serial
        text_to_send = ""
        for dir in dirs:
            text_to_send += dir + SEPERATOR
        text_to_send += folder_path
        message_size = str(len(text_to_send)).zfill(10)  # send the message size
        client_socket.send(bytes(message_size, encoding='utf-8'))  # send the length of the new message
        client_socket.send(bytes(text_to_send, encoding='utf-8'))  # sending folders to write at server

    # function that handle file - after getting info from text (one file only)
    def handle_files(self, text, client_socket):
        # split, pop as usual
        files_list = text.split(SEPERATOR)
        files_list.pop()
        try:
            file_path = files_list.pop(0)[len(self.user_path):]
        except IndexError:
            file_path = ""
        # means main folder
        if file_path == "":
            # convert main directory to self.path
            file_path = self.path + '/' + self.serial
        else:
            # if its not in main directory put it where it belongs lol
            backup_path = file_path
            file_path = self.path + '/' + self.serial + '/' + backup_path
        total_size_file_to_get = files_list[1]
        data = client_socket.recv(int(files_list[1]))  # because file list is [text.txt,10]
        # write file
        total_size = int(total_size_file_to_get)
        with open(file_path + '/' + files_list[0], 'wb') as file:
            while total_size > 0:
                file.write(data)
                total_size -= len(data)
                data = client_socket.recv(total_size)
            file.close()

    # function that gets the new files to the server
    def get_new_files(self, client_socket):
        while True:
            message_size_before = client_socket.recv(10)  # get the size of the message, max size of digits is 10
            message_size = message_size_before.decode()
            files_text = ""
            files_text += client_socket.recv(int(message_size)).decode()  # getting the files info
            if files_text == 'done':
                break
            self.handle_files(files_text, client_socket)  # handle folder_text, creating folders

    def watch_dog_on_deleted(self, event):
        if self.is_current_updating:  # if client is updating by the server than do nothing
            return
        if event.src_path.endswith('swp'):
            return
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.ip, self.port))
        self.client_socket.send(b'02')  # send mode to server

        self.client_socket.send(bytes(self.serial, encoding='utf-8'))  # send serial to server

        text = self.path
        text_length = (str(len(text)).zfill(10))  # calculates the length of path
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(text, encoding='utf-8'))  # send user path to server

        # send computer name
        text = os.uname()[1]
        self.computer_name = text
        text_length = (str(len(text)).zfill(10))
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(text, encoding='utf-8'))  # send user path to server

        text_to_send = f'delete{SEPERATOR}{event.src_path}'
        length = str(len(text_to_send)).zfill(10)
        self.client_socket.send(bytes(length, encoding='utf-8'))  # send text to server
        self.client_socket.send(bytes(text_to_send, encoding='utf-8'))  # send the message

    def watchdog_on_modified(self, event):
        return  # we do not need to implement this function because it uses create and delete functions

    def watchdog_on_moved(self, event):
        if self.is_current_updating:  # if client is updating by the server than do nothing
            return

        if os.path.isdir(event.src_path) or os.path.isdir(event.dest_path):
            self.send_folder_on_watchdog(event.dest_path)  # create the folders on server side
            # erasing the folder from the server
            self.watch_dog_on_deleted(event)
            return

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket
        self.client_socket.connect((self.ip, self.port))
        self.client_socket.send(b'02')  # send mode to server

        self.client_socket.send(bytes(self.serial, encoding='utf-8'))  # send serial to server

        text = self.path
        text_length = (str(len(text)).zfill(10))  # calculates the length of path
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(text, encoding='utf-8'))  # send user path to server

        # send computer name
        text = os.uname()[1]
        text_length = (str(len(text)).zfill(10))
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(text, encoding='utf-8'))  # send user path to server

        # sending paths to server
        text_to_send = f'moved{SEPERATOR}{event.src_path}{SEPERATOR}{event.dest_path}'
        length = str(len(text_to_send)).zfill(10)
        self.client_socket.send(bytes(length, encoding='utf-8'))  # send text to server
        self.client_socket.send(bytes(text_to_send, encoding='utf-8'))  # send the message

        # send the file data to server
        file_length = str(os.path.getsize(event.dest_path)).zfill(10)  # gets the file size
        self.client_socket.send(bytes(file_length, encoding='utf-8'))  # send the file size
        with open(event.dest_path, 'rb') as file:  # open file and read data
            data = file.read()
            self.client_socket.send(data)  # send data file
            file.close()

    def send_folder_on_watchdog(self, source):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket
        self.client_socket.connect((self.ip, self.port))  # connect to server
        self.client_socket.send(b'05')  # send mode to server
        self.client_socket.send(bytes(self.serial, encoding='utf-8'))  # send serial to server
        path_size = str(len(self.path)).zfill(10)
        self.client_socket.send(str.encode(path_size))  # send path size
        self.client_socket.send(str.encode(self.path))  # send the path to server

        # sending client name
        message_size = str(len(self.computer_name)).zfill(10)
        self.client_socket.send(str.encode(message_size))  # send the name length
        self.client_socket.send(str.encode(self.computer_name))

        for path, dirs, files in os.walk(source, topdown=True):  # sending folders without files
            is_first_time = True
            if is_first_time:  # send the outter folder
                text = path
                text_length = str(len(path)).zfill(10)
                self.client_socket.send(str.encode(text_length))
                self.client_socket.send(str.encode(text))
                is_first_time = False
            else:
                folder_path = path[len(self.path):]
                if folder_path == "":
                    folder_path = self.serial
                text_to_send = ""
                for dir in dirs:
                    text_to_send += dir + SEPERATOR
                text_to_send += folder_path
                message_size = str(len(text_to_send)).zfill(10)  # send the message size
                self.client_socket.send(bytes(message_size, encoding='utf-8'))  # send the length of the new message
                self.client_socket.send(bytes(text_to_send, encoding='utf-8'))  # sending folders to write at server

    def watch_dog_on_created(self, event):
        if self.is_current_updating:  # if client is updating by the server than do nothing
            return
        if event.src_path.endswith('swp'):
            return
        if 'goutputstream' in event.src_path:
            return

        if event.is_directory:  # create folder on server side
            self.send_folder_on_watchdog(event.src_path)
            return

        # sent file info, name and path
        file_length = str(os.path.getsize(event.src_path)).zfill(10)  # gets the file size
        with open(event.src_path, 'rb') as file:  # open file and read data
            data = file.read()
            file.close()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket
        self.client_socket.connect((self.ip, self.port))  # connect to server
        self.client_socket.send(b'02')  # send mode to server

        self.client_socket.send(bytes(self.serial, encoding='utf-8'))  # send serial to server

        text = self.path
        text_length = (str(len(text)).zfill(10))  # calculates the length of path
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(text, encoding='utf-8'))  # send user path to server

        # send computer name
        text = os.uname()[1]
        text_length = (str(len(text)).zfill(10))
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(text, encoding='utf-8'))  # send user path to server

        text_to_send = f'created{SEPERATOR}{event.src_path}'  # getting the text
        length = str(len(text_to_send)).zfill(10)  # length as usual
        self.client_socket.send(bytes(length, encoding='utf-8'))  # send length to server
        self.client_socket.send(bytes(text_to_send, encoding='utf-8'))  # send the message

        self.client_socket.send(bytes(file_length, encoding='utf-8'))  # send the file size
        self.client_socket.send(data)

    # function to create file or folder
    def create_function(self, path_to_write):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket
        self.client_socket.connect((self.ip, self.port))
        self.client_socket.send(b'04')  # send mode to server
        self.client_socket.send(bytes(self.serial, encoding='utf-8'))  # send serial to server
        text_length = (str(len(path_to_write)).zfill(10))  # calculates the length of path
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(path_to_write, encoding='utf-8'))
        total_size = int(self.client_socket.recv(10).decode())  # getting the size of the file
        data = self.client_socket.recv(total_size)  # getting first data
        if self.original:
            path_to_create_file = self.path + path_to_write
        else:
            path_to_create_file = self.path + os.sep + self.serial + path_to_write
        with open(path_to_create_file, 'wb') as file:  # write data to file
            while total_size > 0:  # for big files
                file.write(data)
                total_size -= len(data)
                data = self.client_socket.recv(total_size)
            file.close()
        self.client_socket.close()  # close socket

    # function to delete folder
    def delete_folder(self, path_to_remove_dir):
        # if folder is not empty we need to remove all the files in before we delte it
        for root, directories, files in os.walk(path_to_remove_dir, topdown=False):
            # remove files
            for name in files:
                os.remove(os.path.join(root, name))
            for name in directories:
                os.rmdir(os.path.join(root, name))
        os.rmdir(path_to_remove_dir)

    # function to delete folder or file
    def delete_function(self, path_to_delete):
        try:
            if self.original:
                path_to_delete_file = self.path + path_to_delete
            else:
                path_to_delete_file = self.path + os.sep + self.serial + path_to_delete
            if os.path.isdir(path_to_delete_file):
                self.delete_folder(path_to_delete_file)
            else:
                os.remove(path_to_delete_file)
        except FileNotFoundError:
            return

    # function to move file or folder
    def move_function(self, path_to_delete, path_to_write):
        self.create_function(path_to_write)
        self.delete_function(path_to_delete)

    # get commend and call the function that do this
    def handle_command(self, text):
        text_splitted = text.split(SEPERATOR)  # split the command to action and path
        command = text_splitted[0]
        # call function according to the command we need to do
        if command == 'delete':
            self.delete_function(text_splitted[1])
            return

        elif command == 'created':
            self.create_function(text_splitted[1])

        elif command == 'moved':
            self.move_function(text_splitted[1], text_splitted[2])

        elif command == 'create_folder':
            try:
                realative_path = text_splitted[1]
                if self.original:
                    path_to_open_folder = self.path + os.sep + realative_path
                else:
                    path_to_create_folder = self.path + os.sep + self.serial + realative_path
                os.makedirs(path_to_create_folder)
            except Exception as e:
                pass

    # function to get updates from server and do them
    def get_updates(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket
        self.client_socket.connect((self.ip, self.port))
        self.client_socket.send(b'03')  # send mode to server
        self.client_socket.send(bytes(self.serial, encoding='utf-8'))  # send serial to server
        text_length = (str(len(self.path)).zfill(10))  # calculates the length of path
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(self.path, encoding='utf-8'))
        text_length = (str(len(self.computer_name)).zfill(10))  # calculates the computer name
        self.client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        self.client_socket.send(bytes(self.computer_name, encoding='utf-8'))
        message_original = self.client_socket.recv(2).decode()
        is_original = int(message_original)
        if is_original == 1:
            self.original = True
        else:
            self.original = False
        while True:
            try:
                message_size = self.client_socket.recv(10).decode()  # get the text_length for command
                command = self.client_socket.recv(int(message_size)).decode()  # get to command
                if command == 'done':  # the finish message
                    self.client_socket.close()
                    break
                if command not in self.updates_command:  # check if already the command in the dictionary
                    self.updates_command.append(command)  # insert the command to list
                for command in self.updates_command:  # do all the commands
                    if command not in self.finish_command:  # check if already we do the command
                        self.handle_command(command)
                        self.finish_command.append(command)  # add the current command to the list of finish command
            except OSError as e:
                break

    # start watchdog
    def start_watchdog(self):
        time_counter = 0  # use for get updates
        patterns = ["*"]  # all the files
        ignore_patterns = None
        ignore_directories = False
        case_sensitive = True
        my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
        # create watchdog
        my_event_handler.on_created = self.watch_dog_on_created
        my_event_handler.on_deleted = self.watch_dog_on_deleted
        my_event_handler.on_modified = self.watchdog_on_modified
        my_event_handler.on_moved = self.watchdog_on_moved
        # creating observer
        path = self.path
        go_recursively = True
        my_observer = Observer()
        my_observer.schedule(my_event_handler, path, recursive=go_recursively)  # the event handler, the path, for
        # sub-directories
        my_observer.start()  # start the observer
        try:
            while True:
                time.sleep(1)  # for updates
                time_counter += 1  # count seconds
                if time_counter == int(self.time):  # check if time-out
                    self.is_current_updating = True
                    self.get_updates()  # go to get updates
                    time_counter = 0
                self.is_current_updating = False
        except KeyboardInterrupt:
            my_observer.stop()
            my_observer.join()

    def main_loop(self):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket
        self.client_socket = client_socket
        client_socket.connect((self.ip, self.port))  # connecting to server
        client_socket.send(b'01')  # send mode to server
        client_socket.send(bytes(self.serial, encoding='utf-8'))  # send serial to server
        self.serial = client_socket.recv(128).decode()  # get the updated serial number from server
        text = self.path
        text_length = (str(len(text)).zfill(10))  # calculates the length of path
        client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        client_socket.send(bytes(text, encoding='utf-8'))  # send user path to server

        message_size = client_socket.recv(10).decode()  # get the text_length
        self.user_path = client_socket.recv(int(message_size)).decode() + '/' + self.serial

        text = self.time
        text_length = (str(len(text)).zfill(10))  # calculates the time length for the server
        client_socket.send(bytes(text_length, encoding='utf-8'))  # send time length length to server
        client_socket.send(bytes(text, encoding='utf-8'))  # send text to server

        text = os.uname()[1]
        self.computer_name = text  # send computer name
        text_length = (str(len(self.computer_name)).zfill(10))
        client_socket.send(bytes(text_length, encoding='utf-8'))  # send text_length length to server
        client_socket.send(bytes(self.computer_name, encoding='utf-8'))  # send user path to server

        # check if already the user is existed
        if self.is_new:
            self.send_folders_to_server(client_socket)
            self.send_files_to_server(client_socket)
        else:  # when exist client connect from another computer
            self.create_id_folder()
            self.create_new_folder(client_socket)
            self.get_new_files(client_socket)
        client_socket.close()
        self.start_watchdog()


SEPERATOR = "$"
try:
    IP = sys.argv[1]
    PORT = int(sys.argv[2])
    PATH = sys.argv[3]
    TIME = sys.argv[4]
except Exception:
    print("wrong arguments")
try:
    SERIAL = sys.argv[5]
except IndexError:
    SERIAL = '0' * 128
try:
    client = Client(IP, PORT, PATH, TIME, SERIAL)
    client.main_loop()
except KeyboardInterrupt:
    pass