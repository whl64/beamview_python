from select import select
import matplotlib as mpl
mpl.use('TkAgg')
from matplotlib.figure import Figure
import numpy as np
import pypylon.pylon as pylon
from basler_camera_wrapper import Basler_Camera
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.axes_grid1 import make_axes_locatable
import time
import numpy as np
from camera_window import CameraWindow

class Beamview(tk.Tk):
    def __init__(self):
        super().__init__()
                
        self.title('Beamview')

        tlf = pylon.TlFactory.GetInstance()
        devices = tlf.EnumerateDevices()
        
        self.camera_list = ttk.Treeview(self, columns=('name', 'model', 'address'), show='headings', selectmode='browse')
        self.camera_list.heading('name', text='Name')
        self.camera_list.heading('model', text='Model')
        self.camera_list.heading('address', text='IP Address')
        
        device_display = []
        
        for device in devices:
            self.camera_list.insert('', tk.END, values=(device.GetUserDefinedName(), device.GetModelName(), device.GetAddress()))
        
        self.camera_list.grid(row=0, column=0)
        self.camera_list.bind('<Double-Button-1>', self.open_camera_window)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.camera_list.yview)
        self.camera_list.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.opened_cameras = {}
            
    def open_camera_window(self, *args):
        item = self.camera_list.item(self.camera_list.selection()[0])
        address = item['values'][2]
        try:
            self.opened_cameras[address].lift()
        except:
            self.opened_cameras[address] = CameraWindow(address)

        
        
def main():
    beamview = Beamview()
    beamview.mainloop()
    
if __name__ == '__main__':
    main()