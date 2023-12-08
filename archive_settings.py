from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt5 import QtCore

class ArchiveSettings(QDialog):
    
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.setWindowTitle('Archive settings')
        
        Qbtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        
        self.buttonBox = QDialogButtonBox(Qbtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        self.layout = QVBoxLayout()
        
        directory_row = QHBoxLayout()
        self.directory_box = QLineEdit(text=self.root.archive_dir, parent=self)
        self.directory_box.readOnly = True
        directory_button = QPushButton(text='...', parent=self)
        directory_button.clicked.connect(self.find_file)
        directory_row.addWidget(QLabel(text='Archive directory:', parent=self))
        directory_row.addWidget(self.directory_box)
        directory_row.addWidget(directory_button)

        self.layout.addLayout(directory_row)
        
        
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        
        # self.setFixedSize(self.size())
        
    def find_file(self):
        filename = QFileDialog.getExistingDirectory(self, 'Open directory', self.root.archive_dir)
        self.directory_box.setText(filename)
