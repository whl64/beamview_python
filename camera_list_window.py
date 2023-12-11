
from PyQt5.QtWidgets import QMainWindow, QTreeView, QAbstractItemView
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QFont
from PyQt5.QtCore import Qt

class CameraListWindow(QMainWindow):
    def __init__(self, root, app):
        super().__init__()
        self.setMinimumSize(200, 200)
        self.setWindowTitle('Camera list')
        self.app = app
        self.root = root
           
        self.camera_list = QTreeView(self)
        self.camera_list_model = BoldItemModel()
        self.camera_list_model.setHorizontalHeaderLabels(('Name', 'Model'))
        self.camera_list.setModel(self.camera_list_model)
        self.camera_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.camera_list.setUniformRowHeights(True)
        
        for device in self.root.devices:
            name = QStandardItem(device.GetUserDefinedName())
            model = QStandardItem(device.GetModelName())
            name.setEditable(False)
            model.setEditable(False)
            self.camera_list_model.appendRow((name, model))
            
        self.camera_list.doubleClicked.connect(self.add_camera)
        # layout.addChildWidget(self.camera_list)
        # self.camera_list.bind('<Double-Button-1>', self.add_camera)
        # scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.camera_list.yview)
        
        self.setCentralWidget(self.camera_list)
            
    def closeEvent(self, event):
        self.hide()
        event.ignore()
     
    def add_camera(self, *args):
        index = self.camera_list.currentIndex().row()
        self.camera_list_model.boldRow(index)
        self.root.add_camera(index)
        
    def remove_camera(self, cam):
        self.camera_list_model.unboldRow(self.find_camera_index(cam))

        
class BoldItemModel(QStandardItemModel):
    def __init__(self):
        self._bold_rows = []
        super().__init__()
    
    def appendRow(self, args):
        self._bold_rows.append(False)
        super().appendRow(args)
        
    def emitRowChanged(self, row):
        for col in (0, 1):
            index = self.index(row, col)
            self.dataChanged.emit(index, index)
    
    def boldRow(self, row):
        self._bold_rows[row] = True
        self.emitRowChanged(row)
    
    def unboldRow(self, row):
        self._bold_rows[row] = False
        self.emitRowChanged(row)
    
    def data(self, index, role):
        if role == Qt.FontRole:
            if self._bold_rows[index.row()]:
                boldFont = QFont()
                boldFont.setBold(True)
                return boldFont
        return super().data(index, role)
            
