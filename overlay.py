"""Screen-center crosshair overlay implemented as a true Win32 layered window.

Why not Tkinter?  Tk's "-transparentcolor" (color-key) approach is unreliable
on modern Windows 11 + Tk 9 builds: it can render a solid black rectangle over
other windows.  This implementation instead uses UpdateLayeredWindow with
per-pixel alpha, which is the canonical, flicker-free way to build overlays:

  * per-pixel transparency (no color key)      -> never shows a black box
  * WS_EX_NOACTIVATE                           -> never steals keyboard focus
  * WS_EX_TRANSPARENT                          -> clicks pass through to the game
  * WS_EX_TOOLWINDOW                           -> hidden from Alt+Tab
  * anti-aliased PIL rendering (via crosshair_render)
  * opacity support (premultiplied alpha)
  * multi-monitor aware: follows the foreground (game) window
  * auto-hides while the studio window itself is focused
"""
import ctypes
from ctypes import wintypes

import numpy as np
from PIL import Image
import win32api
import win32con
import win32gui

from config import CrosshairConfig
from crosshair_render import render_crosshair

_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32

ULW_ALPHA = 0x00000002
AC_SRC_ALPHA = 0x01
MONITOR_DEFAULTTONEAREST = 2
POLL_MS = 150

WIN_SIZE = 200  # overlay window size, px


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _SIZE(ctypes.Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


class _BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", wintypes.BYTE), ("BlendFlags", wintypes.BYTE),
                ("SourceConstantAlpha", wintypes.BYTE), ("AlphaFormat", wintypes.BYTE)]


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]


_user32.UpdateLayeredWindow.restype = wintypes.BOOL
_user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(_POINT), ctypes.POINTER(_SIZE),
    wintypes.HDC, ctypes.POINTER(_POINT), wintypes.COLORREF,
    ctypes.POINTER(_BLENDFUNCTION), wintypes.DWORD,
]
_gdi32.CreateDIBSection.restype = wintypes.HBITMAP
_gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
]
# 64-bit handles must not be truncated to c_int
_gdi32.SelectObject.restype = wintypes.HANDLE
_gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
_gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
_gdi32.CreateCompatibleDC.restype = wintypes.HDC
_gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
_gdi32.DeleteDC.argtypes = [wintypes.HDC]
_user32.GetDC.restype = wintypes.HDC
_user32.GetDC.argtypes = [wintypes.HWND]
_user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]

_CLASS_NAME = "CrosshairStudioOverlayWindow"
_class_registered = False


def _register_class():
    global _class_registered
    if _class_registered:
        return
    wc = win32gui.WNDCLASS()
    wc.hInstance = win32gui.GetModuleHandle(None)
    wc.lpszClassName = _CLASS_NAME
    wc.lpfnWndProc = win32gui.DefWindowProc
    wc.hbrBackground = win32gui.GetStockObject(win32con.BLACK_BRUSH)
    try:
        win32gui.RegisterClass(wc)
    except win32gui.error:
        pass  # already registered in this process
    _class_registered = True


