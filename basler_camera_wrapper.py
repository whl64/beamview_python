from enum import Enum, auto

import pypylon._genicam as _genicam
import pypylon.pylon as pylon
import threading

import camera_wrapper as cw


class TriggerMode(Enum):
    FREERUN = auto()
    SOFTWARE = auto()
    HARDWARE = auto()

class Basler_Camera(cw.Camera):
    def __init__(self, serial_number, trigger_mode, packet_size=8192, binning=1):
        super().__init__(serial_number)
        tlf = pylon.TlFactory.GetInstance()
        di = pylon.DeviceInfo()
        di.SetSerialNumber(serial_number)
        device = tlf.EnumerateDevices([di, ])[0]
        self.name = device.GetUserDefinedName()
        self.model = device.GetModelName()
#        self.address = device.GetAddress()
        self.cam = pylon.InstantCamera(tlf.CreateDevice(device))
        self.cam.Open()
        
        if trigger_mode == TriggerMode.SOFTWARE:
            self.cam.RegisterConfiguration(pylon.SoftwareTriggerConfiguration(), pylon.RegistrationMode_ReplaceAll,
                                           pylon.Cleanup_Delete)
        elif trigger_mode == TriggerMode.FREERUN:
            pass
        elif trigger_mode == TriggerMode.HARDWARE:
            self.cam.TriggerMode = 'On'
        else:
            raise TypeError('trigger must be of type TriggerMode')
        
        self.trigger_mode = trigger_mode

        self.lock = threading.Lock()
        self.lock.acquire()
        self.waiting_for_trigger = False
        self.lock.release()
            
        
        if self.model != 'Emulation':
            self.cam.GevSCPSPacketSize.SetValue( packet_size )  #  9708 abs max new cam.
            self.cam.GevSCPD.SetValue( 12000 ) #  interpacket delay
        
        if self.model == 'scA1400-17gm':
            self._pixel_format = 'Mono16'		#  Yes, this is 12-bit
        elif self.model == 'acA1920-50gm':
            self._pixel_format = 'Mono12'		#  12-bit
        else:
            self._pixel_format = 'Mono12'
        try:
            self.cam.PixelFormat.SetValue(self._pixel_format)
        except _genicam.InvalidArgumentException as E:
            self._pixel_format = 'Mono8'
            self.cam.PixelFormat.SetValue(self._pixel_format)
        try:
            self.cam.BinningHorizontal = binning
            self.cam.BinningVertical = binning
            self.cam.BinningHorizontalMode = 'Average'
            self.cam.BinningVerticalMode = 'Average'
            self._binning = binning
        except _genicam.LogicalErrorException:
            self._binning = 1 # camera doesn't support binning, so we report a binning factor of 1
    
    @property
    def frame_transmission_delay(self):
        return self.cam.GevSCFTD.GetValue()

    @frame_transmission_delay.setter
    def frame_transmission_delay(self, value):
        return self.cam.GevSCFTD.SetValue(value)

    @property
    def interpacket_delay(self):
        return self.cam.GevSCPD.GetValue()

    @interpacket_delay.setter
    def interpacket_delay(self, value):
        self.cam.GevSCPD.SetValue(value)

    @property
    def pixel_format(self):
        return self._pixel_format
    
    @property
    def gain(self):
        return self.cam.GainRaw.GetValue()
    
    @gain.setter
    def gain(self, value):
        try: 
            self.cam.GainRaw.SetValue(value)    
        except _genicam.OutOfRangeException:
            pass
    @property
    def exposure(self):
        """Exposure time in ms

        Returns:
            float: exposure time in ms
        """
        return self.cam.ExposureTimeRaw.GetValue()/1e3
    
    @exposure.setter
    def exposure(self, value):
        try:
            self.cam.ExposureTimeRaw.SetValue(int(value*1e3))
        except _genicam.OutOfRangeException:
            pass
    @property
    def offset_x(self):
        return self.cam.OffsetX.GetValue()
    
    @offset_x.setter
    def offset_x(self, value):
        self.cam.OffsetX.SetValue(value)
    
    @property
    def offset_y(self):
        return self.cam.OffsetY.GetValue()
    
    @offset_y.setter
    def offset_y(self, value):
        self.cam.OffsetY.SetValue(value)
    
    @property
    def width(self):
        return self.cam.Width.GetValue()
    
    @width.setter
    def width(self, value):
        self.cam.Width.SetValue(value)
    
    @property  
    def height(self):
        return self.cam.Height.GetValue()
    
    @height.setter
    def height(self, value):
        self.cam.Height.SetValue(value)
    
    @property    
    def max_width(self):
        return self.cam.WidthMax.GetValue()
    
    @property
    def max_height(self):
        return self.cam.HeightMax.GetValue()
    
    @property
    def binning(self):
        return self._binning
        
    def start_grabbing(self):
        if self.trigger_mode == TriggerMode.FREERUN or self.trigger_mode == TriggerMode.HARDWARE:
            self.cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly, pylon.GrabLoop_ProvidedByUser)
        elif self.trigger_mode == TriggerMode.SOFTWARE:
            self.cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly, pylon.GrabLoop_ProvidedByInstantCamera)
    
    def return_frame(self):
        if self.trigger_mode == TriggerMode.FREERUN or self.trigger_mode == TriggerMode.HARDWARE:
            with self.cam.RetrieveResult(5000) as res:
                if res.GrabSucceeded():
                    return res.Array
                else:
                    raise RuntimeError('Grab failed')
                
    def request_frame(self):
        if self.trigger_mode == TriggerMode.SOFTWARE:
            self.lock.acquire()
            if self.waiting_for_trigger:
                print('already waiting for trigger')
                self.lock.release()
                return
            self.waiting_for_trigger = True
            self.lock.release()
            try:
                if self.cam.WaitForFrameTriggerReady(1, pylon.TimeoutHandling_ThrowException):
                    self.cam.ExecuteSoftwareTrigger()
                    self.lock.acquire()
                    self.waiting_for_trigger = False
                    self.lock.release()
            except:
                #                print('trigger timed out')
                self.lock.acquire()
                self.waiting_for_trigger = False
                self.lock.release()
    
    def register_event_handler(self, handler):
        self.cam.RegisterImageEventHandler(handler, pylon.RegistrationMode_ReplaceAll, pylon.Cleanup_Delete)
    
    def stop_grabbing(self):
        self.cam.StopGrabbing()

    def is_grabbing(self):
        return self.cam.IsGrabbing()
    
    def release_camera(self):
        self.cam.Close()
