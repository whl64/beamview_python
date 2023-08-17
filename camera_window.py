from multiprocessing import dummy
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
import threading
import time
import datetime
import numpy as np
from camera_frame import CameraFrame
import pyqtgraph.exporters as exp
import os
import qrc_icons

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
        self.create_actions()
        self.connect_actions()
        self.create_toolbar()
        
        self.app = app
        self.last_archive_time = time.time()
        self.trigger_thread = threading.Thread(target=self.trigger_loop, daemon=True)
        self.trigger_thread.start()
        
    def connect_actions(self):
        self.camera_list_action.triggered.connect(self.open_camera_list)
        self.settings_action.triggered.connect(self.open_settings)    

    def create_actions(self):
        self.camera_list_action = QAction(QIcon(':script--arrow.png'), '&Camera list', self)
        self.settings_action = QAction(QIcon(':gear.png'), '&Settings...', self)
        
    def create_toolbar(self):
        self.toolbar = self.addToolBar('Camera controls')
        self.toolbar.addAction(self.camera_list_action)
        self.toolbar.addAction(self.settings_action)
        self.toolbar.toggleViewAction().setVisible(False)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        
    def open_settings(self):
        self.root.settings_window.raise_()
        self.root.settings_window.activateWindow()
        
    def open_camera_list(self):
        self.root.raise_()
        self.root.activateWindow()
        
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
        self.activate_frame(cam)
            
        return frame

    def activate_frame(self, cam):
        for serial, frame in self.camera_frames.items():
            if serial == cam.serial_number:
                frame.activate()
            else:
                frame.deactivate()

    def trigger_loop(self):
        while 1:
            archive = False
            if self.root.archive_mode and time.time() - self.last_archive_time > self.root.archive_time:
                self.last_archive_time = time.time()
                archive = True
                timestamp = datetime.datetime.now()
            try:
                numbers = self.camera_frames.keys()
                for sn in numbers:
                    cam = self.camera_frames[sn].cam
                    if archive:
                        subdir = os.path.join(self.root.archive_dir, f'{timestamp.year}_{timestamp.month:02d}_{timestamp.day:02d}')
                        if not os.path.exists(subdir):
                            os.mkdir(subdir)
                        filename = os.path.join(subdir, f'{timestamp.year}{timestamp.month:02d}{timestamp.day:02d}_{timestamp.hour:02d}{timestamp.minute:02d}{timestamp.second:02d}_{cam.name}')
                        print(filename)
                        # np.savez(filename + '.npz', plot_data=self.camera_frames[sn].plot_data)
                        exporter = exp.ImageExporter(self.camera_frames[sn].plot)
                        exporter.export(filename + '.png')
                        time.sleep(0.2)
                    if cam.is_grabbing():
                        cam.request_frame()
            except:
                pass
            if self.root.archive_mode:
                time.sleep(5)
            else:
                time.sleep(0.1)
                
