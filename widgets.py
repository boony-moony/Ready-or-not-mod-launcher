"""
GUI widgets for Ready or Not Mod Manager
"""
import os
import tempfile
import zipfile
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QCheckBox, QListWidgetItem, QMessageBox, QInputDialog,
    QFileDialog, QTextEdit, QSplitter, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import Optional

from models import Instance, Mod


class InstanceListWidget(QWidget):
    """Left panel: Instance list and controls"""
    
    instance_selected = Signal(str)  # Emits instance name
    instance_activated = Signal(str)  # Emits instance name when enabled
    instance_deactivated = Signal()
    instance_create_requested = Signal(str)  # Emits new instance name
    instance_delete_requested = Signal(str)  # Emits instance name to delete
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_instance: Optional[str] = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Instances")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Instance list
        self.instance_list = QListWidget()
        self.instance_list.itemClicked.connect(self._on_instance_clicked)
        layout.addWidget(self.instance_list)
        
        # Create instance button
        self.create_btn = QPushButton("+ Create Instance")
        self.create_btn.clicked.connect(self._on_create_instance)
        layout.addWidget(self.create_btn)
        
        # Open library folder button
        self.open_folder_btn = QPushButton("📁 Open Mods Library")
        self.open_folder_btn.clicked.connect(self._on_open_library_folder)
        layout.addWidget(self.open_folder_btn)
        
        # Delete instance button
        self.delete_btn = QPushButton("Delete Instance")
        self.delete_btn.clicked.connect(self._on_delete_instance)
        self.delete_btn.setEnabled(False)
        layout.addWidget(self.delete_btn)
        
        # Activate/Deactivate controls
        control_group = QGroupBox("Activation")
        control_layout = QVBoxLayout(control_group)
        
        self.activate_btn = QPushButton("Enable Instance")
        self.activate_btn.clicked.connect(self._on_activate)
        self.activate_btn.setEnabled(False)
        control_layout.addWidget(self.activate_btn)
        
        self.deactivate_btn = QPushButton("Disable All Mods")
        self.deactivate_btn.clicked.connect(self._on_deactivate)
        control_layout.addWidget(self.deactivate_btn)
        
        layout.addWidget(control_group)
        
        # Status label
        self.status_label = QLabel("No instance active")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "padding: 10px; background: #2d2d2d; border-radius: 5px; "
            "color: #9e9e9e; border: 1px solid #3c3c3c;"
        )
        layout.addWidget(self.status_label)
    
    def refresh_instances(self, instances: list[str]):
        """Refresh the instance list"""
        current = self.instance_list.currentItem()
        current_text = current.text() if current else None
        
        self.instance_list.clear()
        for name in instances:
            self.instance_list.addItem(name)
        
        # Restore selection
        if current_text:
            items = self.instance_list.findItems(current_text, Qt.MatchExactly)
            if items:
                self.instance_list.setCurrentItem(items[0])
    
    def set_active_instance(self, name: Optional[str]):
        """Set the active instance"""
        self.active_instance = name
        if name:
            self.status_label.setText(f"✓ Active: {name}")
            self.status_label.setStyleSheet(
                "padding: 10px; background: #1b5e20; border-radius: 5px; "
                "color: #a5d6a7; border: 1px solid #2e7d32; font-weight: bold;"
            )
        else:
            self.status_label.setText("No instance active")
            self.status_label.setStyleSheet(
                "padding: 10px; background: #2d2d2d; border-radius: 5px; "
                "color: #9e9e9e; border: 1px solid #3c3c3c;"
            )
    
    def _on_instance_clicked(self, item: QListWidgetItem):
        """Handle instance selection"""
        self.delete_btn.setEnabled(True)
        self.activate_btn.setEnabled(True)
        self.instance_selected.emit(item.text())
    
    def _on_create_instance(self):
        """Handle create instance button"""
        name, ok = QInputDialog.getText(
            self, "Create Instance", "Instance name:"
        )
        if ok and name:
            # Validate name
            if not name.strip():
                QMessageBox.warning(self, "Invalid Name", "Instance name cannot be empty.")
                return
            
            # Check if already exists
            items = self.instance_list.findItems(name, Qt.MatchExactly)
            if items:
                QMessageBox.warning(self, "Duplicate Name", f"Instance '{name}' already exists.")
                return
            
            # Emit signal to create instance
            self.instance_create_requested.emit(name)
    
    def _on_delete_instance(self):
        """Handle delete instance button"""
        current = self.instance_list.currentItem()
        if not current:
            return
        
        name = current.text()
        reply = QMessageBox.question(
            self, "Delete Instance",
            f"Delete instance '{name}'?\n\nMods will remain in the library.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.instance_delete_requested.emit(name)
    
    def _on_activate(self):
        """Handle activate button"""
        current = self.instance_list.currentItem()
        if current:
            self.instance_activated.emit(current.text())
    
    def _on_deactivate(self):
        """Handle deactivate button"""
        self.instance_deactivated.emit()
    
    def _on_open_library_folder(self):
        """Open the mods library folder in file manager"""
        import subprocess
        from pathlib import Path
        
        mods_dir = Path.home() / ".ron-modmgr" / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Try xdg-open (works on most Linux systems)
            subprocess.Popen(["xdg-open", str(mods_dir)])
        except Exception as e:
            QMessageBox.warning(
                self, "Error",
                f"Could not open folder:\n{e}\n\nPath: {mods_dir}"
            )


class ModListWidget(QWidget):
    """Main panel: Mods in current instance"""
    
    mod_toggled = Signal(str, bool)  # filename, enabled
    add_mods_requested = Signal(list)  # list of file paths
    remove_mods_requested = Signal(list)  # list of filenames
    scan_library_requested = Signal()  # request to scan and add mods from library
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_instance: Optional[Instance] = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title = QLabel("No instance selected")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title.setFont(title_font)
        header_layout.addWidget(self.title)
        
        header_layout.addStretch()
        
        # Add mod button
        self.add_mod_btn = QPushButton("Add Mod")
        self.add_mod_btn.clicked.connect(self._on_add_mod)
        self.add_mod_btn.setEnabled(False)
        header_layout.addWidget(self.add_mod_btn)
        
        # Scan library button
        self.scan_btn = QPushButton("📚 Scan Library")
        self.scan_btn.clicked.connect(self._on_scan_library)
        self.scan_btn.setEnabled(False)
        self.scan_btn.setToolTip("Add all mods from library to this instance")
        header_layout.addWidget(self.scan_btn)
        
        # Remove mod button
        self.remove_mod_btn = QPushButton("Remove Mod")
        self.remove_mod_btn.clicked.connect(self._on_remove_mod)
        self.remove_mod_btn.setEnabled(False)
        header_layout.addWidget(self.remove_mod_btn)
        
        layout.addLayout(header_layout)
        
        # Mod list
        self.mod_list = QListWidget()
        self.mod_list.itemChanged.connect(self._on_mod_checked)
        self.mod_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.mod_list)
        
        # Info label
        self.info_label = QLabel("Select an instance to view mods")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #9e9e9e; padding: 20px; font-size: 13px;")
        layout.addWidget(self.info_label)
    
    def load_instance(self, instance: Optional[Instance]):
        """Load an instance and display its mods"""
        self.current_instance = instance
        self.mod_list.clear()
        
        if instance:
            self.title.setText(f"Instance: {instance.name}")
            self.add_mod_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)
            self.info_label.hide()
            self.mod_list.show()
            
            for mod in instance.mods:
                item = QListWidgetItem(f"{mod.name} ({self._format_size(mod.size)})")
                item.setData(Qt.UserRole, mod.filename)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if mod.enabled else Qt.Unchecked)
                self.mod_list.addItem(item)
        else:
            self.scan_btn.setEnabled(False)
            self.title.setText("No instance selected")
            self.add_mod_btn.setEnabled(False)
            self.remove_mod_btn.setEnabled(False)
            self.mod_list.hide()
            self.info_label.show()
    
    def _format_size(self, size: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _on_mod_checked(self, item: QListWidgetItem):
        """Handle mod checkbox toggle"""
        filename = item.data(Qt.UserRole)
        enabled = item.checkState() == Qt.Checked
        self.mod_toggled.emit(filename, enabled)
    
    def _on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.mod_list.selectedItems()) > 0
        self.remove_mod_btn.setEnabled(has_selection and self.current_instance is not None)
    
    def _on_add_mod(self):
        """Handle add mod button"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Mod Files", str(Path.home()), "PAK Files (*.pak)"
        )
        
        if files:
            self.add_mods_requested.emit(files)
    
    def _on_remove_mod(self):
        """Handle remove mod button"""
        selected = self.mod_list.selectedItems()
        if not selected:
            return
        
        filenames = [item.data(Qt.UserRole) for item in selected]
        
        reply = QMessageBox.question(
            self, "Remove Mods",
            f"Remove {len(filenames)} mod(s) from this instance?\n\n"
            "Mods will remain in the library.",
            QMessageBox.Yes | QMessageBox.No
        )
        
    
    
    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                if self._is_supported_file(path):
                    event.acceptProposedAction()
                    return
    
    def dropEvent(self, event):
        """Handle drop event"""
        if event.mimeData().hasUrls():
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            self.add_mods_requested.emit(files)
            event.acceptProposedAction()
    
    def _is_supported_file(self, filepath: str) -> bool:
        """Check if file is a supported mod file or archive"""
        path = Path(filepath)
        pak = path.suffix.lower() == '.pak'
        archive = path.suffix.lower() in ['.zip', '.7z', '.rar']
        return pak or archive
    
    def _on_scan_library(self):
        """Handle scan library button"""
        self.scan_library_requested.emit()


class LogWidget(QWidget):
    """Bottom panel: Operation logs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Operation Log")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_btn)
    
    def log(self, message: str, level: str = "info"):
        """Add a log message"""
        colors = {
            "info": "#90caf9",
            "success": "#81c784",
            "warning": "#ffb74d",
            "error": "#e57373"
        }
        icons = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗"
        }
        color = colors.get(level, "#90caf9")
        icon = icons.get(level, "•")
        
        html = f'<span style="color: {color}; font-weight: bold;">{icon}</span> <span style="color: {color};">{message}</span>'
        self.log_text.append(html)

