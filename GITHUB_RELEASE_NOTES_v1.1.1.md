# 🚀 AntSim Flow v1.1.1 - Enhanced Configuration

## 🎯 What's New

### ⚙️ Environment Variables Support
- **`ANTSIM_TICKS`**: Configure simulation duration (Default: 10,000 ticks)
- **Increased Default Duration**: Simulations now run 10,000 ticks instead of 100
- **Flexible Configuration**: No code changes needed for different simulation lengths

### 🔧 Usage Examples

```bash
# Standard simulation (10,000 ticks)
python start_backend.py

# Quick test (100 ticks)
ANTSIM_TICKS=100 python start_backend.py

# Extended simulation (50,000 ticks)
ANTSIM_TICKS=50000 python start_backend.py

# Combined with other variables
ANTSIM_TICKS=5000 ANTSIM_TICK_DELAY=0.05 python start_backend.py
```

## 📋 Technical Details

### Modified Files
- `antsim/app/main.py`: Added environment variable support for tick configuration

### New Configuration Options
- **ANTSIM_TICKS**: Controls simulation duration (integer, default: 10000)
- Backward compatible: existing functionality unchanged
- Logging: Shows configured tick count on startup

## 🔄 Migration Guide

### From v1.1.0 to v1.1.1:
- ✅ **No Breaking Changes**: All existing APIs work unchanged
- ✅ **Backward Compatible**: Simulations automatically use better defaults
- ✅ **Optional Configuration**: Environment variables are optional

### Behavior Changes:
- 📈 **Longer Simulations**: Default increased from 100 to 10,000 ticks
- 🔧 **Configurable Duration**: Tick count now adjustable via environment variable

## 📊 Impact

### Developer Experience
- 🎯 **Better Testing**: Longer simulations show more complex behaviors
- ⚡ **Flexible Duration**: Easy adjustment for different testing scenarios  
- 🔧 **No Code Changes**: Configure via environment variables only

### Use Cases Enabled
- 🧪 **Development**: Longer simulations for behavior analysis
- ⚡ **Quick Testing**: Short runs for rapid iteration
- 📊 **Performance Testing**: Extended runs for stability analysis
- 🎯 **Demos**: Configurable length for presentations

## 🎮 Recommended Workflows

### Development
```bash
# Standard development (good balance)
python start_backend.py
```

### Quick Testing
```bash
# Fast iteration
ANTSIM_TICKS=100 python start_backend.py
```

### Extended Analysis
```bash
# Long-term behavior observation
ANTSIM_TICKS=25000 python start_backend.py
```

## 👥 Contributors
- Enhanced configuration system
- Improved simulation duration management
- Better developer experience

---

**Full Changelog**: [v1.1.0...v1.1.1](https://github.com/your-repo/antsim-flow/compare/v1.1.0...v1.1.1)

**Download**: [Source code (zip)](https://github.com/your-repo/antsim-flow/archive/refs/tags/v1.1.1.zip) | [Source code (tar.gz)](https://github.com/your-repo/antsim-flow/archive/refs/tags/v1.1.1.tar.gz)