import argparse
import os

from PyQt5 import QtWidgets, QtGui

import pypylon.pylon as pylon
from pypylon import _genicam as gen

from basler_camera_wrapper import Basler_Camera, TriggerMode
from camera_window import CameraWindow
from settings_window import SettingsWindow
import faulthandler

packet_size = 8192

class Beamview(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # layout = QtWidgets.QGridLayout()
        # self.setLayout(layout)
        self.setWindowTitle('Camera list')
                
        tlf = pylon.TlFactory.GetInstance()
        self.devices = tlf.EnumerateDevices()
        for i, device in enumerate(self.devices):
            if device.GetUserDefinedName() == '':
                device.SetUserDefinedName(f'Camera {i}')

        # self.cam_window = CameraWindow(self)
        # self.settings_window = SettingsWindow(self)
            
        self.camera_list = QtWidgets.QTreeView(self)
        self.camera_list_model = QtGui.QStandardItemModel()
        self.camera_list_model.setHorizontalHeaderLabels(('Name', 'Model'))
        self.camera_list.setModel(self.camera_list_model)
        self.camera_list.setUniformRowHeights(True)
        
        for device in self.devices:
            self.camera_list_model.appendRow((QtGui.QStandardItem(device.GetUserDefinedName()), QtGui.QStandardItem(device.GetModelName())))
        
        # layout.addChildWidget(self.camera_list)
        # self.camera_list.bind('<Double-Button-1>', self.add_camera)
        # scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.camera_list.yview)
        self.opened_cameras = {}
        self.running_cameras = {}
        
        self.setCentralWidget(self.camera_list)

            
    def add_camera(self, *args):
        index = self.camera_list.index(self.camera_list.selection()[0])
        serial_number = self.devices[index].GetSerialNumber()
        if serial_number not in self.opened_cameras:
            try:
                cam  = Basler_Camera(serial_number, TriggerMode.SOFTWARE, packet_size)
            except gen.RuntimeException:
                messagebox.showerror('Error', 'Error: Camera in use by another application.')
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
            cam.frame_transmission_delay = accumulated_delay + delay_offset
            total_packet_size = packet_size + 14 + 4  # including Ethernet headers
            accumulated_delay += total_packet_size
        for cam in self.opened_cameras.values():
            cam.interpacket_delay = accumulated_delay

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
    beamview = Beamview()
    beamview.show()
    app.exec_()
    
    
if __name__ == '__main__':
    main()
