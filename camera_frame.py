from image_grabber import ImageGrabber
import time
import threading
import argparse
import faulthandler
import os
import cmasher as cmr
import datetime
import pyqtgraph.exporters as exp

from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton)
from PyQt5.QtGui import QTransform
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg

import numpy as np
import scipy.ndimage as ndi
from basler_camera_wrapper import Basler_Camera, TriggerMode
from pypylon import pylon
from PIL import Image

class CameraFrame(QFrame):
    # format: "friendly name" displayed to users, "real name" used by getFromMatplotlib     
    colormaps = {'ember': 'cmr.ember',
                 'freeze': 'cmr.freeze',
                 'grayscale': 'cmr.neutral',
                 'jungle': 'cmr.jungle',
                 'seaweed': 'cmr.seaweed',
                 'viridis': 'viridis',
                 'inferno': 'inferno'}
    default_cmap = 'cmr.ember'
    
    def __init__(self, master, cam, app):
        super().__init__(master)
        self.setObjectName('frame')
        self.master = master
        self.app = app
        self.pixel_calibration = 1
        self.cam = cam
        self.default_fig_width = 5
        # set up plotting canvas
        
        main_layout = QVBoxLayout()
        status_layout = QHBoxLayout()
        info_layout = QVBoxLayout()
        info_layout_0 = QHBoxLayout()
        info_layout_1 = QHBoxLayout()
        info_layout_2 = QHBoxLayout()
        info_layout_3 = QHBoxLayout()
        
        main_layout.addLayout(status_layout)
        status_layout.addLayout(info_layout)
        info_layout.addLayout(info_layout_0)
        info_layout.addLayout(info_layout_1)
        info_layout.addLayout(info_layout_2)
        info_layout.addLayout(info_layout_3)
                
        info_layout_0.addWidget(QLabel(text=self.cam.name, parent=self))
        
        self.status_label = QLabel('Stopped.', parent=self)
        info_layout_0.addWidget(self.status_label)
        info_layout_0.addWidget(QLabel(f'Binning: {self.cam.binning}'))
        info_layout_0.addStretch(1)
        
        self.frame_time_label = QLabel(text='Frame time: 0.000 s', parent=self)
        info_layout_1.addWidget(self.frame_time_label)        

        self.max_data_label = QLabel(text='Saturated pixels: 0.0%  ', parent=self)
        info_layout_1.addWidget(self.max_data_label)
        info_layout_1.addStretch(1)
        
        self.centroid_label = QLabel(text='Centroids (px): (N/A, N/A)', parent=self)
        info_layout_2.addWidget(self.centroid_label)
        info_layout_2.addStretch(1)
        
        self.sigma_label = QLabel(text='Sigmas (px): (N/A, N/A)', parent=self)
        info_layout_3.addWidget(self.sigma_label)
        info_layout_3.addStretch(1)
        
        close_button = QPushButton(text='Close camera', parent=self)
        close_layout = QVBoxLayout()
        close_layout.addStretch(1)
        close_layout.addWidget(close_button)
        
        status_layout.addStretch(1)
        status_layout.addLayout(close_layout)
        
        close_button.clicked.connect(self.close)
                
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
        
        self.x_offset = 0
        self.y_offset = 0
        
        self.fig = pg.GraphicsLayoutWidget()
        self.fig.setCursor(Qt.CrossCursor)
        self.fig.ci.setContentsMargins(0, 0, 0, 0)
        self.plot = self.fig.addPlot()
        self.plot.setAspectLocked(True)
        self.plot.setTitle(' ')
        
        self.img = pg.ImageItem()
        self._cmap = CameraFrame.default_cmap
        self.img.setColorMap(pg.colormap.getFromMatplotlib(self.cmap))
        self.plot.addItem(self.img)
        
        # monkey patch in custom mouse events
        self.img.hoverEvent = self.imageHoverEvent
        self.img.mouseClickEvent = self.imageClickEvent
        
        self.cbar = pg.ColorBarItem(values=(self.vmin, self.vmax))
        self.cbar.setImageItem(self.img)
        self.fig.addItem(self.cbar)
        
        # font = .QFont()
        # font.setPixelSize(16)
        # self.plot.getAxis('bottom').setTickFont(font)
        # self.plot.getAxis('left').setTickFont(font)
        self.show_axes = False
        self.plot.showAxis('bottom', self.show_axes)
        self.plot.showAxis('left', self.show_axes)
        self.tr = QTransform()
        
        main_layout.addWidget(self.fig)
        self.setLayout(main_layout)

        self.plot_data = np.array([])
        self.prev_frame_timestamp = time.time()
        self.use_median_filter = False
        self.calculate_stats = False
        self.use_threshold = False
        self.use_calibration = False
        self.frame_available = False
        self.centroid_label.setEnabled(True)
        self.sigma_label.setEnabled(True)

        self.calibration = 1
       
        self.lock = threading.Lock()
        
        self.stop_camera()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(100)
        self.setMinimumHeight(400)
        self.crosshairs = []
        self.image_grabber = ImageGrabber(self)
        self.cam.register_event_handler(self.image_grabber)

        self.last_archive_time = 0
        self.shot_number = 0
        
    def toggle_axes(self):
        self.show_axes = not self.show_axes
        self.plot.showAxis('bottom', self.show_axes)
        self.plot.showAxis('left', self.show_axes)
        
    @property
    def cmap(self):
        return self._cmap

    @cmap.setter
    def cmap(self, value):
        self.cbar.setColorMap(pg.colormap.getFromMatplotlib(value))
        self._cmap = value
        
    def change_calibration(self, use_calibration, calibration):
        self.use_calibration = use_calibration
        self.calibration = calibration
        self.update_transform()
        
    def change_offset(self, x_offset, y_offset):
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.update_transform()

    def update_transform(self):
        self.tr.reset()
        self.tr.translate(self.x_offset, self.y_offset)
        if self.use_calibration:
            self.tr.scale(self.calibration, self.calibration)
        self.img.setTransform(self.tr)


    def close(self):
        self.cleanup()
        self.master.remove_camera(self)
            
    def cleanup(self):
        self.cam.stop_grabbing()
        self.cam.release_camera()
    
    def start_camera(self):
        if not self.cam.is_grabbing():
            self.cam.start_grabbing()
            self.status_label.setText('Running...')
            try:
                self.cam.request_frame()
            except:
                print('trigger timed out')
            self.master.start_camera(self.cam)
        
    def stop_camera(self):
        if self.cam.is_grabbing():
            self.cam.stop_grabbing()
            self.status_label.setText('Stopped.')
            self.master.stop_camera(self.cam)
        
    def auto_range(self):
        self.cbar.setLevels((np.min(self.plot_data), np.max(self.plot_data)))
        
    def reset_range(self):
        self.cbar.setLevels((0, 2**self.bit_depth - 1))

    def update_frames(self):
        if self.cam.is_grabbing():
