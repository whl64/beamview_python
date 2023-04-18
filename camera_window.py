from multiprocessing import dummy
from PyQt5 import QtWidgets
import threading
import time

from camera_frame import CameraFrame


class CameraWindow(QtWidgets.QMainWindow):    
    def __init__(self, root, app):
        super().__init__()
        self.setWindowTitle('Beamview')
        self.camera_frames = {}
        self.root = root
        dummy_widget = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout()
        dummy_widget.setLayout(self.grid)
        self.setCentralWidget(dummy_widget)
        self.app = app
        self.trigger_thread = threading.Thread(target=self.trigger_loop, daemon=True)
        self.trigger_thread.start()
        
    def closeEvent(self, event):
        self.app.quit()
     
    def remove_camera(self, camera_frame):
        self.grid.removeWidget(camera_frame)
        camera_frame.setParent(None)
        del self.camera_frames[camera_frame.cam.serial_number]
        self.regrid()
        
    def regrid(self):                
        for i, frame in enumerate(self.camera_frames.values()):
            self.assign_frame_to_grid(frame, i)
        self.adjustSize()
        
    def assign_frame_to_grid(self, frame, index):
        assigned_row = index % 2
        assigned_column = index // 2
        self.grid.addWidget(frame, assigned_row, assigned_column)
    
    def add_camera(self, cam):
        frame = CameraFrame(self, cam, self.app)
        self.camera_frames[cam.serial_number] = frame
        self.assign_frame_to_grid(frame, len(self.camera_frames) - 1)
            
        return frame

    def trigger_loop(self):
        while 1:
            try:
                numbers = self.camera_frames.keys()
                for sn in numbers:
                    cam = self.camera_frames[sn].cam
                    if cam.is_grabbing():
                        cam.request_frame()
            except:
                pass
            time.sleep(0.1)
                
