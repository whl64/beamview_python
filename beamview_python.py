import matplotlib as mpl

mpl.use('TkAgg')
import argparse
import os
import tkinter as tk
from tkinter import messagebox, ttk

import pypylon.pylon as pylon
from pypylon import _genicam as gen

from basler_camera_wrapper import Basler_Camera, TriggerMode
from camera_window import CameraWindow
from settings_window import SettingsWindow


class Beamview(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Camera list')
                
        tlf = pylon.TlFactory.GetInstance()
        self.devices = tlf.EnumerateDevices()
        for i, device in enumerate(self.devices):
            if device.GetUserDefinedName() == '':
                device.SetUserDefinedName(f'Camera {i}')

        self.cam_window = CameraWindow(self)
        self.settings_window = SettingsWindow(self)
        
        self.camera_list = ttk.Treeview(self, columns=('name', 'model'), show='headings', selectmode='browse')
        self.camera_list.heading('name', text='Name')
        self.camera_list.heading('model', text='Model')
#        self.camera_list.heading('address', text='IP Address')
        
        device_display = []
        for device in self.devices:
            self.camera_list.insert('', tk.END, values=(device.GetUserDefinedName(), device.GetModelName()))
        
        self.camera_list.grid(row=0, column=0)
        self.camera_list.bind('<Double-Button-1>', self.add_camera)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.camera_list.yview)
        self.camera_list.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.opened_cameras = {}
            
    def add_camera(self, *args):
        index = self.camera_list.index(self.camera_list.selection()[0])
        serial_number = self.devices[index].GetSerialNumber()
        if serial_number not in self.opened_cameras:
            try:
                cam  = Basler_Camera(serial_number, TriggerMode.SOFTWARE)
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
            
def main():
    parser = argparse.ArgumentParser(description='Multicam Beamview.')
    parser.add_argument('--debug', help='create emulated cameras for debugging', action='store_true')
    args = parser.parse_args()
    if args.debug:
        number_of_emulated_cameras = 5
        os.environ['PYLON_CAMEMU'] = str(number_of_emulated_cameras)

    beamview = Beamview()
    beamview.mainloop()
    
if __name__ == '__main__':
    main()
