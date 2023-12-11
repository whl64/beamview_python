from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFileDialog, QCheckBox)
from PyQt5 import QtCore

class ArchiveSettings(QDialog):
    
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.setWindowTitle('Archive settings')
        
        self.base_filename = r'{cam_name}_{timestamp}'
        
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
        
        filename_row = QHBoxLayout()
        filename_row.addWidget(QLabel(text='File prefix:', parent=self))
        self.prefix_box = QLineEdit(text=self.root.archive_prefix)
        self.prefix_box.textChanged.connect(self.filename_text_changed)
        filename_row.addWidget(self.prefix_box)
        filename_row.addWidget(QLabel(text='File suffix:', parent=self))
        self.suffix_box = QLineEdit(text=self.root.archive_suffix)
        self.suffix_box.textChanged.connect(self.filename_text_changed)
        filename_row.addWidget(self.suffix_box)
        self.layout.addLayout(filename_row)
        
        shot_number_row = QHBoxLayout()
        self.shot_number_check = QCheckBox()
        shot_number_row.addWidget(QLabel(text=''))
        
        self.preview_label = QLabel(text='', parent=self)
        self.layout.addWidget(self.preview_label)
        
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        
        self.refresh_preview()
        # self.setFixedSize(self.size())
    
    def filename_text_changed(self, text):
        self.refresh_preview()
    
    def refresh_preview(self):
        shot_number_string = ''
        if self.root.archive_shot_number:
            shot_number_string = r'_{shot_number}'
        prefix_string = self.prefix_box.text() + '_' if self.prefix_box.text() != '' else ''
        suffix_string = '_' + self.suffix_box.text() if self.suffix_box.text() != '' else ''
        preview_string = f'Filename preview: {prefix_string}{self.base_filename}{suffix_string}{shot_number_string}.tiff'
        self.preview_label.setText(preview_string)

    def find_file(self):
        filename = QFileDialog.getExistingDirectory(self, 'Open directory', self.root.archive_dir)
        self.directory_box.setText(filename)
