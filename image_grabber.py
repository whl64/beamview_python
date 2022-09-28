from pypylon import pylon
import time

class ImageGrabber(pylon.ImageEventHandler):
    min_frame_time = 0.2
    def __init__(self, camera_frame):
        super().__init__()
        self.camera_frame = camera_frame
        self.last_frame_timestamp = time.time()

    def OnImageGrabbed(self, camera, res):
        if not res.IsValid():
            raise RuntimeError('Grab failed')
        self.camera_frame.draw_frame(res.Array)
        frame_time = time.time() - self.last_frame_timestamp
        if frame_time < self.min_frame_time:
            time.sleep(self.min_frame_time - frame_time)
        self.last_frame_timestamp = time.time()
        self.camera_frame.cam.request_frame()



