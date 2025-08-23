#!/usr/bin/env python3
"""
Minimal test script to diagnose pygame display issues.
Run this to check if pygame can initialize in your environment.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def test_display_env():
    """Check display-related environment variables."""
    log.info("=== Display Environment Check ===")
    display = os.environ.get("DISPLAY")
    sdl_driver = os.environ.get("SDL_VIDEODRIVER")
    
    log.info("DISPLAY=%s", display)
    log.info("SDL_VIDEODRIVER=%s", sdl_driver)
    
    if not display and os.name != "nt":
        log.warning("DISPLAY not set - this may cause pygame to fail")
        log.info("Try: export DISPLAY=:0")
        
    # Check if we can query display info (Linux/Unix)
    if os.name != "nt":
        try:
            import subprocess
            result = subprocess.run(["xdpyinfo"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                log.info("xdpyinfo successful - display seems available")
            else:
                log.warning("xdpyinfo failed: %s", result.stderr)
        except Exception as e:
            log.warning("Could not run xdpyinfo: %s", e)

def test_pygame_import():
    """Test pygame import."""
    log.info("=== Pygame Import Test ===")
    try:
        import pygame
        log.info("pygame import successful: version %s", pygame.version.ver)
        return True
    except Exception as e:
        log.error("pygame import failed: %s", e)
        return False

def test_pygame_init():
    """Test pygame initialization."""
    log.info("=== Pygame Init Test ===")
    try:
        import pygame
        pygame.init()
        log.info("pygame.init() successful")
        return True
    except Exception as e:
        log.error("pygame.init() failed: %s", e)
        return False

def test_pygame_display():
    """Test pygame display creation."""
    log.info("=== Pygame Display Test ===")
    try:
        import pygame
        
        # Test with current settings
        log.info("Attempting display creation with current settings...")
        screen = pygame.display.set_mode((800, 600))
        if screen is None:
            log.error("pygame.display.set_mode returned None")
            return False
        
        log.info("Display created successfully: %dx%d", screen.get_width(), screen.get_height())
        pygame.display.set_caption("Test Window")
        
        # Quick test draw
        screen.fill((100, 150, 200))
        pygame.display.flip()
        
        log.info("Display test successful - keeping window open for 3 seconds")
        import time
        time.sleep(3)
        
        pygame.quit()
        return True
        
    except Exception as e:
        log.error("pygame display test failed: %s", e)
        
        # Try headless mode
        log.info("Trying headless mode with SDL_VIDEODRIVER=dummy")
        try:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.quit()  # Clean up previous init
            pygame.init()
            screen = pygame.display.set_mode((800, 600))
            log.info("Headless mode successful")
            pygame.quit()
            return True
        except Exception as e2:
            log.error("Headless mode also failed: %s", e2)
            return False

def main():
    log.info("Starting pygame display diagnostics...")
    
    test_display_env()
    
    if not test_pygame_import():
        log.error("Cannot proceed - pygame not available")
        sys.exit(1)
    
    if not test_pygame_init():
        log.error("Cannot proceed - pygame init failed")
        sys.exit(1)
    
    if not test_pygame_display():
        log.error("Display test failed")
        log.info("Recommendations:")
        log.info("1. For headless environments: export SDL_VIDEODRIVER=dummy")
        log.info("2. For X11 forwarding: export DISPLAY=:0 and ensure X11 is configured")
        log.info("3. For Codespaces: Try opening the simulation in the browser preview")
        sys.exit(1)
    
    log.info("All tests passed - pygame should work with antsim")

if __name__ == "__main__":
    main()