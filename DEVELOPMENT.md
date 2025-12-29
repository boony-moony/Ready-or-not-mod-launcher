# Development Guide

## Project Structure

```
.
├── main.py              # Application entry point
├── models.py            # Data models (Instance, Mod, AppState)
├── mod_manager.py       # Symlink operations and game integration
├── widgets.py           # Qt GUI widgets
├── requirements.txt     # Python dependencies
├── run.sh              # Launch script
├── README.md           # User documentation
└── DEVELOPMENT.md      # This file
```

## Architecture

### Data Flow

1. **DataManager** (`models.py`)
   - Handles JSON persistence
   - Manages `~/.ron-modmgr/` directory structure
   - CRUD operations for instances

2. **ModManager** (`mod_manager.py`)
   - Detects Steam/Flatpak game paths
   - Creates/removes symlinks with `ronmgr_` prefix
   - Validates mods and detects conflicts

3. **MainWindow** (`main.py`)
   - Orchestrates UI and business logic
   - Handles user actions
   - Updates state

4. **Widgets** (`widgets.py`)
   - InstanceListWidget: Left panel
   - ModListWidget: Main panel
   - LogWidget: Operation logs

### Key Design Decisions

**Symlink Prefix**: All managed symlinks use `ronmgr_` prefix to:
- Avoid conflicts with user-created files
- Enable safe cleanup
- Make manager-created files visible

**Single Active Instance**: Only one instance can be active because:
- Game loads all `.pak` files in the directory
- Multiple active instances would conflict
- Explicit activation prevents user confusion

**Central Library**: Mods are stored in `~/.ron-modmgr/mods/` because:
- Avoids duplication across instances
- Simplifies mod sharing
- Separates mod storage from game directory

## Adding Features

### Adding a New Widget

1. Create widget class in `widgets.py`
2. Define signals for communication
3. Add to `MainWindow._init_ui()`
4. Connect signals to handler methods

### Adding Validation

Add checks in `ModManager.detect_conflicts()`:

```python
def detect_conflicts(self, instance: Instance) -> List[str]:
    warnings = []
    # Add your validation logic
    return warnings
```

### Supporting New Game Paths

Add detection in `ModManager._detect_game_path()`:

```python
def _detect_game_path(self) -> Optional[Path]:
    # Add new path detection logic
    pass
```

## Testing

### Manual Testing Checklist

- [ ] Create instance
- [ ] Add mods to instance
- [ ] Enable/disable mods in instance
- [ ] Activate instance (check symlinks)
- [ ] Deactivate instance (verify cleanup)
- [ ] Delete instance
- [ ] Launch game
- [ ] Handle missing game directory
- [ ] Handle missing mod files
- [ ] Detect mod conflicts

### Testing with Mock Data

Create test mods:

```bash
mkdir -p ~/.ron-modmgr/mods
touch ~/.ron-modmgr/mods/TestMod.pak
touch ~/.ron-modmgr/mods/AnotherMod.pak
```

### Symlink Verification

Check managed symlinks:

```bash
ls -la ~/.steam/steam/steamapps/compatdata/1144200/pfx/drive_c/users/steamuser/AppData/Local/ReadyOrNot/Saved/Paks/ | grep ronmgr_
```

## Building

### Single-File Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name ron-modmgr main.py
```

Output: `dist/ron-modmgr`

### AppImage (Advanced)

Requires `appimagetool`:

```bash
# Create AppDir structure
mkdir -p AppDir/usr/bin
cp dist/ron-modmgr AppDir/usr/bin/
cp ron-modmgr.desktop AppDir/
# Add icon...

# Build AppImage
appimagetool AppDir ron-modmgr.AppImage
```

## Debugging

### Enable Verbose Logging

Add to `main.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Data Files

```bash
cat ~/.ron-modmgr/state.json
cat ~/.ron-modmgr/instances/*/instance.json
```

### Common Issues

**"Game directory not found"**
- Verify Steam installation
- Check if game has been run at least once
- Manually check path existence

**Symlinks not working**
- Verify filesystem supports symlinks
- Check permissions
- Ensure prefix matches `DataManager.SYMLINK_PREFIX`

**Mods not loading in-game**
- Never use in-game mod menu on Linux (it's broken)
- Verify `.pak` files are valid
- Check Proton/Wine compatibility

## Contributing

1. Keep code modular
2. Use type hints
3. Document complex logic
4. Test on Arch Linux
5. Verify Proton compatibility

## Performance Notes

- JSON is sufficient for < 1000 mods
- Symlinks are instant (no file copying)
- UI updates are synchronous (acceptable for mod counts < 100)

## Future Enhancements

- [ ] Mod metadata (description, author, version)
- [ ] Conflict detection improvements
- [ ] Backup/restore instances
- [ ] Import instances from file
- [ ] Mod update checking
- [ ] Integration with mod repositories
- [ ] Custom game path configuration
- [ ] Mod load order management
