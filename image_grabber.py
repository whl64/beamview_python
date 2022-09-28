from pypylon import pylon
import time

class ImageGrabber(pylon.ImageEventHandler):
    def __init__(self, camera_frame):
        super().__init__()
        self.camera_frame = camera_frame
        
    def OnImageGrabbed(self, camera, res):
        if not res.IsValid():
            raise RuntimeError('Grab failed')
        self.camera_frame.plot_data = res.Array
        self.camera_frame.draw_frame()
        try:
            self.camera_frame.cam.request_frame()
        except:
            print('trigger timed out')