#            if self.cam.trigger_mode == TriggerMode.FREERUN or self.cam.trigger_mode == TriggerMode.HARDWARE:
#                self.plot_data = self.cam.return_frame()
#                self.draw_frame()
#            else:
            self.lock.acquire()
            if self.frame_available:
                self.frame_available = False
                self.draw_frame()
            else:
                self.lock.release()
        
    def draw_frame(self):
        plot_data = self.plot_data
        raw_data = np.copy(self.plot_data)
        self.lock.release()
        try:
            frame_time = time.time() - self.prev_frame_timestamp
            self.prev_frame_timestamp = time.time()
            if frame_time > 50:
                frame_time = 50
            self.frame_time_label.setText(f'Frame time: {frame_time:.3f} s')

            if self.use_median_filter:
                plot_data = ndi.median_filter(plot_data, size=2)
            
            saturation = 2**self.bit_depth - 1
            unique, counts = np.unique(plot_data, return_counts=True)
            sat_pixels = dict(zip(unique, counts))
            # max_data_percent = 100 * np.max(plot_data) / (2**self.bit_depth - 1)
            try:
                sat_pixels = sat_pixels[saturation]
            except KeyError:
                sat_pixels = 0
            max_data_string = f'{sat_pixels:.4g}'
            total_counts = np.sum(plot_data)
            self.max_data_label.setText(f'Saturated pixels: {max_data_string}, total counts: {total_counts:.4g}')
            #if sat_pixel_percent > 97:
