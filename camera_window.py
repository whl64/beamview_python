import matplotlib as mpl

mpl.use('TkAgg')
import tkinter as tk

from camera_frame import CameraFrame


class CameraWindow(tk.Toplevel):    
    def __init__(self, root):
        super().__init__()
        self.title('Beamview')
        self.camera_frames = {}
        self.protocol('WM_DELETE_WINDOW', self.cleanup)
        self.root = root
        self.update_frames()
        
    def regrid(self):
        new_frames = {}
        for frame in self.camera_frames.values():
            if frame.winfo_exists():
                frame.grid_forget()
                new_frames[frame.cam.serial_number] = frame
                
        for i, frame in enumerate(new_frames.values()):
            self.assign_frame_to_grid(frame, i)
        self.camera_frames = new_frames
        self.assign_grid_weights()
        
    def assign_frame_to_grid(self, frame, index):
        assigned_row = index % 2
        assigned_column = index // 2
        frame.grid(row=assigned_row, column=assigned_column, sticky='nsew')
        
    def assign_grid_weights(self):
        for col in range(self.grid_size()[0]):
            self.grid_columnconfigure(col, weight=1)
            
        for row in range(self.grid_size()[1]):
            self.grid_rowconfigure(row, weight=1)
    
    def cleanup(self):
        self.root.destroy()
    
    def add_camera(self, cam):
        frame = CameraFrame(self, cam)
        self.camera_frames[cam.serial_number] = frame
        self.assign_frame_to_grid(frame, len(self.camera_frames) - 1)
        self.assign_grid_weights()
            
        return frame
        
    def update_frames(self):
        for address in self.camera_frames:
            self.camera_frames[address].update_frames()
        self.after(50, self.update_frames)

