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

class CameraWindow(tk.Toplevel):    
    def __init__(self):
        super().__init__()
        self.camera_frames = []        
        self.protocol('WM_DELETE_WINDOW', self.cleanup)
    
    def cleanup(self):
        for camera_frame in self.camera_frames:
            camera_frame.cleanup()
        self.destroy()
    
    def update_frames(self):
        if self.cam.is_grabbing():
            try:
                frame = self.cam.return_frame()
                frame_time = time.time() - self.prev_frame_timestamp
                self.prev_frame_timestamp = time.time()
                if frame_time > 50:
                    frame_time = 50
                self.frame_time_string.set(f'Frame time: {frame_time:.3f} s')
                self.title(f'{self.cam.name}: Running. Frame time: {frame_time:.3f} s')

                if self.use_median_filter.get():
                    frame = ndi.median_filter(frame, size=2)
                    
                if self.calculate_stats.get():
                    calc_frame = np.copy(frame)
                    max_data = np.max(calc_frame)
                    calc_frame[calc_frame < max_data*self.calc_threshold/100] = 0
                    calc_frame = calc_frame.astype(float)
                    calc_frame /= np.sum(calc_frame)
                    
                    x_values = np.arange(self.min_x_string.get(), self.max_x_string.get())
                    y_values = np.arange(self.min_y_string.get(), self.max_y_string.get())
                    
                    xx, yy = np.meshgrid(x_values, y_values, indexing='xy')
                    
                    centroid_x = np.sum(xx * calc_frame)
                    centroid_y = np.sum(yy * calc_frame)
                    
                    self.centroid_x_string.set(f'Centroid x (px): {centroid_x:.1f}')
                    self.centroid_y_string.set(f'Centroid y (px): {centroid_y:.1f}')
                    
                max_data_percent = 100 * np.max(frame) / (2**self.bit_depth - 1)
                self.max_data_percent_string.set(f'Max data: {max_data_percent:.1f}%')
                if max_data_percent > 97:
                    self.max_data_label.config(background='red')
                else:
                    self.max_data_label.config(background=self.cget('background'))

                        
                if self.use_threshold.get():
                    max_data = np.max(frame)
                    frame[frame < max_data*self.threshold/100] = 0
                if self.axis_update_required:
                    print('axis updated')
                    self.ax.clear()
                    self.ax.set_title(self.cam.name)
                    self.image = self.ax.imshow(frame, vmin=self.vmin, vmax=self.vmax,
                                                extent=(self.cam.offset_x, self.cam.offset_x + self.cam.width,
                                                        self.cam.offset_y + self.cam.height, self.cam.offset_y))
                    self.axis_update_required = False
                else:
                    self.image.set_data(frame)
                self.canvas.draw()

            except RuntimeError as e:
                print(e)
            self.after(50, self.update_frames)
            
            
            