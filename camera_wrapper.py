'''
Abstract camera wrapper class


'''

from abc import ABC, abstractmethod

class Camera(ABC):
    
    '''
    Class initialization
    
    Parameters:
    address: Camera IP address
    '''
    @abstractmethod
    def __init__(self, serial_number):
        self.serial_number = serial_number
    
    @property
    def pixel_format(self):
        pass
    
    @property
    @abstractmethod
    def gain(self):
        pass
    
    @gain.setter
    @abstractmethod
    def gain(self, value):
        pass
        
    @property
    @abstractmethod
    def exposure(self):
        pass
    
    @exposure.setter
    @abstractmethod
    def exposure(self, value):
        pass
    
    @property
    @abstractmethod
    def offset_x(self):
        pass
    
    @offset_x.setter
    @abstractmethod
    def offset_x(self, value):
        pass
    
    @property
    @abstractmethod
    def offset_y(self):
        pass
    
    @offset_y.setter
    @abstractmethod
    def offset_y(self, value):
        pass
    
    @property
    @abstractmethod
    def width(self):
        pass
    
    @width.setter
    @abstractmethod
    def width(self, value):
        pass
    
    @property
    @abstractmethod
    def height(self):
        pass
    
    @height.setter
    @abstractmethod
    def height(self, value):
        pass
    
    @property
    @abstractmethod
    def max_width(self):
        pass
    
    @property
    @abstractmethod
    def max_height(self):
        pass
    
    @property
    @abstractmethod
    def binning(self):
        pass
    
    @property
    @abstractmethod
    def triggering(self):
        pass
    
    @abstractmethod
    def start_grabbing(self):
        pass
    
    @abstractmethod
    def return_frame(self):
        pass
    
    @abstractmethod
    def stop_grabbing(self):
        pass

    @abstractmethod
    def is_grabbing(self):
        pass
    
    @abstractmethod
    def release_camera(self):
        pass
