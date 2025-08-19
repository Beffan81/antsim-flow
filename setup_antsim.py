#!/usr/bin/env python3
"""
Setup script to install antsim dependencies and verify installation.
"""

import subprocess
import sys
from pathlib import Path

def install_requirements():
    """Install required packages for antsim."""
    requirements = [
        "pluggy>=1.0.0",           # Plugin system
        "pydantic>=2.0.0",         # Config validation  
        "numpy>=1.20.0",           # Pheromone engine
        "scipy",                   # Optional: KDTree optimization
        "pygame",                  # Optional: Rendering
        "PyYAML",                  # Optional: YAML config support
    ]
    
    print("Installing antsim dependencies...")
    for req in requirements:
        try:
            print(f"Installing {req}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", req])
            print(f"✓ {req} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠ Failed to install {req}: {e}")
            if req in ["scipy", "pygame", "PyYAML"]:
                print(f"  → {req} is optional, continuing...")
            else:
                print(f"  → {req} is required! Installation may fail.")
    
    print("\n✓ Dependency installation completed!")

def verify_antsim():
    """Verify antsim installation by running tests."""
    print("\nVerifying antsim installation...")
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Import test runner
        from antsim_test_runner import run_all_tests
        
        # Run tests
        success = run_all_tests()
        
        if success:
            print("\n🎉 antsim verification successful!")
            print("You can now run the simulation with:")
            print("  python -m antsim")
        else:
            print("\n❌ antsim verification failed!")
            print("Check the error messages above.")
            
        return success
        
    except Exception as e:
        print(f"\n❌ Verification error: {e}")
        return False

def main():
    """Main setup function."""
    print("antsim Setup Script")
    print("=" * 30)
    
    # Install dependencies
    install_requirements()
    
    # Verify installation
    success = verify_antsim()
    
    if success:
        print("\n🚀 antsim is ready to use!")
        print("\nExample usage:")
        print("  # Run demo simulation")
        print("  python -m antsim")
        print("")
        print("  # Run with custom config")
        print("  python -m antsim --bt config/my_behavior.yaml")
        print("")
        print("  # Start web backend")
        print("  python start_backend.py")
    else:
        print("\n⚠ Setup completed with issues. Check errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())