from pypylon import pylon
import time

class ImageGrabber(pylon.ImageEventHandler):
    def __init__(self, camera_frame):
        super().__init__()
        self.camera_frame = camera_frame
        
    def OnImageGrabbed(self, camera, res):
        if not res.IsValid():
            raise RuntimeError('Grab failed')
        # self.camera_frame.lock.acquire()
        self.camera_frame.plot_data = res.Array
        self.camera_frame.frame_available = True
        # self.camera_frame.lock.release()
        try:
            self.camera_frame.cam.request_frame()
        except:
            print('trigger timed out')

