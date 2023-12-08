from pypylon import pylon
import time

class ImageGrabber(pylon.ImageEventHandler):
    min_frame_time = 0.2
    def __init__(self, camera_frame):
        super().__init__()
        self.camera_frame = camera_frame
        self.last_frame_timestamp = time.time()

    def OnImageGrabbed(self, camera, res):
        if res.IsValid():
            with self.camera_frame.lock:
                self.camera_frame.plot_data = res.Array
                self.camera_frame.frame_available = True
        else:
            print('grab failed')



