"""Launch CrosshairStudioPro.exe, verify it stays alive, then close it.

Onefile builds extract to a temp dir first, so we allow extra startup time.
Checks:
  1. process starts and does not crash within the observation window
  2. settings.json can be written next to the exe (frozen APP_DIR fix)
"""
import subprocess
import sys
import time
import os
import json

APP_DIR = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(APP_DIR, "dist", "CrosshairStudioPro.exe")

def main():
    if not os.path.exists(EXE):
        print("FAIL exe not found:", EXE)
        return 1

    size_mb = os.path.getsize(EXE) / (1024 * 1024)
    print(f"exe found: {size_mb:.1f} MB")

    # Clean stale settings so we test the default (en) path
    st_path = os.path.join(APP_DIR, "dist", "settings.json")
    if os.path.exists(st_path):
        os.remove(st_path)

    proc = subprocess.Popen([EXE])
    print("launched, waiting for startup (onefile extraction)...")

    # Poll: give it plenty of time to extract + open the GUI
    deadline = time.time() + 25
    crashed = None
    while time.time() < deadline:
        rc = proc.poll()
        if rc is not None:
            crashed = rc
            break
        time.sleep(0.5)

    if crashed is not None:
        print(f"FAIL exe exited early, code={crashed}")
        return 1

    print("OK exe still running after observation window")

    # The GUI writes settings.json on language change / save; simulate the
    # frozen-path rule: it must resolve next to the exe, not the temp dir.
    sys.frozen = True
    real_exe = sys.executable
    try:
        sys.executable = EXE
        # re-import logic from i18n in frozen mode
        import importlib
        if "i18n" in sys.modules:
            importlib.reload(sys.modules["i18n"])
        else:
            import i18n
        expected_dir = os.path.dirname(os.path.abspath(EXE))
        print("i18n.APP_DIR (frozen):", i18n.APP_DIR)
        if os.path.abspath(i18n.APP_DIR) != os.path.abspath(expected_dir):
            print("FAIL APP_DIR not next to exe")
            return 1
        print("OK settings.json resolves next to the exe")

        i18n.save_settings()
        if os.path.exists(st_path):
            with open(st_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print("OK settings.json written beside exe:", data)
        else:
            print("FAIL settings.json was not written beside exe")
            return 1
    finally:
        sys.executable = real_exe
        if hasattr(sys, "frozen"):
            del sys.frozen

    # Close it cleanly
    proc.terminate()
    try:
        proc.wait(timeout=10)
        print("OK exe closed cleanly")
    except subprocess.TimeoutExpired:
        proc.kill()
        print("WARN exe had to be force-killed")

    if os.path.exists(st_path):
        os.remove(st_path)
    print("ALL EXE TESTS PASSED")
    return 0

if __name__ == "__main__":
    code = main()
    print("EXE_EXIT=", code)
    sys.exit(code)
