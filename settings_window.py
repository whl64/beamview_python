import pyqtgraph as pg
import pyqtgraph.exporters as exp
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt

import numpy as np

from camera_frame import CameraFrame

class SettingsWindow(QtWidgets.QMainWindow):
    def __init__(self, root, app):
        super().__init__()
        self.app = app
        self.root = root
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
        self.setCentralWidget(dummy)
        self.app.focusChanged.connect(self.focus_changed)
        
    def closeEvent(self, event):
        self.app.quit()
        
    def remove_camera(self, cam_to_remove):
        new_cameras = []
        new_frames = []
        for i, (cam, frame) in enumerate(zip(self.active_cameras, self.camera_frames)):
            if cam != cam_to_remove:
                new_cameras.append(cam)
                new_frames.append(frame)
            else:
                removed_index = i
        self.active_cameras = new_cameras
        self.camera_frames = new_frames       
        self.selection_box.removeItem(removed_index)

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
        if len(self.active_cameras) < 1:
            return
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
        
        self.calibration_check.setChecked(self.active_frame.use_calibration)
        self.calibration_entry.setText(str(self.active_frame.calibration))
        
        self.stat_check.setChecked(self.active_frame.calculate_stats)
        self.populate_range_entries()
        
        self.thresh_check.setChecked(self.active_frame.use_threshold)
        self.median_check.setChecked(self.active_frame.use_median_filter)
        
        self.thresh_entry.setText(str(self.active_frame.threshold))
        
        self.exposure_entry.setText(str(self.cam.exposure))
        self.gain_entry.setText(str(self.cam.gain))
        
        self.min_x_entry.setText(str(self.cam.offset_x))
        self.min_y_entry.setText(str(self.cam.offset_y))
        self.max_x_entry.setText(str(self.cam.offset_x + self.cam.width))
        self.max_y_entry.setText(str(self.cam.offset_y + self.cam.height))
        
        self.min_range_entry.setText(str(self.active_frame.vmin))
        self.max_range_entry.setText(str(self.active_frame.vmax))

        self.archive_check.setChecked(self.root.archive_mode)
        
    def populate_range_entries(self):
        min_level, max_level = self.active_frame.cbar.levels()
        self.min_range_entry.setText(str(int(min_level)))
        self.max_range_entry.setText(str(int(max_level)))
        
    def add_camera(self, cam, frame):
        self.active_cameras.append(cam)
        self.camera_frames.append(frame)
        self.selection_box.addItem(cam.name)
        self.selection_box.setCurrentIndex(self.selection_box.count() - 1)
  
    def build_stat_frame(self):
        stat_group_box_row = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(stat_group_box_row)
        stat_frame = QtWidgets.QGroupBox(title='Beam statistics', parent=self)
        stat_layout = QtWidgets.QVBoxLayout()
        stat_frame.setLayout(stat_layout)
        stat_group_box_row.addWidget(stat_frame)
        stat_group_box_row.addStretch(1)
        self.stat_check = QtWidgets.QCheckBox(text='Calculate statistics?', parent=stat_frame)
        self.stat_check.clicked.connect(self.stat_check_clicked)
        stat_calc_layout = QtWidgets.QHBoxLayout()
        stat_layout.addLayout(stat_calc_layout)
        stat_calc_layout.addWidget(self.stat_check)
        stat_calc_layout.addStretch(1)

        auto_range_button = QtWidgets.QPushButton(text='Auto range', parent=stat_frame)
        auto_range_button.clicked.connect(self.auto_range)
        reset_range_button = QtWidgets.QPushButton(text='Reset', parent=stat_frame)
        reset_range_button.clicked.connect(self.reset_range)
        range_layout = QtWidgets.QHBoxLayout()
        range_layout.addWidget(auto_range_button)
        range_layout.addWidget(reset_range_button)
        range_layout.addStretch(1)
        stat_layout.addLayout(range_layout)
        
        manual_range_layout = QtWidgets.QHBoxLayout()
        manual_range_button = QtWidgets.QPushButton(text='Set manual range', parent=stat_frame)
        manual_range_button.clicked.connect(self.manual_range)
        manual_range_layout.addWidget(manual_range_button)
        
        range_validator = QtGui.QIntValidator(self)
        self.min_range_entry = QtWidgets.QLineEdit(parent=stat_frame)
        self.max_range_entry = QtWidgets.QLineEdit(parent=stat_frame)
        self.min_range_entry.setValidator(range_validator)
        self.max_range_entry.setValidator(range_validator)
        self.min_range_entry.setFixedWidth(self.base_entry_width)
        self.max_range_entry.setFixedWidth(self.base_entry_width)
        
        manual_range_layout.addWidget(self.min_range_entry)
        manual_range_layout.addWidget(QtWidgets.QLabel(text='-', parent=stat_frame))
        manual_range_layout.addWidget(self.max_range_entry)
        manual_range_layout.addStretch(1)
        
        stat_layout.addLayout(manual_range_layout)
        
        save_button = QtWidgets.QPushButton(text='Save image', parent=self)
        save_button.clicked.connect(self.save_image)
        save_row_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(save_row_layout)
        save_row_layout.addWidget(save_button)
        save_row_layout.addStretch(1)

        archive_row_layout = QtWidgets.QHBoxLayout() 
        self.archive_check = QtWidgets.QCheckBox(text='Archive mode?', parent=self)
        self.archive_check.clicked.connect(self.archive_check_click)
        self.archive_check.setChecked(self.root.archive_mode)
        
        archive_row_layout.addWidget(self.archive_check)
        archive_row_layout.addStretch(1)
        self.main_layout.addLayout(archive_row_layout)
        
        
    def save_image(self):
        filename = QtWidgets.QFileDialog.getSaveFileName(self, 'Save image...', '', 'PNG (*.png);; JPEG (*.jpg);; npz files (*.npz)',
                                                         'PNG (*.png)')[0]
        
        if filename.endswith('.npz'):
            np.savez(filename, plot_data=self.active_frame.plot_data, pixel_calibration=self.calibration)
        else:
            exporter = exp.ImageExporter(self.active_frame.plot)
            exporter.export(filename)


    def stat_check_clicked(self, checked):
        self.active_frame.calculate_stats = checked
    
        
    def auto_range(self):
        self.active_frame.auto_range()
        self.populate_range_entries()


    def reset_range(self):
        self.active_frame.reset_range()
        self.populate_range_entries()

        
    def manual_range(self):
        min_level = int(self.min_range_entry.text())
        max_level = int(self.max_range_entry.text())
        
        self.active_frame.cbar.setLevels((min_level, max_level))
        self.populate_range_entries()


    def build_proc_frame(self):
        # frame that contains image post-processing controls (threshold, median filter)
        proc_row_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(proc_row_layout)
        proc_frame = QtWidgets.QGroupBox(title='Image processing controls', parent=self)
        proc_row_layout.addWidget(proc_frame)
        proc_row_layout.addStretch(1)

        proc_layout = QtWidgets.QVBoxLayout()
        proc_frame.setLayout(proc_layout)
        self.median_check = QtWidgets.QCheckBox(text='Use median filter?', parent=proc_frame)
        self.median_check.clicked.connect(self.median_check_click)
        median_row_layout = QtWidgets.QHBoxLayout()
        proc_layout.addLayout(median_row_layout)
        median_row_layout.addWidget(self.median_check)
        median_row_layout.addStretch(1)
        
        thresh_row_layout = QtWidgets.QHBoxLayout()
        proc_layout.addLayout(thresh_row_layout)
        self.thresh_check = QtWidgets.QCheckBox(text='Use threshold?', parent=proc_frame)
        thresh_row_layout.addWidget(self.thresh_check)
        self.thresh_check.clicked.connect(self.thresh_check_click)      
        thresh_row_layout.addWidget(QtWidgets.QLabel(text='Threshold value (%): ', parent=proc_frame))      
        self.thresh_entry = QtWidgets.QLineEdit(parent=proc_frame)
        self.thresh_entry.setValidator(QtGui.QDoubleValidator(bottom=0, top=100, parent=self))
        self.thresh_entry.setFixedWidth(self.base_entry_width)
        self.thresh_entry.returnPressed.connect(self.threshold_changed)
        thresh_row_layout.addWidget(self.thresh_entry)
        thresh_row_layout.addStretch(1)
        
        colormap_row_layout = QtWidgets.QHBoxLayout()
        proc_layout.addLayout(colormap_row_layout)
        self.colormap_box = pg.ComboBox(parent=proc_frame)
        self.colormap_box.setEditable(False)
        self.colormap_box.setItems(CameraFrame.colormaps)
        colormap_row_layout.addWidget(QtWidgets.QLabel(text='Colormap: ', parent=proc_frame))      
        colormap_row_layout.addWidget(self.colormap_box, 1)
        colormap_row_layout.addStretch(1)
        self.colormap_box.currentIndexChanged.connect(self.colormap_changed)
        self.colormap_box.setValue(CameraFrame.default_cmap)
                
    def colormap_changed(self, i):
        self.active_frame.cmap = self.colormap_box.value()
        
    def median_check_click(self, checked):
        self.active_frame.use_median_filter = checked

    def archive_check_click(self, checked):
        self.root.archive_mode = checked
        
    def thresh_check_click(self, checked):
        self.active_frame.use_threshold = checked
        
    def threshold_changed(self):
        self.active_frame.threshold = float(self.thresh_entry.text())
    
    def build_camera_frame(self):
        
         # frame that contains exposure time and gain controls
        acq_row_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(acq_row_layout)
        acq_frame = QtWidgets.QGroupBox(title='Acquisition controls', parent=self)
        acq_row_layout.addWidget(acq_frame)
        acq_row_layout.addStretch(1)
        acq_layout = QtWidgets.QGridLayout()
        acq_frame.setLayout(acq_layout)

        acq_layout.addWidget(QtWidgets.QLabel(text='Exposure time (ms): ', parent=self), 0, 0, Qt.AlignmentFlag.AlignRight)
        
        dbl_validator = QtGui.QDoubleValidator(bottom=1e-3, parent=self)
        self.exposure_entry = QtWidgets.QLineEdit(parent=acq_frame)
        self.exposure_entry.setValidator(dbl_validator)
        self.exposure_entry.setFixedWidth(self.base_entry_width)
        self.exposure_entry.returnPressed.connect(self.exposure_changed)
        acq_layout.addWidget(self.exposure_entry, 0, 1)
        
        acq_layout.addWidget(QtWidgets.QLabel(text='Gain: ', parent=self), 1, 0, Qt.AlignmentFlag.AlignRight)
        int_validator = QtGui.QIntValidator(bottom=0, parent=self)
        self.gain_entry = QtWidgets.QLineEdit(parent=acq_frame)
        self.gain_entry.setValidator(int_validator)
        self.gain_entry.setFixedWidth(self.base_entry_width)
        self.gain_entry.returnPressed.connect(self.gain_changed)
        acq_layout.addWidget(self.gain_entry, 1, 1)
        
        acq_layout.setColumnStretch(2, 100)
        
        # frame that contains AOI controls
        size_row_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(size_row_layout)
        size_frame = QtWidgets.QGroupBox(title='AOI controls', parent=self)
        size_row_layout.addWidget(size_frame)
        size_row_layout.addStretch(1)
        size_layout = QtWidgets.QGridLayout()
        size_frame.setLayout(size_layout)
        
        size_layout.addWidget(QtWidgets.QLabel(text='x:', parent=size_frame), 0, 0)
        size_layout.addWidget(QtWidgets.QLabel(text='-', parent=size_frame), 0, 2)
        size_layout.addWidget(QtWidgets.QLabel(text='y:', parent=size_frame), 1, 0)
        size_layout.addWidget(QtWidgets.QLabel(text='-', parent=size_frame), 1, 2)
        
        self.reset_size_button = QtWidgets.QPushButton(text='Reset', parent=self)
        self.reset_size_button.clicked.connect(self.reset_size)
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
        
        self.min_x_entry.returnPressed.connect(self.size_changed)
        self.min_y_entry.returnPressed.connect(self.size_changed)
        self.max_x_entry.returnPressed.connect(self.size_changed)
        self.max_y_entry.returnPressed.connect(self.size_changed)
        
        self.min_x_entry.setFixedWidth(self.base_entry_width)
        self.max_x_entry.setFixedWidth(self.base_entry_width)
        self.min_y_entry.setFixedWidth(self.base_entry_width)
        self.max_y_entry.setFixedWidth(self.base_entry_width)
        
        size_layout.addWidget(self.min_x_entry, 0, 1)
        size_layout.addWidget(self.max_x_entry, 0, 3)
        size_layout.addWidget(self.min_y_entry, 1, 1)
        size_layout.addWidget(self.max_y_entry, 1, 3)
        
        self.not_running_widgets.append(size_frame)
        
        calibration_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(calibration_layout)
        
        self.calibration_check = QtWidgets.QCheckBox(text='Use pixel calibration? (um/px)', parent=self)
        self.calibration_check.clicked.connect(self.calibration_changed)
        calibration_layout.addWidget(self.calibration_check)
        
        calibration_validator = QtGui.QDoubleValidator(bottom=1e-12, parent=self)
        self.calibration_entry = QtWidgets.QLineEdit(parent=self)
        self.calibration_entry.setValidator(calibration_validator)
        self.calibration_entry.setFixedWidth(self.base_entry_width)
        self.calibration_entry.returnPressed.connect(self.calibration_changed)
        calibration_layout.addWidget(self.calibration_entry)
        calibration_layout.addStretch(1)
        
    def focus_changed(self, old, new):
        if old == self.calibration_entry:
            self.calibration_changed()
        if old == self.thresh_entry:
            self.threshold_changed()
        if old == self.min_x_entry or old == self.min_y_entry or old == self.max_x_entry or old == self.max_y_entry:
            self.size_changed()
        if old == self.gain_entry:
            self.gain_changed()
        if old == self.exposure_entry:
            self.exposure_changed()
    
    def calibration_changed(self, *args):
        self.active_frame.change_calibration(self.calibration_check.isChecked(), float(self.calibration_entry.text()))
        
    def reset_size(self):
        self.min_x_entry.setText('0')
        self.min_y_entry.setText('0')
        self.max_x_entry.setText(str(self.cam.max_width))
        self.max_y_entry.setText(str(self.cam.max_height))
        self.size_changed()
        
    def size_changed(self, *args):
        min_x = int(self.min_x_entry.text())
        min_y = int(self.min_y_entry.text())
        max_x = int(self.max_x_entry.text())
        max_y = int(self.max_y_entry.text())
        
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
        
        self.min_x_entry.setText(str(self.cam.offset_x))
        self.min_y_entry.setText(str(self.cam.offset_y))
        self.max_x_entry.setText(str(self.cam.offset_x + self.cam.width))
        self.max_y_entry.setText(str(self.cam.offset_y + self.cam.height))
        
        self.active_frame.change_offset(self.cam.offset_x, self.cam.offset_y)

    def gain_changed(self, *args):
        self.cam.gain = int(self.gain_entry.text())

        self.gain_entry.setText(str(self.cam.gain))
    
    def exposure_changed(self, *args):
        self.cam.exposure = float(self.exposure_entry.text())

        self.exposure_entry.setText(str(self.cam.exposure))
