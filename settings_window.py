import time
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt

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
        self.base_entry_width = 100
        selection_box_layout = QtWidgets.QHBoxLayout()
        self.selection_box = QtWidgets.QComboBox(self)
        self.selection_box.setEditable(False)
        selection_box_layout.addStretch(1)
        selection_box_layout.addWidget(self.selection_box, 1)
        selection_box_layout.addStretch(1)
    
        self.selection_box.currentIndexChanged.connect(self.selection_changed)
        self.main_layout.addLayout(selection_box_layout)
        self.active_cameras = []
        self.camera_frames = []
        
        self.running_widgets = []
        self.not_running_widgets = []
        
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(2)

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
        
        button_layout.addStretch(2)
        
        self.main_layout.addLayout(button_layout)
        
        self.threshold = 0
        self.calc_threshold = 0
        self.calibration = 1
        
        self.build_stat_frame()
        self.build_proc_frame()
        self.build_camera_frame()
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
        
        self.x_validator.setTop(self.cam.max_width)
        self.y_validator.setTop(self.cam.max_height)
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
        self.min_range_entry.setFixedWidth(self.base_entry_width)
        self.max_range_entry.setFixedWidth(self.base_entry_width)
        
        range_layout.addWidget(self.min_range_entry, 1, 1)
        range_layout.addWidget(self.max_range_entry, 1, 3)
        
        range_layout.addWidget(QtWidgets.QLabel(text='-', parent=stat_frame), 1, 2)

        stat_frame.setLayout(stat_layout)
        self.main_layout.addWidget(stat_frame)
        save_button = QtWidgets.QPushButton(text='Save image', parent=self)
        self.main_layout.addWidget(save_button)

        
    def manual_range(self):
        min_level = int(self.min_range_entry.text)
        max_level = int(self.max_range_entry.text)
        
        self.active_frame.setLevels(min_level, max_level)
        
        self.populate_range_entries()


    def build_proc_frame(self):
        # frame that contains image post-processing controls (threshold, median filter)
        proc_frame = QtWidgets.QGroupBox(title='Image processing controls', parent=self)
        self.main_layout.addWidget(proc_frame)
        proc_layout = QtWidgets.QGridLayout()
        proc_frame.setLayout(proc_layout)
        self.median_check = QtWidgets.QCheckBox(text='Use median filter?', parent=proc_frame)
        proc_layout.addWidget(self.median_check, 0, 0)
        self.thresh_check = QtWidgets.QCheckBox(text='Use threshold?', parent=proc_frame)
        proc_layout.addWidget(self.thresh_check, 1, 0)
        proc_layout.addWidget(QtWidgets.QLabel(text='Threshold value (%): ', parent=proc_frame), 1, 1)       
        
        self.thresh_entry = QtWidgets.QLineEdit(parent=proc_frame)
        self.thresh_entry.setValidator(QtGui.QIntValidator(bottom=0, top=100, parent=self))
        self.thresh_entry.setFixedWidth(self.base_entry_width)
        proc_layout.addWidget(self.thresh_entry, 1, 2)
        
    
    def build_camera_frame(self):
        bottom_layout = QtWidgets.QGridLayout()
        self.main_layout.addLayout(bottom_layout)
        
         # frame that contains exposure time and gain controls
        acq_frame = QtWidgets.QGroupBox(title='Acquisition controls', parent=self)
        bottom_layout.addWidget(acq_frame, 0, 0)
        acq_layout = QtWidgets.QGridLayout()
        acq_frame.setLayout(acq_layout)

        acq_layout.addWidget(QtWidgets.QLabel(text='Exposure time (ms): ', parent=self), 0, 0, Qt.AlignmentFlag.AlignRight)
        
        validator = QtGui.QIntValidator(bottom=0, parent=self)
        self.exposure_entry = QtWidgets.QLineEdit(parent=acq_frame)
        self.exposure_entry.setValidator(validator)
        self.exposure_entry.setFixedWidth(self.base_entry_width)
        acq_layout.addWidget(self.exposure_entry, 0, 1)
        
        acq_layout.addWidget(QtWidgets.QLabel(text='Gain: ', parent=self), 1, 0, Qt.AlignmentFlag.AlignRight)
        
        self.gain_entry = QtWidgets.QLineEdit(parent=acq_frame)
        self.gain_entry.setValidator(validator)
        self.gain_entry.setFixedWidth(self.base_entry_width)
        acq_layout.addWidget(self.gain_entry, 1, 1)
        
        acq_layout.setColumnStretch(2, 100)
        
        # frame that contains AOI controls
        size_frame = QtWidgets.QGroupBox(title='AOI controls', parent=self)
        bottom_layout.addWidget(size_frame, 1, 0)
        size_layout = QtWidgets.QGridLayout()
        size_frame.setLayout(size_layout)
        
        size_layout.addWidget(QtWidgets.QLabel(text='x:', parent=size_frame), 0, 0)
        size_layout.addWidget(QtWidgets.QLabel(text='-', parent=size_frame), 0, 2)
        size_layout.addWidget(QtWidgets.QLabel(text='y:', parent=size_frame), 1, 0)
        size_layout.addWidget(QtWidgets.QLabel(text='-', parent=size_frame), 1, 2)
        
        self.reset_size_button = QtWidgets.QPushButton(text='Reset', parent=self)
        size_layout.addWidget(self.reset_size_button, 0, 4, 2, 2)

        self.x_validator = QtGui.QIntValidator(bottom=0, top=0, parent=self)
        self.y_validator = QtGui.QIntValidator(bottom=0, top=0, parent=self)
        
        self.min_x_entry = QtWidgets.QLineEdit(parent=size_frame)
        self.min_x_entry.setValidator(self.x_validator)
        self.max_x_entry = QtWidgets.QLineEdit(parent=size_frame)
        self.max_x_entry.setValidator(self.x_validator)
        self.min_y_entry = QtWidgets.QLineEdit(parent=size_frame)
        self.min_y_entry.setValidator(self.y_validator)
        self.max_y_entry = QtWidgets.QLineEdit(parent=size_frame)
        self.max_y_entry.setValidator(self.y_validator)
        
        self.min_x_entry.setFixedWidth(self.base_entry_width)
        self.max_x_entry.setFixedWidth(self.base_entry_width)
        self.min_y_entry.setFixedWidth(self.base_entry_width)
        self.max_y_entry.setFixedWidth(self.base_entry_width)
        
        size_layout.addWidget(self.min_x_entry, 0, 1)
        size_layout.addWidget(self.max_x_entry, 0, 3)
        size_layout.addWidget(self.min_y_entry, 1, 1)
        size_layout.addWidget(self.max_y_entry, 1, 3)
        
        self.not_running_widgets.append(size_frame)
        
        calibration_layout = QtWidgets.QGridLayout()
        bottom_layout.addLayout(calibration_layout, 2, 0, 1, 2)
        
        self.calibration_check = QtWidgets.QCheckBox(text='Use pixel calibration? (um/px)', parent=self)
        calibration_layout.addWidget(self.calibration_check, 0, 0)
        
        calibration_validator = QtGui.QDoubleValidator(bottom=1e-12, parent=self)
        self.calibration_entry = QtWidgets.QLineEdit(parent=self)
        self.calibration_entry.setValidator(calibration_validator)
        self.calibration_entry.setFixedWidth(self.base_entry_width)
        calibration_layout.addWidget(self.calibration_entry, 0, 1)
    
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
