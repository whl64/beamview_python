import camera_wrapper as cw
import pypylon.pylon as pylon

class Basler_Camera(cw.Camera):
    def __init__(self, address):
        super().__init__(address)
        tlf = pylon.TlFactory.GetInstance()
        di = pylon.DeviceInfo()
        di.SetAddress(address)
        device = tlf.EnumerateDevices([di, ])[0]
        self.name = device.GetUserDefinedName()
        self.model = device.GetModelName()
        self.cam = pylon.InstantCamera(tlf.CreateDevice(device))
        self.cam.Open()
        
        self.cam.GevSCPSPacketSize.SetValue( 8192 )  #  9708 abs max new cam.
        self.cam.GevSCPD.SetValue( 12000 ) #  interpacket delay
        
        if self.model == "scA1400-17gm":
            self._pixel_format = "Mono16"		#  Yes, this is 12-bit
        elif self.model == "acA1920-50gm":
            self._pixel_format = "Mono12"		#  12-bit
            
        self.cam.PixelFormat.SetValue(self.pixel_format)
    
    @property
    def pixel_format(self):
        return self._pixel_format
    
    @property
    def gain(self):
        return self.cam.GainRaw.GetValue()
    
    @gain.setter
    def gain(self, value):
        self.cam.GainRaw.SetValue(value)
    
    '''
    Exposure time in ms
    '''
    @property
    def exposure(self):
        return self.cam.ExposureTimeRaw.GetValue()/1e3
    
    @exposure.setter
    def exposure(self, value):
        self.cam.ExposureTimeRaw.SetValue(int(value*1e3))
    
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
        
    def start_grabbing(self):
        self.cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly, pylon.GrabLoop_ProvidedByUser)
    
    def return_frame(self):
        with self.cam.RetrieveResult(5000) as res:
            if res.GrabSucceeded():
                return res.Array
            else:
                raise RuntimeError('Grab failed')
    
    def stop_grabbing(self):
        self.cam.StopGrabbing()

    def is_grabbing(self):
        return self.cam.IsGrabbing()
    
    def release_camera(self):
        self.cam.Close()
