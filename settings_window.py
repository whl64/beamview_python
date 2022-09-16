from multiprocessing.sharedctypes import Value
from tkinter.tix import COLUMN
import matplotlib as mpl
mpl.use('TkAgg')
from matplotlib.figure import Figure
import numpy as np
import pypylon.pylon as pylon
from basler_camera_wrapper import Basler_Camera
import tkinter as tk
from tkinter import Checkbutton, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.axes_grid1 import make_axes_locatable
import time
import numpy as np
import scipy.ndimage as ndi

class SettingsWindow(tk.Toplevel):
    def __init__(self, root):
        super().__init__()
        self.title('Camera settings')
        self.base_entry_width = 6
        self.selection_box = ttk.Combobox(self, state='readonly')
        self.selection_box.bind('<<ComboboxSelected>>', self.selection_changed)
        self.selection_box.grid(row=0, column=0)
        self.active_cameras = {}
        self.camera_frames = {}
        
        self.running_widgets = []
        self.not_running_widgets = []
        
        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0)
        # button to start camera
        start_button = ttk.Button(button_frame, text='Start', command=self.start_camera)
        start_button.grid(row=0, column=0)
        self.not_running_widgets.append(start_button)
        
        # button to stop camera
        stop_button = ttk.Button(button_frame, text='Stop', command=self.stop_camera)
        stop_button.grid(row=0, column=1)
        self.running_widgets.append(stop_button)
        
        self.threshold = 0
        self.calc_threshold = 0
        self.calibration = 0
        
        self.build_stat_frame()
        self.build_proc_frame()
        self.build_camera_frame()
        self.protocol('WM_DELETE_WINDOW', self.cleanup)
        self.root = root
        
    def cleanup(self):
        self.root.destroy()

    def start_camera(self):
        self.frame.start_camera()
        for w in self.not_running_widgets:
            w.configure(state='disable')
            
        for w in self.running_widgets:
            w.configure(state='enable')
        
    def stop_camera(self):
        self.frame.stop_camera()
        for w in self.running_widgets:
            w.configure(state='disabled')
            
        for w in self.not_running_widgets:
            w.configure(state='!disabled')
    
    def selection_changed(self, *args):
        self.cam = self.active_cameras[self.selection_box.get()]
        self.frame = self.camera_frames[self.selection_box.get()]
        if self.cam.is_grabbing():
            for w in self.not_running_widgets:
                w.configure(state='disable')
            for w in self.running_widgets:
                w.configure(state='enable')
        else:
            for w in self.running_widgets:
                w.configure(state='disabled')
            for w in self.not_running_widgets:
                w.configure(state='!disabled')
                
        self.thresh_check.configure(variable=self.frame.use_threshold)
        self.median_check.configure(variable=self.frame.use_median_filter)
        self.stat_check.configure(variable=self.frame.calculate_stats)
        self.calibration_check.configure(variable=self.frame.use_calibration)
        self.threshold = self.frame.threshold
        self.calc_threshold = self.frame.calc_threshold
        self.threshold_string.set(self.threshold)
        self.calc_threshold_string.set(self.calc_threshold)
        
        self.exposure_string.set(self.cam.exposure)
        self.gain_string.set(self.cam.gain)
        
        self.min_x_string.set(self.cam.offset_x)
        self.min_y_string.set(self.cam.offset_y)
        self.max_x_string.set(self.cam.offset_x + self.cam.width)
        self.max_y_string.set(self.cam.offset_y + self.cam.height)
        
    def add_camera(self, cam, frame):
        self.selection_box['values'] = (*self.selection_box['values'], cam.name)
        self.selection_box.set(cam.name)
        self.active_cameras[cam.name] = cam
        self.camera_frames[cam.name] = frame
        self.selection_changed()
        
    def set_range(self):
        self.frame.auto_range = 1

    def reset_range(self):
        self.frame.reset_range = 1
  
    def build_stat_frame(self):
        stat_frame = ttk.LabelFrame(self, text='Beam statistics')
        self.stat_check = ttk.Checkbutton(stat_frame, text='Calculate statistics?')
        self.stat_check.grid(row=0, column=0, columnspan=2)

        set_range_button = ttk.Button(stat_frame, command=self.set_range, text='Set range')
        reset_range_button = ttk.Button(stat_frame, command=self.reset_range, text='Reset')
        set_range_button.grid(row=1, column=0)
        reset_range_button.grid(row=1, column=1)
        
        # ttk.Label(stat_frame, text='Threshold for calculations (%): ').grid(row=1, column=0)
        self.calc_threshold_string = tk.IntVar(value=0)
        self.calc_threshold = 0
        # calc_threshold_entry = ttk.Entry(stat_frame, textvariable=self.calc_threshold_string, validate='focusout',
        #                                  validatecommand=self.calc_threshold_changed, width=self.base_entry_width)
        # calc_threshold_entry.bind('<Return>', self.calc_threshold_changed)
        # # calc_threshold_entry.grid(row=1, column=1)
        
        # self.centroid_x_string = tk.StringVar(value='Centroid x (px): N/A')
        # self.centroid_y_string = tk.StringVar(value='Centroid y (px): N/A')
        # self.size_x_string = tk.StringVar(value='Size x (px): N/A')
        # self.size_y_string = tk.StringVar(value='Size y (px): N/A')

        # ttk.Label(stat_frame, textvariable=self.centroid_x_string).grid(row=2, column=0, padx=(10, 5))
        # ttk.Label(stat_frame, textvariable=self.centroid_y_string).grid(row=2, column=1, padx=(5,10))
        # ttk.Label(stat_frame, textvariable=self.size_x_string).grid(row=3, column=0, padx=(10, 5))
        # ttk.Label(stat_frame, textvariable=self.size_y_string).grid(row=3, column=1, padx=(5,10))
        stat_frame.grid(row=2, column=0)

        
    def build_proc_frame(self):
        # frame that contains image post-processing controls (threshold, median filter)
        proc_frame = ttk.LabelFrame(self, text='Image processing controls')
        
        self.thresh_check = ttk.Checkbutton(proc_frame, text='Use threshold?')
        self.thresh_check.grid(row=1, column=0, sticky='w')
        ttk.Label(proc_frame, text='Threshold value (%): ').grid(row=1, column=1)        
        self.threshold_string = tk.IntVar(value=self.threshold)
        thresh_entry = ttk.Entry(proc_frame, textvariable=self.threshold_string, validate='focusout',
                                 validatecommand=self.threshold_changed, width=self.base_entry_width)
        thresh_entry.bind('<Return>', self.threshold_changed)
        thresh_entry.grid(row=1, column=2)
        self.median_check = ttk.Checkbutton(proc_frame, text='Use median filter?')
        self.median_check.grid(row=0, column=0, sticky='w')
        
        proc_frame.grid(row=3, column=0)
    
    def build_camera_frame(self):
        self.bottom_frame = ttk.Frame(self)
        self.bottom_frame.grid(row=4, column=0)
        
        # frame that contains exposure time and gain controls
        acq_frame = ttk.LabelFrame(self.bottom_frame, text='Acquisition controls', padding=(0, 0, 10, 0))        
        acq_frame.grid(row=0, column=0, padx=(0, 10))

        ttk.Label(acq_frame, text='Exposure time (ms): ').grid(row=0, column=0, sticky='e')
        self.exposure_string = tk.DoubleVar(value=0)
        exposure_entry = ttk.Entry(acq_frame, textvariable=self.exposure_string, validate='focusout',
                                        validatecommand=self.exposure_changed, width=self.base_entry_width)
        exposure_entry.grid(row=0, column=1)
        exposure_entry.bind('<Return>', self.exposure_changed)
        
        ttk.Label(acq_frame, text='Gain: ').grid(row=1, column=0, sticky='e')
        self.gain_string = tk.IntVar(value=0)
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
        
        self.min_x_string = tk.IntVar(value=0)
        self.min_y_string = tk.IntVar(value=0)
        self.max_x_string = tk.IntVar(value=0)
        self.max_y_string = tk.IntVar(value=0)

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
        
        calibration_frame = ttk.Frame(self.bottom_frame)
        calibration_frame.grid(row=1, column=0, columnspan=2)
        
        self.calibration_check = ttk.Checkbutton(calibration_frame, text='Use pixel calibration? (um/px)',
                                                 command=self.calibration_changed)
        self.calibration_check.grid(row=0, column=0)
        
        self.calibration_string = tk.DoubleVar(value=1)
        calibration_entry = ttk.Entry(calibration_frame, textvariable=self.calibration_string, validate='focusout',
                                      validatecommand=self.calibration_changed, width=self.base_entry_width)
        calibration_entry.grid(row=0, column=1)
        calibration_entry.bind('<Return>', self.calibration_changed)
    
    def calibration_changed(self, *args):
        try:
            self.calibration = self.calibration_string.get()
            if self.calibration < 0:
                self.calibration = 0
        except tk.TclError:
            pass
        
        self.calibration_string.set(self.calibration)
        self.frame.pixel_calibration = self.calibration
        self.frame.axis_update_required = True
    
    def calc_threshold_changed(self, *args):
        try:
            self.calc_threshold = self.calc_threshold_string.get()
            if self.calc_threshold < 0:
                self.calc_threshold = 0
            elif self.calc_threshold > 100:
                self.calc_threshold = 100
        except tk.TclError:
            pass
        
        self.calc_threshold_string.set(self.calc_threshold)
        self.frame.calc_threshold = self.calc_threshold
    
    def threshold_changed(self, *args):
        try:
            self.threshold = self.threshold_string.get()
            
            if self.threshold < 0:
                self.threshold = 0
            elif self.threshold > 100:
                self.threshold = 100
        except tk.TclError:
            pass
        
        self.threshold_string.set(self.threshold)
        self.frame.threshold = self.threshold
        
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
        
        self.frame.axis_update_required = True

    def gain_changed(self, *args):
        try:
            self.cam.gain = self.gain_string.get()
        except tk.TclError:
            pass
    
        self.gain_string.set(self.cam.gain)
    
    def exposure_changed(self, *args):
        try:
            self.cam.exposure = self.exposure_string.get()
        except tk.TclError:
            pass
    
        self.exposure_string.set(self.cam.exposure)