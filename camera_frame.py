from multiprocessing.sharedctypes import Value
from tkinter.tix import COLUMN
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

class CameraFrame(tk.Frame):    
    def __init__(self, master, cam):
        super().__init__(master)
        self.cam = cam
        self.default_fig_width = 5
        # set up plotting canvas
        info_frame = ttk.Frame(self)
        info_frame.grid(row=0, column=0)
                
        ttk.Label(info_frame, text=self.cam.name).grid(row=0, column=0, padx=(10, 5))
        
        self.status_string = tk.StringVar(value='Stopped.')
        ttk.Label(info_frame, textvariable=self.status_string)
        
        self.frame_time_string = tk.StringVar(value='Frame time: 0.00 s')
        ttk.Label(info_frame, textvariable=self.frame_time_string).grid(row=0, column=2, padx=(5, 5))
        
        self.centroid_string = tk.StringVar(value='Centroid (px): (N/A, N/A)')
        ttk.Label(info_frame, textvariable=self.centroid_string).grid(row=0, column=3, padx=(5, 5))
                
        self.calc_threshold = 0
        
        self.max_data_percent_string = tk.StringVar(value='Max data: 0.0%')
        self.max_data_label = ttk.Label(info_frame, textvariable=self.max_data_percent_string)
        self.max_data_label.grid(row=0, column=5, padx=(5, 10))
        
        self.threshold = 0

        if self.cam.pixel_format == 'Mono16':
            self.bit_depth = 16
        elif self.cam.pixel_format == 'Mono12':
            self.bit_depth = 12
        else:
            self.bit_depth = 12  # default to 12-bit
            
        self.vmin = 0
        self.vmax = 2**self.bit_depth - 1
        
        self.fig = Figure(figsize=(self.default_fig_width, self.default_fig_width * self.cam.max_height/self.cam.max_width))
        self.fig.set_tight_layout(True)
        self.ax = self.fig.add_subplot()
        self.ax.set_title(self.cam.name)
        self.image = self.ax.imshow(np.zeros((self.cam.height, self.cam.width)), vmin=self.vmin, vmax=self.vmax,
                                    extent=(self.cam.offset_x, self.cam.offset_x + self.cam.width,
                                            self.cam.offset_y + self.cam.height, self.cam.offset_y))
        divider = make_axes_locatable(self.ax)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        self.cbar = self.fig.colorbar(self.image, cax=cax)

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky='nesw')
        
        self.axis_update_required = False
        
        # set resizing priorities (higher weight gets more room)
        self.grid_rowconfigure(0, weight=3, minsize=20)
        self.grid_rowconfigure(1, weight=1)
        
        self.prev_frame_timestamp = time.time()
        self.use_median_filter = tk.BooleanVar(value=False)
        self.calculate_stats = tk.BooleanVar(value=True)
        self.use_threshold = tk.BooleanVar(value=False)
        self.stop_camera()
            
    def cleanup(self):
        self.cam.stop_grabbing()
        self.cam.release_camera()
        self.destroy()
    
    def start_camera(self):
        self.cam.start_grabbing()
        self.status_string.set('Running.')
        self.update_frames()
        
    def stop_camera(self):
        self.cam.stop_grabbing()
        self.status_string.set('Stopped.')
    
    def update_frames(self):
        if self.cam.is_grabbing():
            try:
                frame = self.cam.return_frame()
                frame_time = time.time() - self.prev_frame_timestamp
                self.prev_frame_timestamp = time.time()
                if frame_time > 50:
                    frame_time = 50
                self.frame_time_string.set(f'Frame time: {frame_time:.3f} s')

                if self.use_median_filter.get():
                    frame = ndi.median_filter(frame, size=2)
                    
                if self.calculate_stats.get():
                    calc_frame = np.copy(frame)
                    max_data = np.max(calc_frame)
                    calc_frame[calc_frame < max_data*self.calc_threshold/100] = 0
                    calc_frame = calc_frame.astype(float)
                    calc_frame /= np.sum(calc_frame)
                    
                    x_values = np.arange(self.cam.offset_x, self.cam.offset_x + self.cam.width)
                    y_values = np.arange(self.cam.offset_y, self.cam.offset_y + self.cam.height)
                    
                    xx, yy = np.meshgrid(x_values, y_values, indexing='xy')
                    
                    centroid_x = np.sum(xx * calc_frame)
                    centroid_y = np.sum(yy * calc_frame)
                    
                    self.centroid_string.set(f'Centroid (px): ({centroid_x:.1f}, {centroid_y:.1f})')
                    
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
            
            
            