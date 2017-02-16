'''
Created on 24.1.2017

@author: Samuli Rahkonen
'''

from xcamclient.client import XcamCapture
import time


if __name__ == '__main__':
    xc = XcamCapture('http://127.0.0.1:5000')
    xc.init_camera()
    xc.start_camera()
    # for filename in ['file2.raw', 'file3.raw']:
    filename = 'file1.raw'

    xc.start_recording(filename)
    time.sleep(20)
    meta = xc.stop_recording()

    xc.stop_camera()
    xc.close_camera()
    xc.shutdown_server()
