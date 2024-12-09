from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFileDialog, QCheckBox)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt

class ArchiveSettings(QDialog):
    
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle('Archive settings')
        
        self.base_filename = r'{cam_name}_{timestamp}'
        
        Qbtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        
        self.buttonBox = QDialogButtonBox(Qbtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        self.layout = QVBoxLayout()
        
        top_row = QHBoxLayout()        
        self.archive_check = QCheckBox(text='Enable archiving?', parent=self)
        self.archive_check.setChecked(self.root.archive_mode)
        top_row.addWidget(self.archive_check)
        
        self.low_res_check = QCheckBox(text='Enable low resolution mode?', parent=self)
        self.low_res_check.setChecked(self.root.low_res_mode)
        self.low_res_check.stateChanged.connect(self.trigger_refresh_from_widget)
        top_row.addWidget(self.low_res_check)
        self.layout.addLayout(top_row)
        
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
        self.prefix_box.textChanged.connect(self.trigger_refresh_from_widget)
        filename_row.addWidget(self.prefix_box)
        filename_row.addWidget(QLabel(text='File suffix:', parent=self))
        self.suffix_box = QLineEdit(text=self.root.archive_suffix)
        self.suffix_box.textChanged.connect(self.trigger_refresh_from_widget)
        filename_row.addWidget(self.suffix_box)
        self.layout.addLayout(filename_row)
        
        shot_number_row = QHBoxLayout()
        self.shot_number_check = QCheckBox(text='Append shot number?', parent=self)
        self.shot_number_check.setChecked(self.root.archive_shot_number)
        self.shot_number_check.stateChanged.connect(self.trigger_refresh_from_widget)
        shot_number_row.addWidget(self.shot_number_check)
        shot_number_row.addWidget(QLabel(text='Starting shot number:'))
        self.shot_number_box = QLineEdit(text=str(self.root.archive_shot_number_offset))
        shot_number_validator = QIntValidator(bottom=0, parent=self)
        self.shot_number_box.setValidator(shot_number_validator)
        self.shot_number_box.textChanged.connect(self.trigger_refresh_from_widget)
        shot_number_row.addWidget(self.shot_number_box)
        self.layout.addLayout(shot_number_row)
        
        self.preview_label = QLabel(text='', parent=self)
        self.layout.addWidget(self.preview_label)
        
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel(text='Minimum time between saved images (0 to save every image)'))
        self.interval_box = QLineEdit(text=str(self.root.archive_time), parent=self)
        self.interval_box.setValidator(shot_number_validator)
        interval_row.addWidget(self.interval_box)
        self.layout.addLayout(interval_row)
        
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        
        self.refresh_preview()
        # self.setFixedSize(self.size())
    
    def trigger_refresh_from_widget(self, _):
        self.refresh_preview()
    
    def refresh_preview(self):
        shot_number_string = r'_{shot_number}' if self.shot_number_check.isChecked() else ''
        prefix_string = self.prefix_box.text() + '_' if self.prefix_box.text() != '' else ''
        suffix_string = '_' + self.suffix_box.text() if self.suffix_box.text() != '' else ''
        file_ext_string = '.png' if self.low_res_check.isChecked() else '.tiff'
        preview_string = f'Filename preview: {prefix_string}{self.base_filename}{suffix_string}{shot_number_string}{file_ext_string}'
        self.preview_label.setText(preview_string)

    def find_file(self):
        filename = QFileDialog.getExistingDirectory(self, 'Open directory', self.root.archive_dir)
        self.directory_box.setText(filename)       
        
    def accept(self):
        self.root.set_archive_parameters(self.archive_check.isChecked(), self.low_res_check.isChecked(), int(self.interval_box.text()), self.directory_box.text(),
                                         self.shot_number_check.isChecked(), int(self.shot_number_box.text()),
                                         self.prefix_box.text(), self.suffix_box.text())
        super().accept()
