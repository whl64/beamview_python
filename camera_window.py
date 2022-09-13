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
    def __init__(self, address):
        super().__init__()
        self.frames_hidden = False
        self.aux_frames = []
        self.default_fig_width = 5
        self.base_entry_width = 6  # default width for entries
        self.threshold = 0  # image thresholding
        self.running_widgets = []  # widgets that should only be active while camera is running
        self.not_running_widgets = [] # widgets that should only be active while camera is not running
        
        self.cam = Basler_Camera(address)
        
        self.title(f'{self.cam.name}: Stopped.')
        
        if self.cam.pixel_format == 'Mono16':
            self.bit_depth = 16
        elif self.cam.pixel_format == 'Mono12':
            self.bit_depth = 12
        else:
            self.bit_depth = 12  # default to 12-bit
            
        self.vmin = 0
        self.vmax = 2**self.bit_depth - 1
        
        self.show_hide_button_string = tk.StringVar(value='Hide setting frames')
        ttk.Button(self, textvariable=self.show_hide_button_string, command=self.show_or_hide_frames).grid(row=0, column=0)
        
        # set up plotting canvas
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
        
        self.build_side_frame()
        
        self.build_bottom_frame()
        
        # set resizing priorities (higher weight gets more room)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=3, minsize=20)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=1)
        
        self.axis_update_required = False
        self.stop_camera()
        
        self.protocol('WM_DELETE_WINDOW', self.cleanup)
    
    def cleanup(self):
        self.cam.stop_grabbing()
        self.cam.release_camera()
        self.destroy()
        
    def show_or_hide_frames(self, *args):
        if self.frames_hidden:
            self.frames_hidden = False
            self.show_hide_button_string.set('Hide setting frames')
            self.side_frame.grid(row=1, column=1, rowspan=3)
            self.bottom_frame.grid(row=2, column=0)         
        else:
            self.frames_hidden = True
            self.show_hide_button_string.set('Show setting frames')
            self.side_frame.grid_forget()
            self.bottom_frame.grid_forget()
    
    def build_side_frame(self):
        self.side_frame = ttk.Frame(self)
        self.side_frame.grid(row=1, column=1, rowspan=3)
        
        # label that displays frame time
        self.frame_time_string = tk.StringVar(value='Frame time: 0.000 s')
        frame_time_label = ttk.Label(self.side_frame, textvariable=self.frame_time_string)
        frame_time_label.grid(row=0, column=0, columnspan=2)
        self.running_widgets.append(frame_time_label)
        
        # button to start camera
        start_button = ttk.Button(self.side_frame, text='Start', command=self.start_camera)
        start_button.grid(row=1, column=0)
        self.not_running_widgets.append(start_button)
        
        # button to stop camera
        stop_button = ttk.Button(self.side_frame, text='Stop', command=self.stop_camera)
        stop_button.grid(row=1, column=1)
        self.running_widgets.append(stop_button)
        
        # label that displays the maximum pixel value in the frame
        # as a percentage of the maximum possible pixel value from the bit depth
        self.max_data_percent_string = tk.StringVar(value='Max data: 0.0%')
        self.max_data_label = ttk.Label(self.side_frame, textvariable=self.max_data_percent_string)
        self.max_data_label.grid(row=2, column=0, columnspan=2)
        self.running_widgets.append(self.max_data_label)
        
        # frame that displays information about beam statistics (centroid, size)
        stat_frame = ttk.LabelFrame(self.side_frame, text='Beam statistics')
        stat_frame.grid(row=3, column=0, columnspan=2)
        
        self.calculate_stats = tk.BooleanVar()
        ttk.Checkbutton(stat_frame, variable=self.calculate_stats, text='Calculate statistics?').grid(row=0, column=0, columnspan=2)
        
        ttk.Label(stat_frame, text='Threshold for calculations (%): ').grid(row=1, column=0)
        self.calc_threshold_string = tk.IntVar(value=0)
        self.calc_threshold = 0
        calc_threshold_entry = ttk.Entry(stat_frame, textvariable=self.calc_threshold_string, validate='focusout',
                                         validatecommand=self.calc_threshold_changed, width=self.base_entry_width)
        calc_threshold_entry.bind('<Return>', self.calc_threshold_changed)
        calc_threshold_entry.grid(row=1, column=1)
        
        self.centroid_x_string = tk.StringVar(value='Centroid x (px): N/A')
        self.centroid_y_string = tk.StringVar(value='Centroid y (px): N/A')
        self.size_x_string = tk.StringVar(value='Size x (px): N/A')
        self.size_y_string = tk.StringVar(value='Size y (px): N/A')

        ttk.Label(stat_frame, textvariable=self.centroid_x_string).grid(row=2, column=0, padx=(10, 5))
        ttk.Label(stat_frame, textvariable=self.centroid_y_string).grid(row=2, column=1, padx=(5,10))
        ttk.Label(stat_frame, textvariable=self.size_x_string).grid(row=3, column=0, padx=(10, 5))
        ttk.Label(stat_frame, textvariable=self.size_y_string).grid(row=3, column=1, padx=(5,10))
        
        # frame that contains image post-processing controls (threshold, median filter)
        proc_frame = ttk.LabelFrame(self.side_frame, text='Image processing controls')
        proc_frame.grid(row=4, column=0, columnspan=2)
        
        self.use_threshold = tk.BooleanVar()
        ttk.Checkbutton(proc_frame, text='Use threshold?', variable=self.use_threshold).grid(row=1, column=0, sticky='w')
        ttk.Label(proc_frame, text='Threshold value (%): ').grid(row=1, column=1)        
        self.threshold_string = tk.IntVar(value=self.threshold)
        thresh_entry = ttk.Entry(proc_frame, textvariable=self.threshold_string, validate='focusout',
                                 validatecommand=self.threshold_changed, width=self.base_entry_width)
        thresh_entry.bind('<Return>', self.threshold_changed)
        thresh_entry.grid(row=1, column=2)
        self.use_median_filter = tk.BooleanVar()
        ttk.Checkbutton(proc_frame, text='Use median filter?', variable=self.use_median_filter).grid(row=0, column=0, sticky='w')
        
    def build_bottom_frame(self):
        self.bottom_frame = ttk.Frame(self)
        self.aux_frames.append(self.bottom_frame)

        self.bottom_frame.grid(row=2, column=0)
        
        # frame that contains exposure time and gain controls
        acq_frame = ttk.LabelFrame(self.bottom_frame, text='Acquisition controls', padding=(0, 0, 10, 0))        
        acq_frame.grid(row=0, column=0, padx=(0, 10))

        ttk.Label(acq_frame, text='Exposure time (ms): ').grid(row=0, column=0, sticky='e')
        self.exposure_string = tk.DoubleVar(value=self.cam.exposure)
        exposure_entry = ttk.Entry(acq_frame, textvariable=self.exposure_string, validate='focusout',
                                        validatecommand=self.exposure_changed, width=self.base_entry_width)
        exposure_entry.grid(row=0, column=1)
        exposure_entry.bind('<Return>', self.exposure_changed)
        
        ttk.Label(acq_frame, text='Gain: ').grid(row=1, column=0, sticky='e')
        self.gain_string = tk.IntVar(value=self.cam.gain)
        gain_entry = ttk.Entry(acq_frame, textvariable=self.gain_string, validate='focusout',
                               validatecommand=self.gain_changed, width=self.base_entry_width)
        gain_entry.grid(row=1, column=1)
        gain_entry.bind('<Return>', self.gain_changed)
        self.prev_frame_timestamp = time.time()
        
        
        # frame that contains AOI controls
        size_frame = ttk.LabelFrame(self.bottom_frame, text='AOI controls', padding=(10, 0, 0, 0))
        size_frame.grid(row=0, column=1, padx=(10, 10))
        
        ttk.Label(size_frame, text='x:').grid(row=0, column=0)
        ttk.Label(size_frame, text='-').grid(row=0, column=2)
        ttk.Label(size_frame, text='y:').grid(row=1, column=0)
        ttk.Label(size_frame, text='-').grid(row=1, column=2)
        
        ttk.Button(size_frame, command=self.reset_size, text='Reset').grid(row=0, column=4, rowspan=2)
        
        self.min_x_string = tk.IntVar(value=self.cam.offset_x)
        self.min_y_string = tk.IntVar(value=self.cam.offset_y)
        self.max_x_string = tk.IntVar(value=self.cam.offset_x + self.cam.width)
        self.max_y_string = tk.IntVar(value=self.cam.offset_y + self.cam.height)

        min_x_entry = ttk.Entry(size_frame, textvariable=self.min_x_string, validate='focusout',
                                validatecommand=self.size_changed, width=self.base_entry_width)
        max_x_entry = ttk.Entry(size_frame, textvariable=self.max_x_string, validate='focusout',
                                validatecommand=self.size_changed, width=self.base_entry_width)
        min_y_entry = ttk.Entry(size_frame, textvariable=self.min_y_string, validate='focusout',
                        validatecommand=self.size_changed, width=self.base_entry_width)
        max_y_entry = ttk.Entry(size_frame, textvariable=self.max_y_string, validate='focusout',
                                validatecommand=self.size_changed, width=self.base_entry_width)
        
        min_x_entry.bind('<Return>', self.size_changed)
        min_y_entry.bind('<Return>', self.size_changed, add='+')
        max_x_entry.bind('<Return>', self.size_changed, add='+')
        max_y_entry.bind('<Return>', self.size_changed, add='+')
        
        min_x_entry.grid(row=0, column=1)
        max_x_entry.grid(row=0, column=3)
        min_y_entry.grid(row=1, column=1)
        max_y_entry.grid(row=1, column=3)    
        
        self.not_running_widgets += size_frame.winfo_children()
        
        
    def calc_threshold_changed(self, *args):
        try:
            self.calc_threshold = self.calc_threshold_string.get()
            print(self.calc_threshold)
            if self.calc_threshold < 0:
                self.calc_threshold = 0
            elif self.calc_threshold > 100:
                self.calc_threshold = 100
        except tk.TclError:
            pass
        
        self.calc_threshold_string.set(self.calc_threshold)
    
    def threshold_changed(self, *args):
        try:
            self.threshold = self.threshold_string.get()
            print(self.threshold)
            if self.threshold < 0:
                self.threshold = 0
            elif self.threshold > 100:
                self.threshold = 100
        except tk.TclError:
            pass
        
        self.threshold_string.set(self.threshold)
        
    def reset_size(self):
        self.min_x_string.set(0)
        self.min_y_string.set(0)
        self.max_x_string.set(self.cam.max_width)
        self.max_y_string.set(self.cam.max_height)
        self.size_changed()
        
    def size_changed(self, *args):
        try:
            min_x = self.min_x_string.get()
            min_y = self.min_y_string.get()
            max_x = self.max_x_string.get()
            max_y = self.max_y_string.get()
            
            if min_x < 0:
                min_x = 0
            elif min_x > self.cam.max_width - 4:
                min_x = self.cam.max_width - 4
                
            if min_y < 0:
                min_y = 0
            elif min_y > self.cam.max_height - 4:
                min_y = self.cam.max_height - 4
            
            if max_x - min_x < 4:
                max_x = min_x + 4
            elif max_x > self.cam.max_width:
                max_x = self.cam.max_width
            
            if max_y - min_y < 4:
                max_y = min_y + 4
            elif max_y > self.cam.max_height:
                max_y = self.cam.max_height
                
            if min_x > self.cam.offset_x:
                self.cam.width = max_x - min_x
                self.cam.offset_x = min_x
            else:
                self.cam.offset_x = min_x
                self.cam.width = max_x - min_x
            if min_y > self.cam.offset_y:
                self.cam.height = max_y - min_y
                self.cam.offset_y = min_y
            else:
                self.cam.offset_y = min_y   
                self.cam.height = max_y - min_y
        except tk.TclError:
            pass
        
        self.min_x_string.set(self.cam.offset_x)
        self.min_y_string.set(self.cam.offset_y)
        self.max_x_string.set(self.cam.offset_x + self.cam.width)
        self.max_y_string.set(self.cam.offset_y + self.cam.height)
        
        self.axis_update_required = True

    def gain_changed(self, *args):
        try:
            self.cam.gain = self.gain_string.get()
        except tk.TclError:
            pass
        print(self.cam.gain)
        self.gain_string.set(self.cam.gain)
    
    def exposure_changed(self, *args):
        try:
            self.cam.exposure = self.exposure_string.get()
        except tk.TclError:
            pass
        print(self.cam.exposure)
        self.exposure_string.set(self.cam.exposure)
    
    def start_camera(self):
        self.cam.start_grabbing()
        for w in self.not_running_widgets:
            w.configure(state='disable')
            
        for w in self.running_widgets:
            w.configure(state='enable')
        self.update_frames()
        
    def stop_camera(self):
        self.cam.stop_grabbing()
        self.title(f'{self.cam.name}: Stopped.')

        for w in self.running_widgets:
            w.configure(state='disabled')
            
        for w in self.not_running_widgets:
            w.configure(state='!disabled')
    
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
            
            
            