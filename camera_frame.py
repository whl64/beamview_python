from image_grabber import ImageGrabber
import time
import threading
import argparse
import faulthandler
import os

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

import numpy as np
import scipy.ndimage as ndi
from basler_camera_wrapper import Basler_Camera, TriggerMode
from pypylon import pylon

class CameraFrame(QtWidgets.QWidget):    
    def __init__(self, master, cam, root, app):
        super().__init__(master)
        self.app = app
        self.root = root
        self.pixel_calibration = 1
        self.cam = cam
        self.default_fig_width = 5
        # set up plotting canvas
        
        main_layout = QtWidgets.QVBoxLayout()
        status_layout = QtWidgets.QHBoxLayout()
        info_layout = QtWidgets.QVBoxLayout()
        info_layout_0 = QtWidgets.QHBoxLayout()
        info_layout_1 = QtWidgets.QHBoxLayout()
        
        main_layout.addLayout(status_layout)
        status_layout.addLayout(info_layout)
        info_layout.addLayout(info_layout_0)
        info_layout.addLayout(info_layout_1)
                
        info_layout_0.addWidget(QtWidgets.QLabel(text=self.cam.name, parent=self))
        
        # status_label = QtWidgets.QLabel('Stopped.')
        # ttk.Label(info_frame_0, textvariable=self.status_string).grid(row=0, column=1, padx=(5, 5))
        
        self.frame_time_label = QtWidgets.QLabel(text='0.00 s', parent=self)
        info_layout_0.addWidget(self.frame_time_label)        
        # self.max_data_percent_string = tk.StringVar(value='Max data: 0.0%')
        # self.max_data_label = ttk.Label(info_frame_0, textvariable=self.max_data_percent_string)
        # self.max_data_label.grid(row=0, column=3, padx=(5, 5))
        
        # self.centroid_string = tk.StringVar(value='Centroid (px): (N/A, N/A)')
        # ttk.Label(info_frame_1, textvariable=self.centroid_string).grid(row=0, column=0, padx=(0, 5))
        
        # self.sigma_string = tk.StringVar(value='Sigmas (px): (N/A, N/A)')
        # ttk.Label(info_frame_1, textvariable=self.sigma_string).grid(row=0, column=1, padx=(5, 0))
        
        # close_button = ttk.Button(status_frame, text='Close camera', command=self.close)
        # close_button.grid(row=0, column=1, sticky='w')
                
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
        
        self.fig = pg.GraphicsLayoutWidget()
        self.viewbox = self.fig.addViewBox()
        self.img = pg.ImageItem()
        self.viewbox.addItem(self.img)
        main_layout.addWidget(self.fig)
        self.setLayout(main_layout)

        # self.plot_data = np.array([])
        # self.image = self.ax.imshow(np.zeros((self.cam.height, self.cam.width)), vmin=self.vmin, vmax=self.vmax,
        #                             extent=(self.cam.offset_x, self.cam.offset_x + self.cam.width,
        #                                     self.cam.offset_y + self.cam.height, self.cam.offset_y))
        # divider = make_axes_locatable(self.ax)
        # cax = divider.append_axes('right', size='5%', pad=0.05)
        # self.cbar = self.fig.colorbar(self.image, cax=cax)

        # self.canvas = FigureCanvasTkAgg(self.fig, self)
        # self.canvas.draw()
        # self.canvas.get_tk_widget().grid(row=1, column=0, sticky='nesw')
        
        # self.axis_update_required = False
        
        # # set resizing priorities (higher weight gets more room)
        # self.grid_rowconfigure(0, weight=3, minsize=40)
        # self.grid_rowconfigure(1, weight=1)
        
        self.prev_frame_timestamp = time.time()
        self.use_median_filter = False
        self.calculate_stats = False
        self.use_threshold = False
        self.use_calibration = False
        # self.max_data_percent = 0
        # self.frame_time = 0
        # self.centroid_x = 0
        # self.centroid_y = 0
        # self.sigma_x = 0
        # self.sigma_y = 0

        # self.calibration = 1
        # self.frame_available = False
       
        self.lock = threading.Lock()
        
        self.start_camera()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(50)
    
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
        # self.status_string.set('Running.')
        try:
            self.cam.request_frame()
        except:
            print('trigger timed out')
        # self.root.start_camera(self.cam)
        
    def stop_camera(self):
        self.cam.stop_grabbing()
        self.status_string.set('Stopped.')
        self.root.stop_camera(self.cam)
        
    def auto_range(self):
        self.vmin = np.min(self.plot_data)
        self.vmax = np.max(self.plot_data)
        self.axis_update_required = True
        
    def reset_range(self):
        self.vmin = 0
        self.vmax = 2**self.bit_depth - 1
        self.axis_update_required = True

    def update_frames(self):
        if self.cam.is_grabbing():
            if self.cam.trigger_mode == TriggerMode.FREERUN:
                self.plot_data = self.cam.return_frame()
                self.draw_frame()
            else:
                self.lock.acquire()
                if self.frame_available:
                    self.frame_available = False
                    self.draw_frame()
                else:
                    self.lock.release()
            
    def draw_frame(self):
        plot_data = self.plot_data
        # self.lock.release()
        try:
            frame_time = time.time() - self.prev_frame_timestamp
            self.prev_frame_timestamp = time.time()
            if frame_time > 50:
                frame_time = 50
            self.frame_time_label.setText(f'Frame time: {frame_time:.3f} s')

            # if self.use_median_filter.get():
            #     plot_data = ndi.median_filter(plot_data, size=2)
                
            max_data_percent = 100 * np.max(plot_data) / (2**self.bit_depth - 1)
            # if self.use_threshold.get():
            #     max_data = np.max(plot_data)
            #     plot_data[plot_data < max_data*self.threshold/100] = 0
                
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
                
                # model = Gaussian2dModel() + ConstantModel()
                
                # model.set_param_hint('amplitude', min=0, value=np.max(calc_plot_data))
                # model.set_param_hint('centerx', value=centroid_x)
                # model.set_param_hint('sigmax', value=sigma_x)
                # model.set_param_hint('centery', value=centroid_y)
                # model.set_param_hint('sigmay', value=sigma_y)
                # model.set_param_hint('c', value=np.min(calc_plot_data))
                
                # params = model.make_params()

                # result = model.fit(calc_frame.flatten(), params=params, x=xx.flatten(), y=yy.flatten())              

                if self.use_calibration.get():
                    x_values *= self.pixel_calibration/1000
                    y_values *= self.pixel_calibration/1000
                    unit = '(mm)'
                else:
                    unit = '(px)'
            self.img.setImage(self.plot_data[::-1,])
            self.app.processEvents()
        except RuntimeError as e:
            print(e)
            
            
if __name__ == '__main__':
    pg.setConfigOption('imageAxisOrder', 'row-major')
    parser = argparse.ArgumentParser(description='Multicam Beamview.')
    parser.add_argument('--debug', help='create emulated cameras for debugging', action='store_true')
    args = parser.parse_args()
    if args.debug:
        faulthandler.enable()
        number_of_emulated_cameras = 20
        os.environ['PYLON_CAMEMU'] = str(number_of_emulated_cameras)
    tlf = pylon.TlFactory.GetInstance()
    devices = tlf.EnumerateDevices()

    real_camera = Basler_Camera(devices[0].GetSerialNumber(), TriggerMode.FREERUN, 8192)
    
    app = QtWidgets.QApplication([])
    frame = CameraFrame(None, real_camera, None, app)
    frame.show()
    app.exec()