import argparse
import os

from PyQt5 import QtWidgets, QtGui, QtCore
import pyqtgraph as pg

import pypylon.pylon as pylon
from pypylon import _genicam as gen

from basler_camera_wrapper import Basler_Camera, TriggerMode
from camera_window import CameraWindow
from settings_window import SettingsWindow
import faulthandler

packet_size = 1200
binning = 1

class Beamview(QtWidgets.QMainWindow):
    def __init__(self, root, app):
        super().__init__()
        # layout = QtWidgets.QGridLayout()
        # self.setLayout(layout)
        self.setMinimumSize(200, 200)
        self.setWindowTitle('Camera list')
        self.app = app
        self.archive_mode = False
        self.archive_time = 300
        self.archive_dir = os.path.expanduser(os.path.join('~', 'nir_archive'))
        print(self.archive_dir)
        tlf = pylon.TlFactory.GetInstance()
        self.devices = tlf.EnumerateDevices()
        for i, device in enumerate(self.devices):
            if device.GetUserDefinedName() == '':
                device.SetUserDefinedName(f'Camera {i}')

        self.cam_window = CameraWindow(self, app)
        self.settings_window = SettingsWindow(self, app)
            
        self.camera_list = QtWidgets.QTreeView(self)
        self.camera_list_model = BoldItemModel()
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
        
        self.selected_camera = None
        
    def set_archive_mode(self, archive):
        self.archive_mode = archive
        self.cam_window.archive_action.setChecked(archive)

    def select_camera(self, cam):
        self.selected_camera = cam
        self.cam_window.activate_frame(cam)
            
    def add_camera(self, *args):
        index = self.camera_list.currentIndex().row()
        self.camera_list_model.boldRow(index)
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
            frame = self.cam_window.add_camera(cam)
            self.settings_window.add_camera(cam, frame)
            self.select_camera(cam)

    def remove_camera(self, cam):
        self.settings_window.remove_camera(cam)
        if cam.serial_number in self.opened_cameras:
            del self.opened_cameras[cam.serial_number]
            self.camera_list_model.unboldRow(self.find_camera_index(cam))
            

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
            
    def closeEvent(self, event):
        self.app.quit()
        
class BoldItemModel(QtGui.QStandardItemModel):
    def __init__(self):
        self._bold_rows = []
        super().__init__()
    
    def appendRow(self, args):
        self._bold_rows.append(False)
        super().appendRow(args)
        
    def emitRowChanged(self, row):
        for col in (0, 1):
            index = self.index(row, col)
            self.dataChanged.emit(index, index)
    
    def boldRow(self, row):
        self._bold_rows[row] = True
        self.emitRowChanged(row)
    
    def unboldRow(self, row):
        self._bold_rows[row] = False
        self.emitRowChanged(row)
    
    def data(self, index, role):
        if role == QtCore.Qt.FontRole:
            if self._bold_rows[index.row()]:
                boldFont = QtGui.QFont()
                boldFont.setBold(True)
                return boldFont
        return super().data(index, role)
            
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
