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
from lmfit import Model
from lmfit.models import Gaussian2dModel, ConstantModel

class CameraFrame(tk.Frame):    
    def __init__(self, master, cam):
        super().__init__(master)
        self.pixel_calibration = 1
        self.cam = cam
        self.default_fig_width = 5
        # set up plotting canvas
        status_frame = ttk.Frame(self)
        status_frame.grid(row=0, column=0)
        
        info_frame = ttk.Frame(status_frame)
        info_frame.grid(row=0, column=0)
                
        ttk.Label(info_frame, text=self.cam.name).grid(row=0, column=0, padx=(10, 5))
        
        self.status_string = tk.StringVar(value='Stopped.')
        ttk.Label(info_frame, textvariable=self.status_string).grid(row=0, column=1, padx=(10,10))
        
        self.frame_time_string = tk.StringVar(value='Frame time: 0.00 s')
        ttk.Label(info_frame, textvariable=self.frame_time_string).grid(row=0, column=2, padx=(5, 5))
        
        self.max_data_percent_string = tk.StringVar(value='Max data: 0.0%')
        self.max_data_label = ttk.Label(info_frame, textvariable=self.max_data_percent_string)
        self.max_data_label.grid(row=0, column=3, padx=(5, 10))
        
        self.centroid_string = tk.StringVar(value='Centroid (px): (N/A, N/A)')
        ttk.Label(info_frame, textvariable=self.centroid_string).grid(row=1, column=0, padx=(5, 5), columnspan=2)
        
        self.sigma_string = tk.StringVar(value='Sigmas (px): (N/A, N/A)')
        ttk.Label(info_frame, textvariable=self.sigma_string).grid(row=1, column=2, padx=(5, 5), columnspan=2)
        
        close_button = ttk.Button(status_frame, text='Close camera', command=self.close)
        close_button.grid(row=0, column=1, sticky='e')
                
        self.calc_threshold = 0
        
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
        self.grid_rowconfigure(0, weight=3, minsize=40)
        self.grid_rowconfigure(1, weight=1)
        
        self.prev_frame_timestamp = time.time()
        self.use_median_filter = tk.BooleanVar(value=False)
        self.calculate_stats = tk.BooleanVar(value=True)
        self.use_threshold = tk.BooleanVar(value=False)
        self.use_calibration = tk.BooleanVar(value=False)
        self.calibration = 1
        self.auto_range = 0
        self.reset_range = 0
        self.stop_camera()
    
    def close(self):
        self.cleanup()
        self.master.regrid()
        self.master.root.remove_camera(self.cam)
            
    def cleanup(self):
        self.cam.stop_grabbing()
        self.cam.release_camera()
        self.destroy()
    
    def start_camera(self):
        self.cam.start_grabbing()
        self.status_string.set('Running.')
        
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
                    
                max_data_percent = 100 * np.max(frame) / (2**self.bit_depth - 1)
                self.max_data_percent_string.set(f'Max data: {max_data_percent:.1f}%')
                if max_data_percent > 97:
                    self.max_data_label.config(background='red')
                else:
                    self.max_data_label.config(background=self.cget('background'))

                if self.use_threshold.get():
                    max_data = np.max(frame)
                    frame[frame < max_data*self.threshold/100] = 0
                    
                if self.calculate_stats.get():
                    calc_frame = np.copy(frame)
                    max_data = np.max(calc_frame)
                    # calc_frame[calc_frame < max_data*self.calc_threshold/100] = 0
                    calc_frame = calc_frame.astype(float)
                    calc_frame /= np.sum(calc_frame)
                    
                    x_values = np.arange(self.cam.offset_x, self.cam.offset_x + self.cam.width).astype(float)
                    y_values = np.arange(self.cam.offset_y, self.cam.offset_y + self.cam.height).astype(float)
                    
                    if self.use_calibration.get():
                        x_values *= self.pixel_calibration/1000
                        y_values *= self.pixel_calibration/1000
                        unit = '(mm)'
                    else:
                        unit = '(px)'
                    
                    xx, yy = np.meshgrid(x_values, y_values, indexing='xy')
                    
                    centroid_x = np.sum(xx * calc_frame)
                    centroid_y = np.sum(yy * calc_frame)
                    
                    sigma_x = np.sqrt(np.sum((xx - centroid_x)**2 * calc_frame))
                    sigma_y = np.sqrt(np.sum((yy - centroid_y)**2 * calc_frame))
                    
                    model = Gaussian2dModel() + ConstantModel()
                    
                    model.set_param_hint('amplitude', min=0, value=np.max(calc_frame))
                    model.set_param_hint('centerx', value=centroid_x)
                    model.set_param_hint('sigmax', value=sigma_x)
                    model.set_param_hint('centery', value=centroid_y)
                    model.set_param_hint('sigmay', value=sigma_y)
                    model.set_param_hint('c', value=np.min(calc_frame))
                    
                    params = model.make_params()
    
                    # result = model.fit(calc_frame.flatten(), params=params, x=xx.flatten(), y=yy.flatten())              
                    
                    self.centroid_string.set(f'Centroid {unit}: ({centroid_x:.2f}, {centroid_y:.2f})') 
                                            #+ f'fit: ({result.params["centerx"].value:.1f}, {result.params["centery"].value:.1f}')
                    
                    self.sigma_string.set(f'Sigma {unit}: ({sigma_x:.2f}, {sigma_y:.2f})') 
    #                                   + f'fit: ({result.params["sigmax"].value:.1f}, {result.params["sigmay"].value:.1f}') """
                    
                if self.axis_update_required or self.auto_range or self.reset_range:
                    if self.auto_range:
                        self.vmin = np.min(frame)
                        self.vmax = np.max(frame)
                        self.auto_range = 0
                    elif self.reset_range:
                        self.vmin = 0
                        self.vmax = 2**self.bit_depth - 1
                        self.reset_range = 0
                    self.fig.clear()
                    self.fig.set_tight_layout(True)
                    self.ax = self.fig.add_subplot()
                    self.ax.set_title(self.cam.name)
                    if self.use_calibration.get():
                        extent = (self.pixel_calibration * self.cam.offset_x, self.pixel_calibration * (self.cam.offset_x + self.cam.width),
                                  self.pixel_calibration * (self.cam.offset_y + self.cam.height), self.pixel_calibration * self.cam.offset_y)
                    else:
                        extent = (self.cam.offset_x, (self.cam.offset_x + self.cam.width),
                                  (self.cam.offset_y + self.cam.height), self.cam.offset_y)
                
                    self.image = self.ax.imshow(frame, vmin=self.vmin, vmax=self.vmax, extent=extent)
                    divider = make_axes_locatable(self.ax)
                    cax = divider.append_axes('right', size='5%', pad=0.05)
                    self.cbar = self.fig.colorbar(self.image, cax=cax)
                    self.axis_update_required = False
                else:
                    self.image.set_data(frame)
                self.canvas.draw()

            except RuntimeError as e:
                print(e)
            
            
            
