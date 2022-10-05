import time
from PyQt5 import QtWidgets, QtGui

import numpy as np


class SettingsWindow(QtWidgets.QMainWindow):
    def __init__(self, root, app):
        super().__init__()
        self.app = app
        self.setMinimumSize(200, 200)
        self.setWindowTitle('Camera settings')
        dummy = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout()
        dummy.setLayout(self.main_layout)
        self.base_entry_width = 6
        self.selection_box = QtWidgets.QComboBox(self)
        self.selection_box.setEditable(False)
    
        self.selection_box.currentIndexChanged.connect(self.selection_changed)
        self.main_layout.addWidget(self.selection_box)
        self.active_cameras = []
        self.camera_frames = []
        
        self.running_widgets = []
        self.not_running_widgets = []
        
        button_layout = QtWidgets.QHBoxLayout()
        # button to start camera
        start_button = QtWidgets.QPushButton(text='Start', parent=self)
        button_layout.addWidget(start_button)
        self.not_running_widgets.append(start_button)
        start_button.clicked.connect(self.start_camera)
        
        # button to stop camera
        stop_button = QtWidgets.QPushButton(text='Stop', parent=self)
        button_layout.addWidget(stop_button)
        self.running_widgets.append(stop_button)
        stop_button.clicked.connect(self.stop_camera)
        
        self.main_layout.addLayout(button_layout)
        
        self.threshold = 0
        self.calc_threshold = 0
        self.calibration = 1
        
        self.build_stat_frame()
        # self.build_proc_frame()
        # self.build_camera_frame()
        self.root = root
        self.setCentralWidget(dummy)
        
    def closeEvent(self, event):
        self.app.quit()
        
    def remove_camera(self, cam_to_remove):
        new_cameras = []
        new_frames = []
        for cam, frame in zip(self.active_cameras, self.camera_frames):
            if cam != cam_to_remove:
                new_cameras.append(cam)
                new_frames.append(frame)
        self.active_cameras = new_cameras
        self.camera_frames = new_frames       
        current_index = self.selection_box.current()
        if current_index == len(self.active_cameras):
            current_index -= 1
        self.selection_box['values'] = tuple([cam.name for cam in self.active_cameras])
        if current_index > -1:
            self.selection_box.current(current_index)

    def start_camera(self):
        self.active_frame.start_camera()
        for w in self.not_running_widgets:
            w.setEnabled(False)
            
        for w in self.running_widgets:
            w.setEnabled(True)
        
    def stop_camera(self):
        self.active_frame.stop_camera()
        for w in self.running_widgets:
            w.setEnabled(False)
            
        for w in self.not_running_widgets:
            w.setEnabled(True)
    
    def selection_changed(self, i):
        self.cam = self.active_cameras[i]
        self.active_frame = self.camera_frames[i]
        if self.cam.is_grabbing():
            for w in self.not_running_widgets:
                w.setEnabled(False)
            for w in self.running_widgets:
                w.setEnabled(True)
        else:
            for w in self.running_widgets:
                w.setEnabled(False)
            for w in self.not_running_widgets:
                w.setEnabled(True)
                
        # self.thresh_check.configure(variable=self.active_frame.use_threshold)
        # self.median_check.configure(variable=self.active_frame.use_median_filter)
        # self.stat_check.configure(variable=self.active_frame.calculate_stats)
        # self.calibration_check.configure(variable=self.active_frame.use_calibration)
        # self.threshold = self.active_frame.threshold
        # self.calc_threshold = self.active_frame.calc_threshold
        # self.threshold_string.set(self.threshold)
        # self.calc_threshold_string.set(self.calc_threshold)
        
        # self.exposure_string.set(self.cam.exposure)
        # self.gain_string.set(self.cam.gain)
        
        # self.min_x_string.set(self.cam.offset_x)
        # self.min_y_string.set(self.cam.offset_y)
        # self.max_x_string.set(self.cam.offset_x + self.cam.width)
        # self.max_y_string.set(self.cam.offset_y + self.cam.height)
        
        # self.manual_min_string.set(self.active_frame.vmin)
        # self.manual_max_string.set(self.active_frame.vmax)
        
    def refresh_levels(self):
        min_level, max_level = self.active_frame.cbar.levels()
        self.min_range_entry.setText(int(min_level))
        self.max_range_entry.setText(int(max_level))
        
    def reconnect(self, signal, slot):
        try:
            signal.disconnect()
        except:
            pass
        signal.connect(slot)
        
    def add_camera(self, cam, frame):
        self.active_cameras.append(cam)
        self.camera_frames.append(frame)
        self.selection_box.addItem(cam.name)
        self.selection_box.setCurrentIndex(self.selection_box.count() - 1)
        
    def auto_range(self):
        self.active_frame.auto_range()
        self.populate_range_entries()

    def reset_range(self):
        self.active_frame.reset_range()
        self.populate_range_entries()
  
    def build_stat_frame(self):
        stat_frame = QtWidgets.QGroupBox(title='Beam statistics', parent=self)
        stat_layout = QtWidgets.QGridLayout()
        self.stat_check = QtWidgets.QCheckBox(text='Calculate statistics?', parent=stat_frame)
        stat_layout.addWidget(self.stat_check, 0, 0, 1, 2)        

        auto_range_button = QtWidgets.QPushButton(text='Auto range', parent=stat_frame)
        reset_range_button = QtWidgets.QPushButton(text='Reset', parent=stat_frame)
        stat_layout.addWidget(auto_range_button, 1, 0)
        stat_layout.addWidget(reset_range_button, 1, 1)
        
        range_layout = QtWidgets.QGridLayout()
        stat_layout.addLayout(range_layout, 2, 0, 1, 2)
        manual_range_button = QtWidgets.QPushButton(text='Set manual range', parent=stat_frame)
        range_layout.addWidget(manual_range_button, 1, 0)
        
        range_validator = QtGui.QIntValidator(self)
        self.min_range_entry = QtWidgets.QLineEdit(parent=stat_frame)
        self.max_range_entry = QtWidgets.QLineEdit(parent=stat_frame)
        self.min_range_entry.setValidator(range_validator)
        self.max_range_entry.setValidator(range_validator)
        
        range_layout.addWidget(self.min_range_entry, 1, 1)
        range_layout.addWidget(self.max_range_entry, 1, 3)
        
        range_layout.addWidget(QtWidgets.QLabel(text='-', parent=stat_frame), 1, 2)
        
        # ttk.Label(stat_frame, text='Threshold for calculations (%): ').grid(row=1, column=0)
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
        stat_frame.setLayout(stat_layout)
        self.main_layout.addWidget(stat_frame)
        # save_button = QtWidgets.QPushButton(text='Save image', parent=self)
        # self.main_layout.addWidget(save_button)

        
    def manual_range(self):
        min_level = int(self.min_range_entry.text)
        max_level = int(self.max_range_entry.text)
        
        self.active_frame.setLevels(min_level, max_level)
        
        self.populate_range_entries()


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
        
        proc_frame.grid(row=4, column=0)
    
    def build_camera_frame(self):
        self.bottom_frame = ttk.Frame(self)
        self.bottom_frame.grid(row=5, column=0)
        
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
        self.active_frame.pixel_calibration = self.calibration
        self.active_frame.axis_update_required = True
    
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
        self.active_frame.calc_threshold = self.calc_threshold
    
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
        self.active_frame.threshold = self.threshold
        
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
        
        self.active_frame.axis_update_required = True

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
