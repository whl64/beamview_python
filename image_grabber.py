from pypylon import genicam
from pypylon import pylon

class ImageGrabber(pylon.ImageEventHandler):
    def __init__(self, camera_frame):
        super().__init__()
        self.camera_frame = camera_frame
        
    def OnImageGrabbed(self, camera, res):
        if not res.IsValid():
            raise RuntimeError('Grab failed')
        
        self.camera_frame.draw_frame(res.Array)