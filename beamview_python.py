from multiprocessing import dummy
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QActionGroup
import threading
import time
import datetime
import numpy as np
from camera_frame import CameraFrame
import pyqtgraph.exporters as exp
import os
import qrc_icons
import faulthandler
import argparse
import pypylon.pylon as pylon
from pypylon import _genicam as gen
from basler_camera_wrapper import Basler_Camera, TriggerMode
from settings_window import SettingsWindow
from camera_list_window import CameraListWindow
import pyqtgraph as pg

packet_size = 1200
binning = 1

class Beamview(QtWidgets.QMainWindow):    
    def __init__(self, app):
        super().__init__()
        self.setWindowTitle('Beamview')
        self.camera_frames = {}
        self.archive_mode = False
        self.archive_time = 300
        self.archive_dir = os.path.expanduser(os.path.join('~', 'nir_archive'))
        print(self.archive_dir)
        tlf = pylon.TlFactory.GetInstance()
        self.devices = tlf.EnumerateDevices()
        for i, device in enumerate(self.devices):
            if device.GetUserDefinedName() == '':
                device.SetUserDefinedName(f'Camera {i}')
                
        dummy_widget = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout()
        dummy_widget.setLayout(self.grid)
        self.setCentralWidget(dummy_widget)
        self.adding_crosshair = False
        self.moving_crosshair = False
        self.deleting_crosshair = False
        self.create_actions()
        self.connect_actions()
        self.create_toolbar()
        
        self.app = app
        self.last_archive_time = time.time()
        self.trigger_thread = threading.Thread(target=self.trigger_loop, daemon=True)
        self.trigger_thread.start()
        
        self.opened_cameras = {}
        self.running_cameras = {}
        
        self.selected_camera = None
        
        self.settings_window = SettingsWindow(self, app)
        self.camera_list_window = CameraListWindow(self, app)
            
    def closeEvent(self, event):
        self.camera_list_window.hide()
        self.settings_window.hide()
        self.app.quit()
        
    def connect_actions(self):
        self.start_all_action.triggered.connect(self.start_all_cameras)
        self.stop_all_action.triggered.connect(self.stop_all_cameras)    
        self.camera_list_action.triggered.connect(self.open_camera_list)
        self.settings_action.triggered.connect(self.open_settings)    
        self.archive_action.toggled.connect(self.toggle_archive)
        self.axis_action.toggled.connect(self.toggle_axes)
        self.crosshair_add_action.toggled.connect(self.toggle_add_crosshair)
        self.crosshair_move_action.toggled.connect(self.toggle_move_crosshair)
        self.crosshair_delete_action.toggled.connect(self.toggle_delete_crosshair)

    def create_actions(self):
        self.start_all_action = QAction(QIcon(':control.png'), '&Start all cameras', self)
        self.stop_all_action = QAction(QIcon(':control-stop-square.png'), '&Stop all cameras', self)
        self.camera_list_action = QAction(QIcon(':script--arrow.png'), '&Camera list...', self)
        self.settings_action = QAction(QIcon(':gear.png'), '&Settings...', self)
        self.archive_action = QAction(QIcon(':books-brown.png'), '&Toggle archive mode', self)
        self.archive_action.setCheckable(True)    
        self.axis_action = QAction(QIcon(':guide.png'), '&Toggle axis labels', self)
        self.axis_action.setCheckable(True)
        self.crosshair_add_action = QAction(QIcon(':target--plus.png'), '&Add crosshair', self)
        self.crosshair_add_action.setCheckable(True)
        self.crosshair_move_action = QAction(QIcon(':target--arrow.png'), '&Move crosshair', self)
        self.crosshair_move_action.setCheckable(True)
        self.crosshair_delete_action = QAction(QIcon(':target--minus.png'), '&Delete crosshair', self)
        self.crosshair_delete_action.setCheckable(True)
        
    def create_toolbar(self):
        self.toolbar = self.addToolBar('Camera controls')
        self.toolbar.addAction(self.start_all_action)
        self.toolbar.addAction(self.stop_all_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.camera_list_action)
        self.toolbar.addAction(self.settings_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.archive_action)
        self.toolbar.addAction(self.axis_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.crosshair_add_action)
        self.toolbar.addAction(self.crosshair_move_action)
        self.toolbar.addAction(self.crosshair_delete_action)
        self.toolbar.toggleViewAction().setVisible(False)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        
    def start_all_cameras(self):
        for frame in self.camera_frames.values():
            frame.start_camera()
        self.settings_window.refresh()
        
    def stop_all_cameras(self):
        for frame in self.camera_frames.values():
            frame.stop_camera()
        self.settings_window.refresh()
        
    def toggle_archive(self):
        self.archive_mode = self.archive_action.isChecked()
        self.settings_window.refresh()
            
    def toggle_add_crosshair(self):
        self.adding_crosshair = self.crosshair_add_action.isChecked()
        if self.adding_crosshair:
            self.crosshair_move_action.setChecked(False)
            self.crosshair_delete_action.setChecked(False)
        
    def toggle_move_crosshair(self):
        self.moving_crosshair = self.crosshair_move_action.isChecked()
        for frame in self.camera_frames.values():
            frame.move_crosshairs(self.moving_crosshair)
        if self.moving_crosshair:
            self.crosshair_add_action.setChecked(False)
            self.crosshair_delete_action.setChecked(False)
        
    def toggle_delete_crosshair(self):
        self.deleting_crosshair = self.crosshair_delete_action.isChecked()
        for frame in self.camera_frames.values():
            frame.highlight_crosshairs(self.deleting_crosshair)
        if self.deleting_crosshair:
            self.crosshair_add_action.setChecked(False)
            self.crosshair_move_action.setChecked(False)
        
    def toggle_axes(self):
        for frame in self.camera_frames.values():
            frame.toggle_axes()
        
    def open_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
        
    def open_camera_list(self):
        self.camera_list_window.show()
        self.camera_list_window.raise_()
        self.camera_list_window.activateWindow()
        
    def regrid(self):                
        for i, frame in enumerate(self.camera_frames.values()):
            self.assign_frame_to_grid(frame, i)
        self.adjustSize()
        
    def assign_frame_to_grid(self, frame, index):
        assigned_row = index % 2
        assigned_column = index // 2
        self.grid.addWidget(frame, assigned_row, assigned_column)


    def activate_frame(self, cam):
        return  # highlighting active frame doesn't seem necessary at the moment
        for serial, frame in self.camera_frames.items():
            if serial == cam.serial_number:
                frame.activate()
            else:
                frame.deactivate()

    def trigger_loop(self):
        while 1:
            archive = False
            if self.archive_mode and time.time() - self.last_archive_time > self.archive_time:
                self.last_archive_time = time.time()
                archive = True
                timestamp = datetime.datetime.now()
            numbers = self.camera_frames.keys()
            for sn in numbers:
                try:
                    frame = self.camera_frames[sn]
                    cam = frame.cam
                    if cam.is_grabbing():
                        if archive:
                            subdir = os.path.join(self.archive_dir, f'{timestamp.year}_{timestamp.month:02d}_{timestamp.day:02d}')
                            if not os.path.exists(subdir):
                                os.mkdir(subdir)
                            filename = os.path.join(subdir, f'{timestamp.year}{timestamp.month:02d}{timestamp.day:02d}_{timestamp.hour:02d}{timestamp.minute:02d}{timestamp.second:02d}_{cam.name}')
                            print(filename)
                            # np.savez(filename + '.npz', plot_data=self.camera_frames[sn].plot_data)
                            exporter = exp.ImageExporter(self.camera_frames[sn].plot)
                            exporter.export(filename + '.png')
                            time.sleep(0.2)
                        cam.request_frame()
                        res = cam.return_frame()
                        frame.image_grabber.OnImageGrabbed(cam, res)
                except:
                    pass
            if self.archive_mode:
                time.sleep(5)
            else:
                time.sleep(0.1)
                
    def set_archive_mode(self, archive):
        self.archive_mode = archive
        self.cam_window.archive_action.setChecked(archive)

    def select_camera(self, cam):
        self.selected_camera = cam
        self.activate_frame(cam)
            
    def add_camera(self, index):
        serial_number = self.devices[index].GetSerialNumber()
        if serial_number not in self.opened_cameras:
            try:
                cam  = Basler_Camera(serial_number, TriggerMode.FREERUN, packet_size, binning)
            except gen.RuntimeException:
                error_box = QtWidgets.QMessageBox()
                error_box.setIcon(QtWidgets.QMessageBox.Critical)
                error_box.setWindowTitle('Error')
                error_box.setText('Error: Camera in use by another application.')
                error_box.show()
                error_box.exec_()
                return
            if cam.name == '':
                cam.name = self.devices[index].GetUserDefinedName()
            self.opened_cameras[serial_number] = cam
            frame = CameraFrame(self, cam, self.app)
            self.camera_frames[cam.serial_number] = frame
            self.assign_frame_to_grid(frame, len(self.camera_frames) - 1)
            self.settings_window.add_camera(cam, frame)
            self.select_camera(cam)

    def remove_camera(self, camera_frame):
        cam = camera_frame.cam
        self.grid.removeWidget(camera_frame)
        camera_frame.setParent(None)
        del self.camera_frames[cam.serial_number]
        self.regrid()
        self.settings_window.remove_camera(cam)
        if cam.serial_number in self.opened_cameras:
            del self.opened_cameras[cam.serial_number]
            self.camera_list.remove_camera(cam)

    def find_camera_index(self, cam):
        for i, bascam in enumerate(self.devices):
            if cam.serial_number == bascam.GetSerialNumber():
                return i
        raise ValueError('Camera not found')

    def set_delays(self):
        accumulated_delay = 0
        delay_offset = 0
        for cam in self.opened_cameras.values():
            try:
                cam.frame_transmission_delay = accumulated_delay + delay_offset
                total_packet_size = packet_size + 14 + 4  # including Ethernet headers
                accumulated_delay += total_packet_size
            except gen.LogicalErrorException:
                pass
        for cam in self.opened_cameras.values():
            try:
                cam.interpacket_delay = accumulated_delay
            except gen.LogicalErrorException:
                pass

    def start_camera(self, cam):
        if cam.serial_number not in self.running_cameras:
            self.running_cameras[cam.serial_number] = cam
            self.set_delays()

    def stop_camera(self, cam):
        if cam.serial_number in self.running_cameras:
            del self.running_cameras[cam.serial_number]
            self.set_delays()
                
def main():
    parser = argparse.ArgumentParser(description='Multicam Beamview.')
    parser.add_argument('--debug', help='create emulated cameras for debugging', action='store_true')
    args = parser.parse_args()
    if args.debug:
        faulthandler.enable()
        number_of_emulated_cameras = 20
        os.environ['PYLON_CAMEMU'] = str(number_of_emulated_cameras)
    app = QtWidgets.QApplication([])
    pg.setConfigOption('imageAxisOrder', 'row-major')
    beamview = Beamview(app)
    beamview.show()
    beamview.camera_list_window.show()  
    beamview.camera_list_window.raise_()
    beamview.camera_list_window.activateWindow()
    app.exec_()
    
    
if __name__ == '__main__':
    main()
