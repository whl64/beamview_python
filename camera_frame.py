import matplotlib as mpl

from image_grabber import ImageGrabber

mpl.use('TkAgg')
import time
import tkinter as tk
from tkinter import ttk
import threading

import numpy as np
import scipy.ndimage as ndi
from lmfit.models import ConstantModel, Gaussian2dModel
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable

from basler_camera_wrapper import TriggerMode


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
        elif self.cam.pixel_format == 'Mono8':
            self.bit_depth = 8  # default to 12-bit
            
        self.vmin = 0
        self.vmax = 2**self.bit_depth - 1
        
        self.fig = Figure(figsize=(self.default_fig_width, self.default_fig_width * self.cam.max_height/self.cam.max_width))
        self.fig.set_tight_layout(True)
        self.ax = self.fig.add_subplot()
        self.ax.set_title(self.cam.name)
        self.plot_data = np.array([])
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
        self.lock = threading.Lock()
        self.frame_available = False
        self.currently_drawing = False
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
        self.cam.register_event_handler(ImageGrabber(self))
        self.status_string.set('Running.')
        try:
            self.cam.request_frame()
        except:
            print('trigger timed out')
        threading.Thread(target=self.update_frames, daemon=True).start()
        
    def stop_camera(self):
        self.cam.stop_grabbing()
        self.status_string.set('Stopped.')
        
    def auto_range(self):
        self.vmin = np.min(self.plot_data)
        self.vmax = np.max(self.plot_data)
        self.axis_update_required = 1
        
    def reset_range(self):
        self.vmin = 0
        self.vmax = 2**self.bit_depth - 1
        self.axis_update_required = 1
    
    def update_frames(self):
        while 1:
            if self.cam.is_grabbing():
                if self.cam.trigger_mode == TriggerMode.FREERUN:
                    self.plot_data = self.cam.return_frame()
                    self.draw_frame()
                elif self.cam.trigger_mode == TriggerMode.SOFTWARE:
                    if self.frame_available:
                        self.frame_available = False
                        self.draw_frame()
            else:
                break
            
    def draw_frame(self):
        plot_data = self.plot_data
        
        try:
            frame_time = time.time() - self.prev_frame_timestamp
            self.prev_frame_timestamp = time.time()
            if frame_time > 50:
                frame_time = 50
            self.frame_time_string.set(f'Frame time: {frame_time:.3f} s')

            if self.use_median_filter.get():
                plot_data = ndi.median_filter(plot_data, size=2)
                
            max_data_percent = 100 * np.max(plot_data) / (2**self.bit_depth - 1)
            self.max_data_percent_string.set(f'Max data: {max_data_percent:.1f}%')
            if max_data_percent > 97:
                self.max_data_label.config(background='red')
            else:
                self.max_data_label.config(background=self.cget('background'))

            if self.use_threshold.get():
                max_data = np.max(plot_data)
                plot_data[plot_data < max_data*self.threshold/100] = 0
                
            if self.calculate_stats.get():
                calc_plot_data = np.copy(plot_data)
                max_data = np.max(calc_plot_data)
                # calc_frame[calc_frame < max_data*self.calc_threshold/100] = 0
                calc_plot_data = calc_plot_data.astype(float)
                calc_plot_data /= np.sum(calc_plot_data)
                
                x_values = np.arange(self.cam.offset_x, self.cam.offset_x + self.cam.width).astype(float)
                y_values = np.arange(self.cam.offset_y, self.cam.offset_y + self.cam.height).astype(float)
                
                if self.use_calibration.get():
                    x_values *= self.pixel_calibration/1000
                    y_values *= self.pixel_calibration/1000
                    unit = '(mm)'
                else:
                    unit = '(px)'
                
                xx, yy = np.meshgrid(x_values, y_values, indexing='xy')
                
                centroid_x = np.sum(xx * calc_plot_data)
                centroid_y = np.sum(yy * calc_plot_data)
                
                sigma_x = np.sqrt(np.sum((xx - centroid_x)**2 * calc_plot_data))
                sigma_y = np.sqrt(np.sum((yy - centroid_y)**2 * calc_plot_data))
                
                # model = Gaussian2dModel() + ConstantModel()
                
                # model.set_param_hint('amplitude', min=0, value=np.max(calc_plot_data))
                # model.set_param_hint('centerx', value=centroid_x)
                # model.set_param_hint('sigmax', value=sigma_x)
                # model.set_param_hint('centery', value=centroid_y)
                # model.set_param_hint('sigmay', value=sigma_y)
                # model.set_param_hint('c', value=np.min(calc_plot_data))
                
                # params = model.make_params()

                # result = model.fit(calc_frame.flatten(), params=params, x=xx.flatten(), y=yy.flatten())              
                
                self.centroid_string.set(f'Centroid {unit}: ({centroid_x:.2f}, {centroid_y:.2f})') 
                                        #+ f'fit: ({result.params["centerx"].value:.1f}, {result.params["centery"].value:.1f}')
                
                self.sigma_string.set(f'Sigma {unit}: ({sigma_x:.2f}, {sigma_y:.2f})') 
#                                   + f'fit: ({result.params["sigmax"].value:.1f}, {result.params["sigmay"].value:.1f}') """
            if self.axis_update_required:
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
            
                self.image = self.ax.imshow(plot_data, vmin=self.vmin, vmax=self.vmax, extent=extent)
                divider = make_axes_locatable(self.ax)
                cax = divider.append_axes('right', size='5%', pad=0.05)
                self.cbar = self.fig.colorbar(self.image, cax=cax)
                self.canvas.draw()
                self.axis_update_required = False
            else:
                self.image.set_data(plot_data)
                self.ax.draw_artist(self.image)
                self.fig.canvas.blit(self.fig.bbox)
                self.fig.canvas.flush_events()
            if self.cam.trigger_mode == TriggerMode.FREERUN:
                self.plot_data = plot_data
        except RuntimeError as e:
            print(e)
        
            
            
