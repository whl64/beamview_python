import argparse
import os

from PyQt5 import QtWidgets, QtGui
import pyqtgraph as pg

import pypylon.pylon as pylon
from pypylon import _genicam as gen

from basler_camera_wrapper import Basler_Camera, TriggerMode
from camera_window import CameraWindow
from settings_window import SettingsWindow
import faulthandler

packet_size = 8192

class Beamview(QtWidgets.QMainWindow):
    def __init__(self, app):
        super().__init__()
        # layout = QtWidgets.QGridLayout()
        # self.setLayout(layout)
        self.setMinimumSize(200, 200)
        self.setWindowTitle('Camera list')
        self.app = app
        self.archive_mode = False
        self.archive_time = 300
        self.archive_dir = '/home/lo_li/nir_archive'
        tlf = pylon.TlFactory.GetInstance()
        self.devices = tlf.EnumerateDevices()
        for i, device in enumerate(self.devices):
            if device.GetUserDefinedName() == '':
                device.SetUserDefinedName(f'Camera {i}')

        self.cam_window = CameraWindow(self, app)
        self.settings_window = SettingsWindow(self, app)
            
        self.camera_list = QtWidgets.QTreeView(self)
        self.camera_list_model = QtGui.QStandardItemModel()
        self.camera_list_model.setHorizontalHeaderLabels(('Name', 'Model'))
        self.camera_list.setModel(self.camera_list_model)
        self.camera_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.camera_list.setUniformRowHeights(True)
        
        for device in self.devices:
            name = QtGui.QStandardItem(device.GetUserDefinedName())
            model = QtGui.QStandardItem(device.GetModelName())
            name.setEditable(False)
            model.setEditable(False)
            self.camera_list_model.appendRow((name, model))
            
        self.camera_list.doubleClicked.connect(self.add_camera)
        # layout.addChildWidget(self.camera_list)
        # self.camera_list.bind('<Double-Button-1>', self.add_camera)
        # scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.camera_list.yview)
        self.opened_cameras = {}
        self.running_cameras = {}
        
        self.setCentralWidget(self.camera_list)
        self.settings_window.show()
        self.cam_window.show()


            
    def add_camera(self, *args):
        index = self.camera_list.currentIndex().row()
        serial_number = self.devices[index].GetSerialNumber()
        if serial_number not in self.opened_cameras:
            try:
                cam  = Basler_Camera(serial_number, TriggerMode.SOFTWARE, packet_size)
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
            frame = self.cam_window.add_camera(cam)
            self.settings_window.add_camera(cam, frame)

    def remove_camera(self, cam):
        self.settings_window.remove_camera(cam)
        if cam.serial_number in self.opened_cameras:
            del self.opened_cameras[cam.serial_number]


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
            
    def closeEvent(self, event):
        self.app.quit()
            
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
    app.exec_()
    
    
if __name__ == '__main__':
    main()
