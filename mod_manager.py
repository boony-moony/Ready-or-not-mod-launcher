"""
Mod manager - handles symlink operations for Ready or Not
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple
from models import Mod, Instance, DataManager


class ModManager:
    """Manages mod activation via symlinks"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.game_mods_dir: Optional[Path] = None
        self.error_message: Optional[str] = None
        self._detect_game_path()
    
    def _find_steam_libraries(self) -> List[Path]:
        """
        Find all Steam library paths (native and Flatpak).
        Returns list of steamapps directories.
        """
        home = Path.home()
        libraries = []
        
        # Native Steam paths
        native_steam = home / ".steam/steam"
        if native_steam.exists():
            # Main library
            main_steamapps = native_steam / "steamapps"
            if main_steamapps.exists():
                libraries.append(main_steamapps)
            
            # Additional libraries from libraryfolders.vdf
            libraryfolders_vdf = main_steamapps / "libraryfolders.vdf"
            if libraryfolders_vdf.exists():
                try:
                    with open(libraryfolders_vdf, 'r') as f:
                        content = f.read()
                        # Parse VDF for additional library paths
                        import re
                        paths = re.findall(r'"path"\s+"([^"]+)"', content)
                        for path in paths:
                            lib_path = Path(path) / "steamapps"
                            if lib_path.exists() and lib_path not in libraries:
                                libraries.append(lib_path)
                except Exception as e:
                    print(f"Error parsing libraryfolders.vdf: {e}")
        
        # Flatpak Steam paths
        flatpak_steam = home / ".var/app/com.valvesoftware.Steam/.steam/steam"
        if flatpak_steam.exists():
            flatpak_steamapps = flatpak_steam / "steamapps"
            if flatpak_steamapps.exists() and flatpak_steamapps not in libraries:
                libraries.append(flatpak_steamapps)
            
            # Flatpak additional libraries
            libraryfolders_vdf = flatpak_steamapps / "libraryfolders.vdf"
            if libraryfolders_vdf.exists():
                try:
                    with open(libraryfolders_vdf, 'r') as f:
                        content = f.read()
                        import re
                        paths = re.findall(r'"path"\s+"([^"]+)"', content)
                        for path in paths:
                            lib_path = Path(path) / "steamapps"
                            if lib_path.exists() and lib_path not in libraries:
                                libraries.append(lib_path)
                except Exception as e:
                    print(f"Error parsing Flatpak libraryfolders.vdf: {e}")
        
        return libraries
    
    def _validate_and_create_mod_directory(self, steamapps: Path) -> Tuple[Optional[Path], Optional[str]]:
        """
        Validate prerequisites and create mod directory if needed.
        Returns (path, error_message).
        """
        # Check 1: appmanifest exists
        manifest = steamapps / "appmanifest_1144200.acf"
        if not manifest.exists():
            return None, None  # Game not in this library, continue searching
        
        # Check 2: Game files exist
        game_dir = steamapps / "common" / "Ready Or Not"
        if not game_dir.exists():
            return None, (
                "Ready or Not is registered in Steam but game files are missing.\n\n"
                "Please verify the game files in Steam:\n"
                "Right-click Ready or Not → Properties → Installed Files → Verify integrity"
            )
        
        # Check 3: Proton prefix exists
        compatdata_pfx = steamapps / "compatdata" / "1144200" / "pfx"
        if not compatdata_pfx.exists():
            return None, (
                "Ready or Not is installed, but the Proton prefix does not exist.\n\n"
                "Please launch the game once in Steam to generate the Proton prefix."
            )
        
        # All checks passed - now construct the full path to mods directory
        mods_path = (
            compatdata_pfx / "drive_c" / "users" / "steamuser" / 
            "AppData" / "Local" / "ReadyOrNot" / "Saved" / "Paks"
        )
        
        # If the directory exists, return it
        if mods_path.exists():
            return mods_path, None
        
        # Create only the missing tail directories (Saved/Paks)
        # First verify that the parent structure up to ReadyOrNot exists
        readyornot_dir = (
            compatdata_pfx / "drive_c" / "users" / "steamuser" / 
            "AppData" / "Local" / "ReadyOrNot"
        )
        
        # If even the base directories don't exist, the prefix might be incomplete
        appdata_local = compatdata_pfx / "drive_c" / "users" / "steamuser" / "AppData" / "Local"
        if not appdata_local.exists():
            return None, (
                "Proton prefix exists but appears incomplete.\n\n"
                "The AppData/Local directory structure is missing.\n"
                "Please launch the game once to complete prefix initialization."
            )
        
        # Safe to create the tail directories
        try:
            mods_path.mkdir(parents=True, exist_ok=True)
            print(f"Created mod directory: {mods_path}")
            return mods_path, None
        except Exception as e:
            return None, f"Failed to create mod directory: {e}"
    
    def _detect_game_path(self) -> Optional[Path]:
        """
        Detect and validate Ready or Not Proton mod directory.
        Creates missing directories only if all prerequisites are met.
        """
        libraries = self._find_steam_libraries()
        
        if not libraries:
            self.error_message = (
                "Steam installation not detected (native or Flatpak).\n\n"
                "Expected locations:\n"
                "  • ~/.steam/steam/steamapps (native)\n"
                "  • ~/.var/app/com.valvesoftware.Steam/.steam/steam/steamapps (Flatpak)"
            )
            return None
        
        # Check each library for Ready or Not
        for steamapps in libraries:
            path, error = self._validate_and_create_mod_directory(steamapps)
            
            if path:
                # Success! Found and validated the game
                self.game_mods_dir = path
                self.error_message = None
                return path
            
            if error:
                # Found the game but validation failed
                self.error_message = error
                return None
        
        # Game not found in any library
        self.error_message = (
            "Ready or Not is not installed in any detected Steam library.\n\n"
            f"Checked {len(libraries)} Steam librar{'y' if len(libraries) == 1 else 'ies'}.\n\n"
            "Please install Ready or Not from Steam."
        )
        return None
    
    def is_game_path_valid(self) -> bool:
        """Check if game path is detected and valid"""
        return self.game_mods_dir is not None and self.game_mods_dir.exists()
    
    def get_game_path(self) -> Optional[str]:
        """Get the game mods directory path"""
        return str(self.game_mods_dir) if self.game_mods_dir else None
    
    def get_error_message(self) -> Optional[str]:
        """Get the error message if game path detection failed"""
        return self.error_message
    
    def get_managed_symlinks(self) -> List[Path]:
        """Get all symlinks created by this manager"""
        if not self.is_game_path_valid():
            return []
        
        managed = []
        for item in self.game_mods_dir.iterdir():
            if item.is_symlink() and item.name.startswith(DataManager.SYMLINK_PREFIX):
                managed.append(item)
        return managed
    
    def clear_managed_symlinks(self) -> int:
        """Remove all manager-created symlinks"""
        if not self.is_game_path_valid():
            return 0
        
        count = 0
        for symlink in self.get_managed_symlinks():
            try:
                symlink.unlink()
                count += 1
            except Exception as e:
                print(f"Error removing symlink {symlink}: {e}")
        
        return count
    
    def activate_instance(self, instance: Instance) -> tuple[int, List[str]]:
        """
        Activate an instance by creating symlinks for its enabled mods
        Returns (count of symlinks created, list of errors)
        """
        if not self.is_game_path_valid():
            return 0, ["Game directory not found"]
        
        # Clear existing managed symlinks
        self.clear_managed_symlinks()
        
        errors = []
        count = 0
        
        for mod in instance.get_enabled_mods():
            # Verify mod file exists
            mod_path = Path(mod.path)
            if not mod_path.exists():
                errors.append(f"Mod file not found: {mod.filename}")
                continue
            
            # Create symlink with prefix
            symlink_name = f"{DataManager.SYMLINK_PREFIX}{mod.filename}"
            symlink_path = self.game_mods_dir / symlink_name
            
            try:
                # Create symlink
                os.symlink(mod_path, symlink_path)
                count += 1
            except FileExistsError:
                errors.append(f"Symlink already exists: {symlink_name}")
            except Exception as e:
                errors.append(f"Failed to create symlink for {mod.filename}: {e}")
        
        return count, errors
    
    def deactivate_all(self) -> int:
        """Deactivate all mods (remove all managed symlinks)"""
        return self.clear_managed_symlinks()
    
    def verify_mods(self, instance: Instance) -> List[str]:
        """
        Verify that all mods in an instance exist
        Returns list of missing mod filenames
        """
        missing = []
        for mod in instance.mods:
            if not Path(mod.path).exists():
                missing.append(mod.filename)
        return missing
    
    def detect_conflicts(self, instance: Instance) -> List[str]:
        """
        Detect potential mod conflicts
        Returns list of warnings
        """
        warnings = []
        
        # Check for multiple AI mods (common conflict)
        ai_keywords = ['ai', 'suspect', 'swat', 'officer']
        ai_mods = []
        
        for mod in instance.get_enabled_mods():
            mod_lower = mod.name.lower()
            if any(keyword in mod_lower for keyword in ai_keywords):
                ai_mods.append(mod.name)
        
        if len(ai_mods) > 1:
            warnings.append(
                f"Multiple AI-related mods detected: {', '.join(ai_mods)}. "
                "These may conflict."
            )
        
        # Check for duplicate functionality
        seen_names = {}
        for mod in instance.get_enabled_mods():
            # Remove version numbers and common suffixes for comparison
            base_name = mod.name.lower().split('_v')[0].split('-v')[0]
            
            if base_name in seen_names:
                warnings.append(
                    f"Similar mods detected: '{seen_names[base_name]}' and '{mod.name}'. "
                    "These may be duplicate versions."
                )
            else:
                seen_names[base_name] = mod.name
        
        return warnings
    
    def get_steam_launch_command(self) -> str:
        """Get the Steam launch command for Ready or Not"""
        # Steam App ID for Ready or Not
        return "steam steam://rungameid/1144200"
