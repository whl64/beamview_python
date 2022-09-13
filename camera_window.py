from multiprocessing.sharedctypes import Value
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
import scipy.ndimage as ndi
from camera_frame import CameraFrame

class CameraWindow(tk.Toplevel):    
    def __init__(self, root):
        super().__init__()
        self.title('Beamview')
        self.camera_frames = {}
        self.protocol('WM_DELETE_WINDOW', self.cleanup)
        self.root = root
        self.update_frames()
    
    def cleanup(self):
        self.root.destroy()
    
    def add_camera(self, cam):
        frame = CameraFrame(self, cam)
        self.camera_frames[cam.serial_number] = frame
        assigned_row = (len(self.camera_frames) - 1)%2
        assigned_column = int((len(self.camera_frames) - 1)/2)
        frame.grid(row=assigned_row, column=assigned_column, sticky='nsew')
        
        for col in range(self.grid_size()[0]):
            self.grid_columnconfigure(col, weight=1)
            
        for row in range(self.grid_size()[1]):
            self.grid_rowconfigure(row, weight=1)
            
        return frame
        
    def update_frames(self):
        for address in self.camera_frames:
            self.camera_frames[address].update_frames()
        self.after(50, self.update_frames)

