# xcamclient

## Synopsis

This Python 3 package controls the the xcamserver via REST API and makes it easier to read the streamed data from the socket.


## Usage

First start xcamserver.

This example saves 20 seconds of frames to file (however it is less, because of latencies):

```python
from xcamclient.client import XcamCapture
import time

if __name__ == '__main__':
    xc = XcamCapture('http://127.0.0.1:5000')
    xc.init_camera()
    xc.start_camera()
    filename = 'file1.raw'  # or a stream object

    xc.start_recording(filename)
    time.sleep(20)
    meta = xc.stop_recording()

    xc.stop_camera()
    xc.close_camera()
    xc.shutdown_server()
```

See example 'capture_preview.py' for how to use matplotlib to display the frame stream.


## Installation

Tested only with Python 3.5 (Windows). 'xcamserver', 'requests', 'Numpy' and 'matplotlib' are required.

Install with pip:
`pip install <directory path to setup.py>`


## License

The MIT License (MIT)

**Disclaimer**
The author disclaims all responsibility for possible damage to equipment and/or people. Use the software with your own risk.
