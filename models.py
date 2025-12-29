"""
Data models for Ready or Not Mod Manager
"""
import json
import zipfile
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class Mod:
    """Represents a mod in the library"""
    name: str  # Filename without extension
    filename: str  # Full filename with .pak
    path: str  # Absolute path to .pak file
    size: int  # File size in bytes
    enabled: bool = True  # Whether mod is enabled in instance
    
    def to_dict(self):
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'Mod':
        return Mod(**data)


@dataclass
class Instance:
    """Represents a mod instance (profile)"""
    name: str
    mods: List[Mod] = field(default_factory=list)
    created: str = ""  # ISO timestamp
    
    def to_dict(self):
        return {
            'name': self.name,
            'mods': [mod.to_dict() for mod in self.mods],
            'created': self.created
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Instance':
        instance = Instance(
            name=data['name'],
            created=data.get('created', '')
        )
        instance.mods = [Mod.from_dict(mod) for mod in data.get('mods', [])]
        return instance
    
    def add_mod(self, mod: Mod):
        """Add a mod to this instance"""
        # Check if mod already exists
        for existing in self.mods:
            if existing.filename == mod.filename:
                return False
        self.mods.append(mod)
        return True
    
    def remove_mod(self, filename: str):
        """Remove a mod from this instance"""
        self.mods = [mod for mod in self.mods if mod.filename != filename]
    
    def get_enabled_mods(self) -> List[Mod]:
        """Get list of enabled mods"""
        return [mod for mod in self.mods if mod.enabled]


@dataclass
class AppState:
    """Application state"""
    active_instance: Optional[str] = None  # Name of active instance
    steam_path: Optional[str] = None  # Detected Steam path
    
    def to_dict(self):
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'AppState':
        return AppState(**data)


class DataManager:
    """Manages application data and persistence"""
    
    SYMLINK_PREFIX = "ronmgr_"
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.mods_dir = data_dir / "mods"
        self.instances_dir = data_dir / "instances"
        self.state_file = data_dir / "state.json"
        
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Create necessary directories"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.mods_dir.mkdir(exist_ok=True)
        self.instances_dir.mkdir(exist_ok=True)
    
    def load_state(self) -> AppState:
        """Load application state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return AppState.from_dict(data)
            except Exception as e:
                print(f"Error loading state: {e}")
        return AppState()
    
    def save_state(self, state: AppState):
        """Save application state"""
        with open(self.state_file, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)
    
    def load_instance(self, name: str) -> Optional[Instance]:
        """Load an instance from disk"""
        instance_file = self.instances_dir / name / "instance.json"
        if not instance_file.exists():
            return None
        
        try:
            with open(instance_file, 'r') as f:
                data = json.load(f)
            return Instance.from_dict(data)
        except Exception as e:
            print(f"Error loading instance {name}: {e}")
            return None
    
    def save_instance(self, instance: Instance):
        """Save an instance to disk"""
        instance_dir = self.instances_dir / instance.name
        instance_dir.mkdir(exist_ok=True)
        
        instance_file = instance_dir / "instance.json"
        with open(instance_file, 'w') as f:
            json.dump(instance.to_dict(), f, indent=2)
    
    def delete_instance(self, name: str):
        """Delete an instance"""
        instance_dir = self.instances_dir / name
        if instance_dir.exists():
            import shutil
            shutil.rmtree(instance_dir)
    
    def list_instances(self) -> List[str]:
        """List all instance names"""
        if not self.instances_dir.exists():
            return []
        
        instances = []
        for item in self.instances_dir.iterdir():
            if item.is_dir() and (item / "instance.json").exists():
                instances.append(item.name)
        return sorted(instances)
    
    def import_mod(self, pak_file: Path) -> Optional[Mod]:
        """Import a mod .pak file into the library"""
        if not pak_file.exists() or pak_file.suffix.lower() != '.pak':
            return None
        
        # Copy to library
        dest = self.mods_dir / pak_file.name
        if dest.exists():
            # File already exists
            return None
        
        import shutil
        shutil.copy2(pak_file, dest)
        
        # Create Mod object
        mod = Mod(
            name=pak_file.stem,
            filename=pak_file.name,
            path=str(dest.absolute()),
            size=dest.stat().st_size
        )
        return mod
    
    def _extract_archive(self, archive_path: Path) -> List[Path]:
        """
        Extract an archive file and return list of extracted .pak files.
        Supports zip, 7z, and rar formats.
        """
        extracted_paks = []
        temp_dir = None
        
        try:
            temp_dir = tempfile.mkdtemp()
            temp_path = Path(temp_dir)
            
            suffix = archive_path.suffix.lower()
            
            if suffix == '.zip':
                # Use built-in zipfile
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
            
            elif suffix == '.7z':
                # Use 7z command
                result = subprocess.run(
                    ['7z', 'x', str(archive_path), f'-o{temp_path}'],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise Exception(f"7z extraction failed: {result.stderr}")
            
            elif suffix == '.rar':
                # Try unrar command
                result = subprocess.run(
                    ['unrar', 'x', str(archive_path), str(temp_path)],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise Exception(f"unrar extraction failed: {result.stderr}")
            
            # Find all .pak files in extracted content
            for pak_file in temp_path.rglob('*.pak'):
                extracted_paks.append(pak_file)
            
            return extracted_paks
        
        except FileNotFoundError as e:
            raise Exception(f"Extraction tool not found: {e}")
        except Exception as e:
            raise e
        finally:
            # Note: temp_dir is left for caller to clean up after importing
            pass
    
    def import_archive(self, archive_path: Path) -> tuple[List[Mod], Optional[str]]:
        """
        Import an archive file, extract .pak files, and add them to the library.
        Returns (list of imported mods, error message if any)
        """
        if not archive_path.exists():
            return [], "Archive file not found"
        
        suffix = archive_path.suffix.lower()
        if suffix not in ['.zip', '.7z', '.rar']:
            return [], f"Unsupported archive format: {suffix}"
        
        try:
            extracted_paks = self._extract_archive(archive_path)
            
            if not extracted_paks:
                return [], "No .pak files found in archive"
            
            imported_mods = []
            for pak_file in extracted_paks:
                mod = self.import_mod(pak_file)
                if mod:
                    imported_mods.append(mod)
            
            return imported_mods, None
        
        except Exception as e:
            return [], str(e)

    
    def list_library_mods(self) -> List[Mod]:
        """List all mods in the library"""
        mods = []
        for pak_file in self.mods_dir.glob("*.pak"):
            mod = Mod(
                name=pak_file.stem,
                filename=pak_file.name,
                path=str(pak_file.absolute()),
                size=pak_file.stat().st_size
            )
            mods.append(mod)
        return sorted(mods, key=lambda m: m.name.lower())
