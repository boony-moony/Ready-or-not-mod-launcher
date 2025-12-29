"""
Ready or Not Mod Manager
Main application entry point
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from models import DataManager, Instance, Mod, AppState
from mod_manager import ModManager
from widgets import InstanceListWidget, ModListWidget, LogWidget


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize data
        self.data_dir = Path.home() / ".ron-modmgr"
        self.data_manager = DataManager(self.data_dir)
        self.mod_manager = ModManager(self.data_manager)
        self.state = self.data_manager.load_state()
        
        self.current_instance: Optional[Instance] = None
        
        self._init_ui()
        self._check_game_path()
        self._load_instances()
        
        # Restore active instance
        if self.state.active_instance:
            self._load_instance(self.state.active_instance)
            self.instance_list.set_active_instance(self.state.active_instance)
    
    def _init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle("Ready or Not Mod Manager")
        self.setGeometry(100, 100, 1200, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Top bar
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)
        
        # Main content (splitter)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Instances
        self.instance_list = InstanceListWidget(self)
        self.instance_list.instance_selected.connect(self._on_instance_selected)
        self.instance_list.instance_activated.connect(self._on_instance_activated)
        self.instance_list.instance_deactivated.connect(self._on_instance_deactivated)
        self.instance_list.instance_create_requested.connect(self.create_instance)
        self.instance_list.instance_delete_requested.connect(self.delete_instance)
        self.instance_list.setMaximumWidth(300)
        splitter.addWidget(self.instance_list)
        
        # Right side: Mods + Logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main panel: Mods
        self.mod_list = ModListWidget(self)
        self.mod_list.mod_toggled.connect(self._on_mod_toggled)
        self.mod_list.add_mods_requested.connect(self.add_mods_to_instance)
        self.mod_list.remove_mods_requested.connect(self.remove_mods_from_instance)
        self.mod_list.scan_library_requested.connect(self.scan_and_add_library_mods)
        right_layout.addWidget(self.mod_list, stretch=3)
        
        # Log panel
        self.log_widget = LogWidget()
        right_layout.addWidget(self.log_widget, stretch=1)
        
        splitter.addWidget(right_panel)
        
        main_layout.addWidget(splitter)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
                border: 1px solid #505050;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
            QPushButton:disabled {
                color: #666;
                background-color: #252525;
                border: 1px solid #2d2d2d;
            }
            QListWidget {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                background-color: #252525;
                color: #e0e0e0;
            }
            QListWidget::item {
                padding: 8px;
                color: #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
            QListWidget::item:checked {
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QTextEdit {
                background-color: #252525;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #e0e0e0;
            }
            QCheckBox {
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3c3c3c;
                border-radius: 2px;
                background-color: #252525;
            }
            QCheckBox::indicator:checked {
                background-color: #0d47a1;
                border: 1px solid #0d47a1;
            }
        """)
    
    def _create_top_bar(self) -> QWidget:
        """Create the top bar with title and launch button"""
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #2c3e50; padding: 10px;")
        layout = QHBoxLayout(top_bar)
        
        # Title
        title = QLabel("Ready or Not Mod Manager")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Game path indicator
        self.path_label = QLabel()
        self.path_label.setStyleSheet("color: white; font-size: 11px;")
        layout.addWidget(self.path_label)
        
        # Launch button
        self.launch_btn = QPushButton("Launch Game")
        self.launch_btn = QPushButton("🎮 Launch Game")
        self.launch_btn.clicked.connect(self._on_launch_game)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #1b5e20;
            }
        """)
        layout.addWidget(self.launch_btn)
        
        return top_bar
    
    def _check_game_path(self):
        """Check if game path is valid and update UI"""
        if self.mod_manager.is_game_path_valid():
            path = self.mod_manager.get_game_path()
            # Show shortened path
            if len(path) > 50:
                path = "..." + path[-47:]
            self.path_label.setText(f"Game: {path}")
            self.log_widget.log("Game directory detected and ready", "success")
        else:
            self.path_label.setText("⚠ Game directory not found")
            
            # Get detailed error message
            error_msg = self.mod_manager.get_error_message()
            if error_msg:
                self.log_widget.log("Game directory error: See details", "error")
                QMessageBox.warning(
                    self, "Game Directory Error",
                    error_msg
                )
            else:
                self.log_widget.log(
                    "Game directory not found. Please ensure Ready or Not is installed via Steam.",
                    "error"
                )
                QMessageBox.warning(
                    self, "Game Not Found",
                    "Ready or Not game directory not found.\n\n"
                    "Please ensure the game is installed via Steam."
                )
    
    def _load_instances(self):
        """Load and display all instances"""
        instances = self.data_manager.list_instances()
        self.instance_list.refresh_instances(instances)
        self.log_widget.log(f"Loaded {len(instances)} instance(s)", "info")
    
    def _load_instance(self, name: str):
        """Load a specific instance"""
        instance = self.data_manager.load_instance(name)
        if instance:
            self.current_instance = instance
            self.mod_list.load_instance(instance)
            
            # Check for missing mods
            missing = self.mod_manager.verify_mods(instance)
            if missing:
                self.log_widget.log(
                    f"Warning: {len(missing)} missing mod(s) in instance '{name}'",
                    "warning"
                )
            
            # Check for conflicts
            conflicts = self.mod_manager.detect_conflicts(instance)
            for conflict in conflicts:
                self.log_widget.log(f"Warning: {conflict}", "warning")
    
    def _on_instance_selected(self, name: str):
        """Handle instance selection"""
        self._load_instance(name)
        self.log_widget.log(f"Selected instance: {name}", "info")
    
    def _on_instance_activated(self, name: str):
        """Handle instance activation"""
        if not self.mod_manager.is_game_path_valid():
            QMessageBox.critical(
                self, "Error", "Game directory not found. Cannot activate instance."
            )
            return
        
        instance = self.data_manager.load_instance(name)
        if not instance:
            return
        
        # Activate instance
        count, errors = self.mod_manager.activate_instance(instance)
        
        if errors:
            error_msg = "\n".join(errors)
            QMessageBox.warning(
                self, "Activation Errors",
                f"Instance activated with {len(errors)} error(s):\n\n{error_msg}"
            )
            for error in errors:
                self.log_widget.log(error, "error")
        
        # Update state
        self.state.active_instance = name
        self.data_manager.save_state(self.state)
        self.instance_list.set_active_instance(name)
        
        self.log_widget.log(
            f"Activated instance '{name}': {count} mod(s) enabled",
            "success"
        )
        
        QMessageBox.information(
            self, "Instance Activated",
            f"Instance '{name}' activated.\n\n"
            f"{count} mod(s) have been symlinked to the game directory."
        )
    
    def _on_instance_deactivated(self):
        """Handle instance deactivation"""
        if not self.mod_manager.is_game_path_valid():
            QMessageBox.critical(
                self, "Error", "Game directory not found."
            )
            return
        
        count = self.mod_manager.deactivate_all()
        
        # Update state
        self.state.active_instance = None
        self.data_manager.save_state(self.state)
        self.instance_list.set_active_instance(None)
        
        self.log_widget.log(f"Deactivated all mods: removed {count} symlink(s)", "success")
        
        QMessageBox.information(
            self, "Mods Deactivated",
            f"All mods have been deactivated.\n\n"
            f"{count} symlink(s) removed."
        )
    
    def _on_mod_toggled(self, filename: str, enabled: bool):
        """Handle mod enable/disable toggle"""
        if not self.current_instance:
            return
        
        # Update mod state
        for mod in self.current_instance.mods:
            if mod.filename == filename:
                mod.enabled = enabled
                break
        
        # Save instance
        self.data_manager.save_instance(self.current_instance)
        
        status = "enabled" if enabled else "disabled"
        self.log_widget.log(f"Mod '{filename}' {status}", "info")
    
    def create_instance(self, name: str):
        """Create a new instance"""
        # Create instance
        instance = Instance(
            name=name,
            created=datetime.now().isoformat()
        )
        
        # Save
        self.data_manager.save_instance(instance)
        
        # Refresh list
        self._load_instances()
        
        # Select new instance
        items = self.instance_list.instance_list.findItems(name, Qt.MatchExactly)
        if items:
            self.instance_list.instance_list.setCurrentItem(items[0])
            self._load_instance(name)
        
        self.log_widget.log(f"Created instance: {name}", "success")
    
    def delete_instance(self, name: str):
        """Delete an instance"""
        # Check if active
        if self.state.active_instance == name:
            QMessageBox.warning(
                self, "Cannot Delete",
                "Cannot delete the active instance. Please deactivate it first."
            )
            return
        
        # Delete
        self.data_manager.delete_instance(name)
        
        # Refresh
        self._load_instances()
        self.current_instance = None
        self.mod_list.load_instance(None)
        
        self.log_widget.log(f"Deleted instance: {name}", "info")
    
    def add_mods_to_instance(self, file_paths: list[str]):
        """Add mods to the current instance"""
        if not self.current_instance:
            return
        
        added_count = 0
        failed_count = 0
        
        for file_path in file_paths:
            path = Path(file_path)
            
            # Check if it's an archive
            if path.suffix.lower() in ['.zip', '.7z', '.rar']:
                # Import archive
                mods, error = self.data_manager.import_archive(path)
                
                if error:
                    self.log_widget.log(f"Archive error ({path.name}): {error}", "error")
                    failed_count += 1
                    continue
                
                # Add extracted mods to instance
                for mod in mods:
                    if self.current_instance.add_mod(mod):
                        added_count += 1
                        self.log_widget.log(f"Extracted and added: {mod.filename}", "success")
                    else:
                        self.log_widget.log(f"Mod already in instance: {mod.filename}", "warning")
            
            elif path.suffix.lower() == '.pak':
                # Import single mod
                mod = self.data_manager.import_mod(path)
                
                if not mod:
                    # Check if already in library
                    filename = path.name
                    library_mods = self.data_manager.list_library_mods()
                    existing = next((m for m in library_mods if m.filename == filename), None)
                    
                    if existing:
                        # Use existing mod from library
                        if self.current_instance.add_mod(existing):
                            added_count += 1
                            self.log_widget.log(f"Added mod from library: {filename}", "info")
                        else:
                            self.log_widget.log(f"Mod already in instance: {filename}", "warning")
                    else:
                        self.log_widget.log(f"Failed to import: {filename}", "error")
                        failed_count += 1
                    continue
                
                # Add to instance
                if self.current_instance.add_mod(mod):
                    added_count += 1
                    self.log_widget.log(f"Imported and added: {mod.filename}", "success")
                else:
                    self.log_widget.log(f"Mod already in instance: {mod.filename}", "warning")
            
            else:
                self.log_widget.log(f"Unsupported file format: {path.name}", "warning")
                failed_count += 1
        
        # Save instance
        self.data_manager.save_instance(self.current_instance)
        
        # Refresh display
        self.mod_list.load_instance(self.current_instance)
        
        # Show summary
        if added_count > 0 or failed_count > 0:
            msg = f"Added {added_count} mod(s) to instance '{self.current_instance.name}'."
            if failed_count > 0:
                msg += f"\n{failed_count} file(s) failed to import."
            
            self.log_widget.log(msg, "success" if added_count > 0 else "warning")
            QMessageBox.information(self, "Import Complete", msg)

    
    def remove_mods_from_instance(self, filenames: list[str]):
        """Remove mods from the current instance"""
        if not self.current_instance:
            return
        
        for filename in filenames:
            self.current_instance.remove_mod(filename)
            self.log_widget.log(f"Removed mod: {filename}", "info")
        
        # Save instance
        self.data_manager.save_instance(self.current_instance)
        
        # Refresh display
        self.mod_list.load_instance(self.current_instance)
    
    def scan_and_add_library_mods(self):
        """Scan library folder and add all mods to current instance"""
        if not self.current_instance:
            return
        
        # Get all mods from library
        library_mods = self.data_manager.list_library_mods()
        
        if not library_mods:
            QMessageBox.information(
                self, "No Mods Found",
                "No mods found in the library.\n\n"
                f"Add .pak files to: {self.data_manager.mods_dir}"
            )
            return
        
        # Add mods that aren't already in the instance
        added_count = 0
        skipped_count = 0
        
        for mod in library_mods:
            if self.current_instance.add_mod(mod):
                added_count += 1
                self.log_widget.log(f"Added from library: {mod.filename}", "info")
            else:
                skipped_count += 1
        
        # Save instance
        if added_count > 0:
            self.data_manager.save_instance(self.current_instance)
            self.mod_list.load_instance(self.current_instance)
        
        # Show summary
        msg = f"Added {added_count} mod(s) to instance '{self.current_instance.name}'."
        if skipped_count > 0:
            msg += f"\n{skipped_count} mod(s) already in instance."
        
        self.log_widget.log(msg, "success" if added_count > 0 else "info")
        QMessageBox.information(self, "Library Scan Complete", msg)
    
    def _on_launch_game(self):
        """Launch Ready or Not"""
        import subprocess
        
        try:
            cmd = self.mod_manager.get_steam_launch_command()
            subprocess.Popen(cmd.split())
            self.log_widget.log("Launching Ready or Not...", "success")
        except Exception as e:
            self.log_widget.log(f"Failed to launch game: {e}", "error")
            QMessageBox.critical(
                self, "Launch Error",
                f"Failed to launch game:\n{e}"
            )


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Ready or Not Mod Manager")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