#                self.max_data_label.setStyleSheet('background-color: red')
#            else:
#                self.max_data_label.setStyleSheet('background-color: none')
            if self.use_threshold:
                max_data = np.max(plot_data)
                plot_data[plot_data < max_data*self.threshold/100] = 0


            if self.calculate_stats:
                calc_plot_data = np.copy(plot_data)
                max_data = np.max(calc_plot_data)
                # calc_frame[calc_frame < max_data*self.calc_threshold/100] = 0
                calc_plot_data = calc_plot_data.astype(float)
                calc_plot_data /= np.sum(calc_plot_data)
                
                x_values = np.arange(self.cam.offset_x, self.cam.offset_x + self.cam.width).astype(float)
                y_values = np.arange(self.cam.offset_y, self.cam.offset_y + self.cam.height).astype(float)
                
                xx, yy = np.meshgrid(x_values, y_values, indexing='xy')
                
                centroid_x = np.sum(xx * calc_plot_data)
                centroid_y = np.sum(yy * calc_plot_data)
                
                sigma_x = np.sqrt(np.sum((xx - centroid_x)**2 * calc_plot_data))
                sigma_y = np.sqrt(np.sum((yy - centroid_y)**2 * calc_plot_data))
                
                if self.use_calibration:
                    x_values *= self.pixel_calibration/1000
                    y_values *= self.pixel_calibration/1000
                    unit = '(mm)'
                else:
                    unit = '(px)'
                    
                self.centroid_label.setText(f'Centroids {unit}: {centroid_x:.1f}, {centroid_y:.1f}')
                self.sigma_label.setText(f'Sigmas {unit}: {sigma_x:.1f}, {sigma_y:.1f}')
                self.centroid_label.setEnabled(True)
                self.sigma_label.setEnabled(True)
            else:
                self.centroid_label.setEnabled(False)
                self.sigma_label.setEnabled(False)

            self.img.setImage(plot_data[::-1,], autoLevels=False)
            if self.master.archive_mode and time.time() - self.last_archive_time > self.master.archive_time:
                self.last_archive_time = time.time()
                timestamp = datetime.datetime.now()
                try:
                    shot_number_string = f'_{self.shot_number}' if self.master.archive_shot_number else ''
                    prefix_string = self.master.archive_prefix + '_' if self.master.archive_prefix != '' else ''
                    suffix_string = '_' + self.master.archive_suffix if self.master.archive_suffix != '' else ''
                    filename = os.path.join(self.master.archive_dir, f'{prefix_string}{timestamp.year}{timestamp.month:02d}{timestamp.day:02d}_{timestamp.hour:02d}{timestamp.minute:02d}{timestamp.second:02d}'+f'_{self.cam.name}{suffix_string}{shot_number_string}')
                    print(filename)
# np.savez(filename + '.npz', plot_data=self.camera_frames[sn].plot_data)
                    im = Image.fromarray(raw_data)
                    im.save(filename + '.tiff', 'TIFF')
                    # exporter = exp.ImageExporter(self.plot)
                    # exporter.export(filename + '.tiff')
                    # res = cam.return_frame()
                    # frame.image_grabber.OnImageGrabbed(cam, res)
                    self.shot_number += 1
                except Exception as e:
                    print(e)
            self.app.processEvents()
        except RuntimeError as e:
            print(e)
    
    def activate(self):
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setStyleSheet('#frame {border: 1px solid red; }')
        
    def deactivate(self):
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet('')

    def imageHoverEvent(self, event):
        """Show the position, pixel, and value under the mouse cursor.
        """
        if event.isExit():
            self.plot.setTitle(' ')
            return
        pos = event.pos()
        i, j = pos.x(), pos.y()
        i = int(np.clip(i, 0, self.plot_data.shape[0] - 1))
        j = int(np.clip(j, 0, self.plot_data.shape[1] - 1))
        val = self.plot_data[i, j]
        ppos = self.img.mapToParent(pos)
        x, y = ppos.x(), ppos.y()
        self.plot.setTitle("pos: (%0.1f, %0.1f)<br>pixel: (%d, %d)  value: %.3g" % (x, y, i, j, val))
        
    def imageClickEvent(self, event):
        if self.master.adding_crosshair and event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            i, j = pos.x(), pos.y()
            i = int(np.clip(i, 0, self.plot_data.shape[0] - 1))
            j = int(np.clip(j, 0, self.plot_data.shape[1] - 1))
            ppos = self.img.mapToParent(pos)
            x, y = ppos.x(), ppos.y()
            crosshair = Crosshair((x, y), movable=False, frame=self, pen='white')
            self.crosshairs.append(crosshair)          
            self.plot.addItem(crosshair)
            
    def remove_crosshair(self, crosshair):
        self.crosshairs.remove(crosshair)
        self.plot.removeItem(crosshair)
        
    def move_crosshairs(self, move):
        for crosshair in self.crosshairs:
            crosshair.movable = move
            
    def highlight_crosshairs(self, highlight):
        for crosshair in self.crosshairs:
            crosshair.highlight = highlight

class Crosshair(pg.TargetItem):
    def __init__(self, *args, **kwargs):
        self.frame = kwargs.pop('frame')
        self.highlight = False
        super().__init__(*args, **kwargs)
        
    def mouseClickEvent(self, ev):
        ev.accept()
        if self.frame.master.deleting_crosshair and ev.button() == Qt.MouseButton.LeftButton:
            self.frame.remove_crosshair(self)
        else:
            super().mouseClickEvent(ev)

    def hoverEvent(self, ev):
        if (self.movable or self.highlight) and (not ev.isExit()) and ev.acceptDrags(Qt.MouseButton.LeftButton):
            self.setMouseHover(True)
        else:
            self.setMouseHover(False)
