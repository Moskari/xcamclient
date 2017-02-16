'''
Created on 24.1.2017

@author: sapejura
'''
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pylab
from xcamclient.client import XcamCapture
import numpy as np
import io
import threading


class PreviewStream(io.IOBase):
    '''
    Stream object returns the most recent full frame.
    Reading partial frames is not supported.
    You should not write more than one frame at once.
    '''

    def __init__(self, frame_size):
        super().__init__()
        self.frame_size = frame_size
        self._lock = threading.Lock()
        self._current_frame = b''
        self._next_frame = bytearray(frame_size)
        self.data_start_pointer = 0
        self.data_end_pointer = 0

    def readable(self):
        return True

    def writable(self):
        return True

    def write(self, b):
        # TODO: This does not work if written more than one frame at once
        with self._lock:
            data = b
            # Write when full frame is received
            data_len = len(data)
            # print('Received', data_len, 'bytes')
            self.data_start_pointer = self.data_end_pointer
            tmp = self.data_start_pointer+data_len
            if tmp >= self.frame_size:
                remaining_len = (self.data_start_pointer+data_len) % self.frame_size
                chunk_len = data_len - remaining_len
                chunk = data[:chunk_len]
                remaining = data[chunk_len:]

                self._next_frame[self.data_start_pointer:self.data_start_pointer+chunk_len] = chunk
                # Set current frame

                self._current_frame = bytes(self._next_frame)

                # print('Wrote', len(frame_data), 'bytes to stream.')
                self._next_frame[:remaining_len] = remaining
                # frame_data[:remaining_len-1] = remaining
                self.data_end_pointer = remaining_len
            else:
                self.data_end_pointer = tmp
                self._next_frame[self.data_start_pointer:self.data_end_pointer] = data
        return data_len

    def read(self, n=-1):
        with self._lock:
            b = self._current_frame
            self._current_frame = b''
        return b


def _image(stream, size, dims, pixel_dtype, pixel_size_bytes):
    while True:
        img = stream.read(size)
        if img == b'':
            continue
        break
    # print('Image size:', len(img))
    frame_buffer = np.frombuffer(img,
                                 dtype=pixel_dtype,
                                 count=int(size/pixel_size_bytes))
    frame_buffer = np.reshape(frame_buffer, dims)
    return frame_buffer


if __name__ == '__main__':
    addr = 'http://127.0.0.1:5000'
    xc = XcamCapture(addr)
    xc.init_camera()
    meta = xc.start_camera()

    size = meta['frame_size']
    dims = (meta['height'], meta['width'])
    pixel_dtype = np.dtype(meta['data type'])
    pixel_size = int(meta['data type'][1:])

    print('Size:', size, 'Dims:', dims, 'Dtype:', pixel_dtype, 'Pixel size:', pixel_size)

    stream = PreviewStream(size)
    xc.start_recording(stream)

    # Show images
    fig = plt.figure()
    fig.canvas.set_window_title('Preview')


    im = plt.imshow(_image(stream,
                           size,
                           dims,
                           pixel_dtype,
                           pixel_size))

    def updatefig(*args):
        img = _image(stream,
                     size,
                     dims,
                     pixel_dtype,
                     pixel_size)
        im.set_data(img)
        # These have to be set every time
        # because matplotlib is buggy
        im.set_clim(vmin=0, vmax=5000)
        return im,

    # im.set_data(image(stream))

    # The _ has to be there because matplotlib is buggy
    _ = animation.FuncAnimation(fig=fig,
                                func=updatefig,
                                interval=60,
                                blit=True)
    pylab.show()
    xc.stop_recording()
    xc.stop_camera()
    resp = xc.close_camera()
    print(resp)
    xc.shutdown_server()
    print('Done')
