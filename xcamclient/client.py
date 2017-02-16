'''
Created on 23.1.2017

@author: Samuli Rahkonen
'''
import socket
import requests
import threading
import queue


class XcamCapture():

    def __init__(self, addr):
        self.addr = addr
        self._capture_thread = threading.Thread(name='capture_thread',
                                                target=self._capture_frame_stream,
                                                args=[None, None])
        self._enabled = False
        self.enabled_lock = threading.Lock()
        self.exc_queue = queue.Queue()
        self.frames_count = 0

    @property
    def enabled(self):
        '''
        Is capture thread enabled.
        @return: True/False
        '''
        with self.enabled_lock:
            val = self._enabled
        return val

    @enabled.setter
    def enabled(self, value):
        '''
        Signals capture thread to shut down when set to False.
        Otherwise always True.
        '''
        with self.enabled_lock:
            self._enabled = value

    def get_meta(self):
        r = requests.get(self.addr + "/meta", timeout=30)
        resp = r.json()
        return resp

    def init_camera(self, force=False):
        r = requests.get(self.addr + "/meta", timeout=30)
        resp = r.json()
        # Don't init if it is already running
        if not force and resp['status'] != 'CLOSED':
            return resp
        print('INIT')
        r = requests.post(self.addr + "/init", timeout=30)
        print(r.status_code, r.reason)
        print(r.text)
        resp = r.json()
        if resp['status'] != 'STOPPED':
            print('status is not STOPPED, it\'s %s' % resp['status'])
            return None
        return resp

    def start_camera(self):
        r = requests.get(self.addr + "/meta", timeout=30)
        resp = r.json()
        # Don't start if it is already running
        if resp['status'] != 'STOPPED':
            print(r.text)
            print('Server status is ', resp['status'])
            return resp
        print('START')
        r = requests.post(self.addr + "/start", timeout=30)
        # print(r.status_code, r.reason)
        # print(r.text)
        if r.status_code is 200 and r.reason == 'OK':
            return r.json()
        else:
            return None

    def stop_camera(self):
        r = requests.get(self.addr + "/meta", timeout=30)
        resp = r.json()
        # Don't start if it is already running
        if resp['status'] != 'STOPPED':
            print(r.text)
            print('Server status is ', resp['status'])
            return resp
        print('STOP')
        r = requests.post(self.addr + "/stop", timeout=30)
        # print(r.status_code, r.reason)
        # print(r.text)
        if r.status_code is 200 and r.reason == 'OK':
            return r.json()
        else:
            return None

    def close_camera(self):
        print('CLOSE')
        r = requests.post(self.addr + "/close", timeout=30)
        # print(r.status_code, r.reason)
        # print(r.text)
        if r.status_code is 200 and r.reason == 'OK':
            return r.json()
        else:
            return None

    def shutdown_server(self):
        print('SHUTDOWN')
        r = requests.post(self.addr + "/shutdown", timeout=30)
        # print(r.status_code, r.reason)
        # print(r.text)
        if r.status_code is 200 and r.reason == 'OK':
            return r.text
        else:
            return None

    def _capture_frame_stream(self, from_socket, to_stream, frame_size):
        print('_capture_frame_stream started')
        self.frames_count = 0
        try:
            frame_data = bytearray(frame_size)
            data_start_pointer = 0
            data_end_pointer = 0
            while self.enabled:
                # Write when full frame is received
                data = from_socket.recv(frame_size)
                data_len = len(data)
                # print('Received', data_len, 'bytes')
                data_start_pointer = data_end_pointer
                tmp = data_start_pointer+data_len
                if tmp >= frame_size:
                    remaining_len = (data_start_pointer+data_len) % frame_size
                    chunk_len = data_len - remaining_len
                    chunk = data[:chunk_len]
                    remaining = data[chunk_len:]
                    frame_data[data_start_pointer:data_start_pointer+chunk_len] = chunk
                    to_stream.write(frame_data)
                    self.frames_count += 1
                    # print('Wrote', len(frame_data), 'bytes to stream.')
                    frame_data[:remaining_len] = remaining
                    data_end_pointer = remaining_len
                else:
                    data_end_pointer = tmp
                    frame_data[data_start_pointer:data_end_pointer] = data
                #print('Read data')
                # to_stream.write(data)
                #print('Wrote data')
        except Exception as e:
            self.enabled = False
            self.exc_queue.put(e)
            print('_capture_frame_stream', repr(e))
        finally:
            to_stream.close()
            print('_capture_frame_stream closed')

    def start_recording(self, stream):
        if isinstance(stream, str):
            stream_obj = open(stream, 'wb')
        else:
            stream_obj = stream
        self.meta = self.get_meta()
        stream_address = tuple(self.meta['stream_address'])
        print('CONNECTING TO SOCKET %s:%s' % stream_address)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(stream_address)
        # cs = client_socket.makefile(mode='rb')

        self.enabled = True
        self._capture_thread = threading.Thread(name='capture_thread',
                                                target=self._capture_frame_stream,
                                                args=[client_socket, stream_obj, self.meta['frame_size']])
        self._capture_thread.start()

    def stop_recording(self):
        self.enabled = False
        self._capture_thread.join(5)
        if self._capture_thread.isAlive():
            raise Exception('Thread didn\'t stop.')
        try:
            exc = self.exc_queue.get(block=False)
        except queue.Empty:
            pass
        else:
            print(repr(exc))
            raise exc
        meta = (('samples', self.meta['width']),
                ('bands', self.frames_count),
                ('lines', self.meta['height']),
                ('data type', self.meta['data type']),
                ('interleave', self.meta['interleave']),
                ('byte order', self.meta['byte order']),
                ('description', ''))
        return meta

    def frames(self):
        self.meta = self.get_meta()
        stream_address = tuple(self.meta['stream_address'])
        print('CONNECTING TO SOCKET %s:%s' % stream_address)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(stream_address)
        from_socket = client_socket
        frame_size = self.meta['frame_size']
        try:
            frame_data = bytearray(frame_size)
            data_start_pointer = 0
            data_end_pointer = 0
            while True:
                # Write when full frame is received
                data = from_socket.recv(1024)
                data_len = len(data)
                print('Received', data_len, 'bytes')
                data_start_pointer = data_end_pointer
                tmp = data_start_pointer+data_len
                if tmp >= frame_size-1:
                    remaining_len = data_start_pointer+data_len % frame_size
                    chunk_len = data_len - remaining_len
                    chunk = data[:chunk_len-1]
                    remaining = data[chunk_len:]
                    frame_data[data_start_pointer:data_start_pointer+chunk_len] = chunk
                    yield frame_data
                    self.frames_count += 1
                    print('Wrote', len(frame_data), 'bytes to stream.')
                    frame_data[:remaining_len-1] = remaining
                    data_end_pointer = remaining_len-1
                else:
                    data_end_pointer = tmp
                    frame_data[data_start_pointer:data_end_pointer] = data
                #print('Read data')
                # to_stream.write(data)
                #print('Wrote data')
        except Exception as e:
            raise e
            # self.enabled = False
            # self.exc_queue.put(e)


    '''
    def receive_data(self, addr_tuple):
        print('CONNECTING TO SOCKET %s:%s' % tuple(addr_tuple))
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(tuple(addr_tuple))
        cs = client_socket.makefile(mode='rb')

        print('CONNECTED')
        try:
            # Make a file-like object out of the connection
            # connection = client_socket.makefile('rb')
            # input('Enter')
            i = 0
            while True:
                # data = connection.read(163840)
                # data = client_socket.recv(1024)
                data = cs.read(163840)
                if data != b'':
                    # print(data)
                    print('Got', len(data), 'bytes frame data,', i)
                    # print('Got', len(data), 'bytes frame data,', i)
                    i += 1
                else:
                    print('No frame data')
                # print(connection.read(163840))
                # a = input('asdasd>')
                # if a != '':
                #    break
        except:
            raise
        finally:
            print('Closing connection...')
            # connection.close()
            client_socket.close()
            print('...closed.')
    '''

    def frames(self, meta):
        ''' Generator for  '''
        width = meta['width']
        height = meta['height']
        frame_size = meta['frame_size']
        if width is None:
            raise Exception('Width is None')
        if height is None:
            raise Exception('Height is None')
        if frame_size is None:
            raise Exception('frame_size is None')

        addr_tuple = meta['stream_address']
        if addr_tuple is None:
            raise Exception('stream_address is None')

        print('CONNECTING TO SOCKET %s:%s' % tuple(addr_tuple))
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(tuple(addr_tuple))
        cs = client_socket.makefile(mode='rb')

        while True:
            data = cs.read(frame_size)
            if data:
                yield data
            else:
                break
        cs.close()
        yield b''


def _main():
    print('Starting')
    addr = "http://127.0.0.1:5000"
    init(addr)
    input('Enter')
    resp = start(addr)
    socket_addr = resp['stream_address']
    if socket_addr is None:
        print('Received data didn\'t have socket address')
        return
    resp['frame_size']
    receive_data(socket_addr)


if __name__ == '__main__':
    _main()