class CrosshairOverlay:
    """Pure-Win32 per-pixel-alpha overlay window centered on the target monitor."""

    def __init__(self, root, config: CrosshairConfig):
        self._root = root            # Tk root, only used to schedule the poll loop
        self.config = config
        self.enabled = True          # master toggle (set via set_visible)
        self.offset_x = 0
        self.offset_y = 0

        self._visible = False
        self._after_id = None
        self._fg_last = None
        self._mon_last = None
        self._img = None             # last rendered RGBA PIL image
        self._bgra = None            # last premultiplied BGRA bytes
        self._destroyed = False

        _register_class()
        hinst = win32gui.GetModuleHandle(None)
        ex_style = (win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT |
                    win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE)
        self.hwnd = win32gui.CreateWindowEx(
            ex_style, _CLASS_NAME, "CrosshairOverlayWindow",
            win32con.WS_POPUP, 0, 0, WIN_SIZE, WIN_SIZE,
            0, 0, hinst, None,
        )
        self.redraw()
        self._poll()

    # ------------------------------------------------------------------ rendering

    def redraw(self):
        """Re-render the crosshair from the current config."""
        if self._destroyed:
            return
        self._img = render_crosshair(self.config, canvas=WIN_SIZE, bg=None)
        arr = np.asarray(self._img, dtype=np.float32)
        a = arr[..., 3:4] / 255.0
        arr[..., :3] = arr[..., :3] * a  # premultiply for AC_SRC_ALPHA
        self._bgra = np.ascontiguousarray(arr[..., [2, 1, 0, 3]].astype(np.uint8)).tobytes()
        if self._visible:
            self._blit()

    def _blit(self, x=None, y=None):
        """Push the cached bitmap to the screen at (x, y); default = current pos."""
        if self._destroyed or self._bgra is None:
            return
        if x is None or y is None:
            x, y = self._center_pos(self._mon_last)
        w = h = WIN_SIZE
        bmi = _BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down DIB
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0  # BI_RGB
        bmi.biSizeImage = w * h * 4

        bits = ctypes.c_void_p()
        hdc_screen = _user32.GetDC(0)
        try:
            hbmp = _gdi32.CreateDIBSection(
                hdc_screen, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
            if not hbmp or not bits.value:
                return
            ctypes.memmove(bits.value, self._bgra, len(self._bgra))
            hdc_mem = _gdi32.CreateCompatibleDC(hdc_screen)
            old = _gdi32.SelectObject(hdc_mem, hbmp)
            blend = _BLENDFUNCTION(0, 0, 255, AC_SRC_ALPHA)
            pt_dst = _POINT(int(x), int(y))
            pt_src = _POINT(0, 0)
            sz = _SIZE(w, h)
            _user32.UpdateLayeredWindow(
                self.hwnd, hdc_screen, ctypes.byref(pt_dst), ctypes.byref(sz),
                hdc_mem, ctypes.byref(pt_src), 0, ctypes.byref(blend), ULW_ALPHA)
            _gdi32.SelectObject(hdc_mem, old)
            _gdi32.DeleteDC(hdc_mem)
            _gdi32.DeleteObject(hbmp)
        finally:
            _user32.ReleaseDC(0, hdc_screen)

    # ------------------------------------------------------------------ positioning

    def _center_pos(self, mon_rect):
        if mon_rect:
            l, t, r, b = mon_rect
        else:
            l, t, r, b = (0, 0,
                          win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
                          win32api.GetSystemMetrics(win32con.SM_CYSCREEN))
        cx = (l + r) // 2 + self.offset_x
        cy = (t + b) // 2 + self.offset_y
        return cx - WIN_SIZE // 2, cy - WIN_SIZE // 2

    @staticmethod
    def _monitor_of(hwnd_fg):
        try:
            if hwnd_fg:
                hmon = win32api.MonitorFromWindow(hwnd_fg, MONITOR_DEFAULTTONEAREST)
            else:
                hmon = win32api.MonitorFromPoint(win32api.GetCursorPos(), MONITOR_DEFAULTTONEAREST)
            return win32gui.GetMonitorInfo(hmon)["Monitor"]
        except Exception:
            return None

    @staticmethod
    def _foreground_is_own():
        fg = win32gui.GetForegroundWindow()
        if not fg:
            return False, None
        # A hidden foreground window (e.g. a withdrawn Tk root that briefly
        # grabbed focus during startup) must not suppress the overlay.
        if not win32gui.IsWindowVisible(fg):
            return False, fg
        try:
            _, pid = win32gui.GetWindowThreadProcessId(fg)
            return pid == win32api.GetCurrentProcessId(), fg
        except Exception:
            return False, fg

    # ------------------------------------------------------------------ public API

    def set_offset(self, off_x: int, off_y: int):
        self.offset_x = int(off_x)
        self.offset_y = int(off_y)
        if self._visible:
            self._blit()

    def update_config(self, config: CrosshairConfig):
        self.config = config
        self.redraw()

    def set_visible(self, visible: bool):
        self.enabled = bool(visible)
        self._apply_visibility()

    def destroy(self):
        self._destroyed = True
        if self._after_id is not None:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            if self.hwnd:
                win32gui.DestroyWindow(self.hwnd)
        except Exception:
            pass

    # ------------------------------------------------------------------ polling

    def _apply_visibility(self):
        if self._destroyed:
            return
        own_fg, fg = self._foreground_is_own()
        want = self.enabled and not own_fg
        if want:
            mon = self._monitor_of(fg)
            need_move = (mon != self._mon_last) or (fg != self._fg_last)
            self._fg_last, self._mon_last = fg, mon
            if not self._visible:
                self._visible = True
                self._blit()
                win32gui.SetWindowPos(
                    self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                    win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW)
            else:
                if need_move:
                    self._blit()
                # some games steal topmost; reassert cheaply
                win32gui.SetWindowPos(
                    self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        elif self._visible:
            self._visible = False
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def _poll(self):
        if self._destroyed:
            return
        try:
            self._apply_visibility()
        except Exception:
            pass
        try:
            self._after_id = self._root.after(POLL_MS, self._poll)
        except Exception:
            self._after_id = None
