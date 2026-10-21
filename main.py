import os
import sys
import re
import ctypes
import json
import tkinter as tk
from ctypes import wintypes
from tkinter import filedialog, messagebox

# 1. High-DPI Awareness for Windows (Solves scaling & centering on 125%/150% displays)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import customtkinter as ctk
from PIL import Image, ImageTk

import i18n
from config import CrosshairConfig, PRESETS, VALID_STYLES, _HEX_RE
from overlay import CrosshairOverlay
from analyzer import analyze_crosshair_image
from crosshair_render import render_crosshair

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PREVIEW_PX = 220

STYLE_LABEL_KEYS = {
    "style_cross": "cross",
    "style_dot": "dot",
    "style_cross_dot": "cross_dot",
    "style_circle": "circle",
    "style_t": "t_shape",
}

# ---------------------------------------------------------------------------
# Global hotkey (F8) via RegisterHotKey + Tk WndProc subclass.
# Falls back to GetAsyncKeyState polling if registration is not possible.
# ---------------------------------------------------------------------------
WM_HOTKEY = 0x0312
HOTKEY_ID = 0x4353
VK_F8 = 0x77
_LRESULT = ctypes.c_ssize_t
_WNDPROC = ctypes.WINFUNCTYPE(_LRESULT, wintypes.HWND, ctypes.c_uint,
                              wintypes.WPARAM, wintypes.LPARAM)
_user32 = ctypes.windll.user32
_user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
_user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
_user32.CallWindowProcW.restype = _LRESULT
_user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, ctypes.c_uint,
                                    wintypes.WPARAM, wintypes.LPARAM]
_user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
_user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]


class GlobalHotkey:
    """Fires `callback` on F8 while the app is running, even during a game."""

    def __init__(self, root, callback, vk=VK_F8, modifiers=0):
        self.root = root
        self.callback = callback
        self.vk = vk
        self.modifiers = modifiers
        self.hwnd = None
        self._old_proc = None
        self._cb_ref = None
        self._fallback = False
        self._down_last = False
        self._install()

    def _install(self):
        try:
            self.hwnd = int(self.root.wm_frame(), 16)
            def _proc(hwnd, msg, wp, lp):
                if msg == WM_HOTKEY and wp == HOTKEY_ID:
                    try:
                        self.root.after(0, self.callback)
                    except Exception:
                        pass
                    return 0
                return _user32.CallWindowProcW(self._old_proc, hwnd, msg, wp, lp)
            self._cb_ref = _WNDPROC(_proc)
            old = _user32.SetWindowLongPtrW(self.hwnd, -4,  # GWL_WNDPROC
                                            ctypes.cast(self._cb_ref, ctypes.c_void_p).value)
            if not old:
                raise ctypes.get_last_error()
            self._old_proc = old
            if not _user32.RegisterHotKey(self.hwnd, HOTKEY_ID, self.modifiers, self.vk):
                raise ctypes.get_last_error()
        except Exception:
            self._fallback = True

    def poll_fallback(self):
        if not self._fallback:
            return
        try:
            down = bool(_user32.GetAsyncKeyState(self.vk) & 0x8000)
        except Exception:
            return
        if down and not self._down_last:
            try:
                self.callback()
            except Exception:
                pass
        self._down_last = down

    def unregister(self):
        if self._fallback or self.hwnd is None:
            return
        try:
            _user32.UnregisterHotKey(self.hwnd, HOTKEY_ID)
        except Exception:
            pass
        if self._old_proc:
            try:
                _user32.SetWindowLongPtrW(self.hwnd, -4, self._old_proc)
            except Exception:
                pass


class CrosshairStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Crosshair Studio Pro")
        self.geometry("940x740")
        self.minsize(880, 660)

        # Default config: Cross + Center Dot
        self.config = CrosshairConfig(
            enabled=True,
            style="cross_dot",
            size=8,
            thickness=2,
            gap=4,
            dot_size=3,
            color="#00FF66",
            outline=True,
            outline_thickness=1,
            opacity=1.0,
        )

        self.offset_x = 0
        self.offset_y = 0

        # Overlay window (pure Win32 layered window, no black box)
        self.overlay = CrosshairOverlay(self, self.config)

        self._build_ui()
        self.update_preview()

        # Global F8 toggle — works even while a game is focused
        self.hotkey = GlobalHotkey(self, self.toggle_crosshair)

        # Rebuild the UI when the language changes
        i18n.on_change(self._on_language_change)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Destroy>", self._on_destroy, add="+")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def on_close(self):
        try:
            self.hotkey.unregister()
        except Exception:
            pass
        try:
            self.overlay.destroy()
        except Exception:
            pass
        self.destroy()

    def _on_destroy(self, event):
        if event.widget is self:
            try:
                self.overlay.destroy()
            except Exception:
                pass

    def _on_language_change(self):
        """Rebuild all widget texts in the new language, keeping current config."""
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Destroy and recreate every widget; keeps config, offsets, hotkey."""
        cfg = self.config
        for child in self.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass
        self.config = cfg
        self._build_ui()
        self.sync_ui_to_config()
        self.update_preview()

    def toggle_crosshair(self):
        new_val = not self.overlay.enabled
        self.toggle_var.set(new_val)
        self.on_toggle_switch()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. TOP HEADER BAR
        top_bar = ctk.CTkFrame(self, height=70, corner_radius=10, fg_color="#18181B")
        top_bar.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        top_bar.grid_columnconfigure(2, weight=1)

        self.title_label = ctk.CTkLabel(
            top_bar,
            text=i18n.t("app_title"),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.hotkey_hint = ctk.CTkLabel(
            top_bar,
            text=i18n.t("hotkey_hint"),
            font=ctk.CTkFont(size=12),
            text_color="#71717A"
        )
        self.hotkey_hint.grid(row=0, column=1, pady=15, sticky="w")

        # Language selector
        lang_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        lang_frame.grid(row=0, column=3, padx=(0, 10), pady=15, sticky="e")
        ctk.CTkLabel(lang_frame, text=i18n.t("lang_label"),
                     font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=(0, 6))
        self.lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=[i18n.lang_label(c) for c in i18n.LANG_ORDER],
            width=110,
            command=self.on_language_select
        )
        self.lang_menu.set(i18n.lang_label())
        self.lang_menu.grid(row=0, column=1)

        self.toggle_var = ctk.BooleanVar(value=self.overlay.enabled)
        self.toggle_switch = ctk.CTkSwitch(
            top_bar,
            text=i18n.t("master_toggle"),
            font=ctk.CTkFont(size=14, weight="bold"),
            variable=self.toggle_var,
            command=self.on_toggle_switch,
            progress_color="#10B981"
        )
        self.toggle_switch.grid(row=0, column=4, padx=20, pady=15, sticky="e")

        # 2. MAIN BODY (Left: Tabs, Right: Live Preview)
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=3)
        content_frame.grid_columnconfigure(1, weight=2)
        content_frame.grid_rowconfigure(0, weight=1)

        # LEFT: Tabview
        self.tabs = ctk.CTkTabview(content_frame, corner_radius=10)
        self.tabs.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")

        self.tab_designer = self.tabs.add(i18n.t("tab_designer"))
        self.tab_analyzer = self.tabs.add(i18n.t("tab_analyzer"))
        self.tab_presets = self.tabs.add(i18n.t("tab_presets"))

        self._build_designer_tab()
        self._build_analyzer_tab()
        self._build_presets_tab()

        # RIGHT: Live Preview Panel
        preview_panel = ctk.CTkFrame(content_frame, corner_radius=10, fg_color="#18181B")
        preview_panel.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        preview_panel.grid_rowconfigure(1, weight=1)
        preview_panel.grid_columnconfigure(0, weight=1)

        prev_title = ctk.CTkLabel(
            preview_panel,
            text=i18n.t("preview_title"),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#A1A1AA"
        )
        prev_title.grid(row=0, column=0, padx=15, pady=(15, 5))

        self.preview_canvas = tk.Canvas(
            preview_panel,
            width=PREVIEW_PX,
            height=PREVIEW_PX,
            bg="#09090B",
            highlightthickness=2,
            highlightbackground="#27272A"
        )
        self.preview_canvas.grid(row=1, column=0, padx=20, pady=10)
        self._preview_imgtk = None

        # Quick preset buttons under preview
        quick_frame = ctk.CTkFrame(preview_panel, fg_color="transparent")
        quick_frame.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="ew")
        quick_frame.grid_columnconfigure((0, 1), weight=1)

        awp_btn = ctk.CTkButton(
            quick_frame,
            text=i18n.t("quick_awp"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=lambda: self.load_preset("AWP Red Sniper Dot")
        )
        awp_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        val_btn = ctk.CTkButton(
            quick_frame,
            text=i18n.t("quick_valorant"),
            fg_color="#0891B2",
            hover_color="#0E7490",
            command=lambda: self.load_preset("Valorant Cyan Pro")
        )
        val_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    def on_language_select(self, label):
        i18n.set_language(i18n.code_for_label(label))  # triggers _on_language_change

    # ------------------------------------------------------------------
    # TAB 1: DESIGNER
    # ------------------------------------------------------------------
    def _build_designer_tab(self):
        f = self.tab_designer
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text=i18n.t("lbl_style"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=6, sticky="w")
        style_labels = [i18n.t(k) for k in STYLE_LABEL_KEYS]
        self.style_menu = ctk.CTkSegmentedButton(
            f,
            values=style_labels,
            command=self.on_style_change
        )
        self.style_menu.grid(row=0, column=1, padx=10, pady=6, sticky="ew")

        ctk.CTkLabel(f, text=i18n.t("lbl_size")).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.size_slider = ctk.CTkSlider(f, from_=0, to=60, number_of_steps=60, command=self.on_slider_change)
        self.size_slider.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(f, text=i18n.t("lbl_thickness")).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.thick_slider = ctk.CTkSlider(f, from_=1, to=10, number_of_steps=9, command=self.on_slider_change)
        self.thick_slider.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(f, text=i18n.t("lbl_gap")).grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.gap_slider = ctk.CTkSlider(f, from_=0, to=40, number_of_steps=40, command=self.on_slider_change)
        self.gap_slider.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(f, text=i18n.t("lbl_dot_size")).grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.dot_slider = ctk.CTkSlider(f, from_=1, to=12, number_of_steps=11, command=self.on_slider_change)
        self.dot_slider.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(f, text=i18n.t("lbl_opacity")).grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.opacity_slider = ctk.CTkSlider(f, from_=0.2, to=1.0, number_of_steps=8, command=self.on_opacity_change)
        self.opacity_slider.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(f, text=i18n.t("lbl_colors")).grid(row=6, column=0, padx=10, pady=6, sticky="w")
        color_frame = ctk.CTkFrame(f, fg_color="transparent")
        color_frame.grid(row=6, column=1, padx=10, pady=6, sticky="w")

        colors = [
            ("#00FF66", "Yashil"),
            ("#FF1E1E", "Qizil"),
            ("#00FFFF", "Moviy"),
            ("#FFE600", "Sariq"),
            ("#FFFFFF", "Oq"),
            ("#BF00FF", "Binafsha")
        ]
        for idx, (col_hex, name) in enumerate(colors):
            b = ctk.CTkButton(
                color_frame,
                text="",
                width=30,
                height=30,
                corner_radius=15,
                fg_color=col_hex,
                hover_color=col_hex,
                command=lambda c=col_hex: self.set_color(c)
            )
            b.grid(row=0, column=idx, padx=4, pady=2)

        ctk.CTkLabel(f, text=i18n.t("lbl_hex")).grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.hex_entry = ctk.CTkEntry(f, width=130)
        self.hex_entry.insert(0, self.config.color)
        self.hex_entry.grid(row=7, column=1, padx=10, pady=5, sticky="w")
        self.hex_entry.bind("<Return>", lambda e: self.on_hex_enter())
        self.hex_entry.bind("<FocusOut>", lambda e: self.on_hex_enter(silent=True))

        self.outline_var = ctk.BooleanVar(value=self.config.outline)
        self.outline_cb = ctk.CTkCheckBox(
            f,
            text=i18n.t("cb_outline"),
            variable=self.outline_var,
            command=self.on_outline_toggle
        )
        self.outline_cb.grid(row=8, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(f, text=i18n.t("lbl_offset")).grid(row=9, column=0, padx=10, pady=5, sticky="w")
        offset_frame = ctk.CTkFrame(f, fg_color="transparent")
        offset_frame.grid(row=9, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(offset_frame, text="X:").grid(row=0, column=0, padx=2)
        self.off_x_slider = ctk.CTkSlider(offset_frame, from_=-50, to=50, width=110, command=self.on_offset_change)
        self.off_x_slider.grid(row=0, column=1, padx=4)

        ctk.CTkLabel(offset_frame, text="Y:").grid(row=0, column=2, padx=2)
        self.off_y_slider = ctk.CTkSlider(offset_frame, from_=-50, to=50, width=110, command=self.on_offset_change)
        self.off_y_slider.grid(row=0, column=3, padx=4)

        reset_pos_btn = ctk.CTkButton(offset_frame, text=i18n.t("btn_reset"), width=60, height=24, command=self.reset_offset)
        reset_pos_btn.grid(row=0, column=4, padx=6)

    def on_offset_change(self, _=None):
        self.offset_x = int(self.off_x_slider.get())
        self.offset_y = int(self.off_y_slider.get())
        self.overlay.set_offset(self.offset_x, self.offset_y)

    def reset_offset(self):
        self.off_x_slider.set(0)
        self.off_y_slider.set(0)
        self.offset_x = 0
        self.offset_y = 0
        self.overlay.set_offset(0, 0)

    # ------------------------------------------------------------------
    # TAB 2: IMAGE ANALYZER
    # ------------------------------------------------------------------
    def _build_analyzer_tab(self):
        f = self.tab_analyzer
        f.grid_columnconfigure(0, weight=1)

        intro = ctk.CTkLabel(
            f,
            text=i18n.t("analyzer_intro"),
            font=ctk.CTkFont(size=13),
            text_color="#A1A1AA",
            justify="center"
        )
        intro.pack(padx=15, pady=(15, 10))

        self.upload_btn = ctk.CTkButton(
            f,
            text=i18n.t("btn_upload"),
            height=38,
            font=ctk.CTkFont(weight="bold"),
            command=self.on_upload_image
        )
        self.upload_btn.pack(padx=20, pady=10)

        self.result_card = ctk.CTkFrame(f, corner_radius=10, fg_color="#18181B")
        self.result_card.pack(padx=20, pady=10, fill="x")

        self.res_lbl = ctk.CTkLabel(
            self.result_card,
            text=i18n.t("analyzer_placeholder"),
            font=ctk.CTkFont(size=13),
            text_color="#71717A"
        )
        self.res_lbl.pack(padx=15, pady=15)

        self.apply_detected_btn = ctk.CTkButton(
            f,
            text=i18n.t("btn_apply"),
            fg_color="#10B981",
            hover_color="#059669",
            height=40,
            font=ctk.CTkFont(weight="bold"),
            state="disabled",
            command=self.on_apply_detected
        )
        self.apply_detected_btn.pack(padx=20, pady=10)

        self.detected_config = None

    # ------------------------------------------------------------------
    # TAB 3: PRESETS & EXPORT/IMPORT
    # ------------------------------------------------------------------
    def _build_presets_tab(self):
        f = self.tab_presets
        f.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(f, text=i18n.t("lbl_presets"), font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(15, 8), sticky="w"
        )

        row_idx = 1
        for name, preset_cfg in PRESETS.items():
            btn = ctk.CTkButton(
                f,
                text=name,
                height=34,
                fg_color="#27272A",
                hover_color="#3F3F46",
                command=lambda n=name: self.load_preset(n)
            )
            btn.grid(row=row_idx, column=0, columnspan=2, padx=15, pady=4, sticky="ew")
            row_idx += 1

        ctk.CTkLabel(f, text=i18n.t("lbl_save_file"), font=ctk.CTkFont(weight="bold")).grid(
            row=row_idx, column=0, columnspan=2, padx=15, pady=(15, 6), sticky="w"
        )
        row_idx += 1

        exp_btn = ctk.CTkButton(f, text=i18n.t("btn_export"), command=self.export_to_file)
        exp_btn.grid(row=row_idx, column=0, padx=(15, 5), pady=5, sticky="ew")

        imp_btn = ctk.CTkButton(f, text=i18n.t("btn_import"), command=self.import_from_file)
        imp_btn.grid(row=row_idx, column=1, padx=(5, 15), pady=5, sticky="ew")
        row_idx += 1

        ctk.CTkLabel(f, text=i18n.t("lbl_share"), font=ctk.CTkFont(weight="bold")).grid(
            row=row_idx, column=0, columnspan=2, padx=15, pady=(12, 6), sticky="w"
        )
        row_idx += 1

        self.share_code_entry = ctk.CTkEntry(f, placeholder_text="CRX-...")
        self.share_code_entry.grid(row=row_idx, column=0, columnspan=2, padx=15, pady=5, sticky="ew")
        row_idx += 1

        copy_btn = ctk.CTkButton(f, text=i18n.t("btn_copy_code"), command=self.copy_share_code)
        copy_btn.grid(row=row_idx, column=0, padx=(15, 5), pady=5, sticky="ew")

        load_code_btn = ctk.CTkButton(f, text=i18n.t("btn_load_code"), command=self.load_share_code)
        load_code_btn.grid(row=row_idx, column=1, padx=(5, 15), pady=5, sticky="ew")

    # ------------------------------------------------------------------
    # EVENT HANDLERS
    # ------------------------------------------------------------------
    def on_toggle_switch(self):
        enabled = self.toggle_var.get()
        self.config.enabled = enabled
        self.overlay.set_visible(enabled)
        self.update_preview()

    def on_style_change(self, val):
        for key, style in STYLE_LABEL_KEYS.items():
            if val == i18n.t(key):
                if style in VALID_STYLES:
                    self.config.style = style
                break
        self.sync_and_redraw()

    def on_slider_change(self, _=None):
        self.config.size = int(self.size_slider.get())
        self.config.thickness = int(self.thick_slider.get())
        self.config.gap = int(self.gap_slider.get())
        self.config.dot_size = int(self.dot_slider.get())
        self.sync_and_redraw()

    def on_opacity_change(self, _=None):
        self.config.opacity = float(self.opacity_slider.get())
        self.sync_and_redraw()

    def set_color(self, hex_val):
        self.config.color = hex_val
        self.hex_entry.delete(0, tk.END)
        self.hex_entry.insert(0, hex_val)
        self.sync_and_redraw()

    def on_hex_enter(self, silent=False):
        val = self.hex_entry.get().strip()
        if not val:
            if not silent:
                messagebox.showwarning(i18n.t("msg_bad_hex_title"), i18n.t("msg_empty_hex_body"))
            self.hex_entry.delete(0, tk.END)
            self.hex_entry.insert(0, self.config.color)
            return
        if not val.startswith("#"):
            val = "#" + val
        if _HEX_RE.match(val):
            self.config.color = val.upper()
            if self.hex_entry.get().strip() != val.upper():
                self.hex_entry.delete(0, tk.END)
                self.hex_entry.insert(0, val.upper())
            self.sync_and_redraw()
        else:
            if not silent:
                messagebox.showwarning(i18n.t("msg_bad_hex_title"), i18n.t("msg_bad_hex_body", val=val))
            self.hex_entry.delete(0, tk.END)
            self.hex_entry.insert(0, self.config.color)

    def on_outline_toggle(self):
        self.config.outline = self.outline_var.get()
        self.sync_and_redraw()

    def sync_and_redraw(self):
        self.overlay.update_config(self.config)
        self.update_preview()

    def update_preview(self):
        self.preview_canvas.delete("all")

        for i in range(20, PREVIEW_PX, 20):
            self.preview_canvas.create_line(i, 0, i, PREVIEW_PX, fill="#18181B")
            self.preview_canvas.create_line(0, i, PREVIEW_PX, i, fill="#18181B")
        cx = cy = PREVIEW_PX // 2
        self.preview_canvas.create_line(cx - 30, cy, cx + 30, cy, fill="#27272A", dash=(2, 2))
        self.preview_canvas.create_line(cx, cy - 30, cx, cy + 30, fill="#27272A", dash=(2, 2))

        img = render_crosshair(self.config, canvas=PREVIEW_PX, bg=None)
        self._preview_imgtk = ImageTk.PhotoImage(img)
        self.preview_canvas.create_image(cx, cy, image=self._preview_imgtk)

    def load_preset(self, name):
        if name in PRESETS:
            self.config = CrosshairConfig.from_dict(PRESETS[name].to_dict())
            self.sync_ui_to_config()
            self.sync_and_redraw()

    def _style_label_for(self, style):
        for key, s in STYLE_LABEL_KEYS.items():
            if s == style:
                return i18n.t(key)
        return i18n.t("style_cross")

    def sync_ui_to_config(self):
        self.style_menu.set(self._style_label_for(self.config.style))
        self.size_slider.set(self.config.size)
        self.thick_slider.set(self.config.thickness)
        self.gap_slider.set(self.config.gap)
        self.dot_slider.set(self.config.dot_size)
        self.opacity_slider.set(self.config.opacity)
        self.hex_entry.delete(0, tk.END)
        self.hex_entry.insert(0, self.config.color)
        self.outline_var.set(self.config.outline)
        self.toggle_var.set(self.overlay.enabled)

    # Image Analyzer
    def on_upload_image(self):
        path = filedialog.askopenfilename(
            title=i18n.t("dlg_pick_image"),
            filetypes=[(i18n.t("dlg_images"), "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if not path:
            return

        try:
            cfg, metrics = analyze_crosshair_image(path)
            self.detected_config = cfg
            summary_text = (
                f"{i18n.t('res_ok')}\n\n"
                f"{i18n.t('res_color')} {metrics['detected_color']}\n"
                f"{i18n.t('res_style')} {metrics['detected_style']}\n"
                f"{i18n.t('res_size', size=metrics['detected_size'], thickness=metrics['detected_thickness'])}\n"
                f"{i18n.t('res_gap', gap=metrics['detected_gap'])}\n"
                f"{i18n.t('res_outline')} {i18n.t('val_yes' if metrics['has_outline'] else 'val_no')}"
            )
            self.res_lbl.configure(text=summary_text, text_color="#10B981")
            self.apply_detected_btn.configure(state="normal")
        except Exception as e:
            messagebox.showerror(i18n.t("msg_error"), f"{i18n.t('msg_analyze_error')}\n{e}")

    def on_apply_detected(self):
        if self.detected_config:
            self.config = CrosshairConfig.from_dict(self.detected_config.to_dict())
            self.sync_ui_to_config()
            self.sync_and_redraw()
            messagebox.showinfo(i18n.t("msg_applied_title"), i18n.t("msg_applied_body"))

    # Export / Import
    def export_to_file(self):
        path = filedialog.asksaveasfilename(
            title=i18n.t("dlg_save_crosshair"),
            defaultextension=".json",
            filetypes=[(i18n.t("dlg_json"), "*.json")]
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.config.to_dict(), f, indent=4, ensure_ascii=False)
                messagebox.showinfo(i18n.t("msg_saved_title"),
                                    i18n.t("msg_saved_body", name=os.path.basename(path)))
            except Exception as e:
                messagebox.showerror(i18n.t("msg_error"), f"{i18n.t('msg_save_error')}\n{e}")

    def import_from_file(self):
        path = filedialog.askopenfilename(
            title=i18n.t("dlg_load_profile"),
            filetypes=[(i18n.t("dlg_json"), "*.json")]
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.config = CrosshairConfig.from_dict(data)
                self.sync_ui_to_config()
                self.sync_and_redraw()
                messagebox.showinfo(i18n.t("msg_loaded_title"), i18n.t("msg_loaded_file"))
            except Exception as e:
                messagebox.showerror(i18n.t("msg_error"), f"{i18n.t('msg_load_error')}\n{e}")

    def copy_share_code(self):
        code = self.config.to_share_code()
        self.clipboard_clear()
        self.clipboard_append(code)
        self.share_code_entry.delete(0, tk.END)
        self.share_code_entry.insert(0, code)
        messagebox.showinfo(i18n.t("msg_copied_title"), i18n.t("msg_copied_body"))

    def load_share_code(self):
        code = self.share_code_entry.get().strip()
        if not code:
            return
        try:
            self.config = CrosshairConfig.from_share_code(code)
            self.sync_ui_to_config()
            self.sync_and_redraw()
            messagebox.showinfo(i18n.t("msg_loaded_title"), i18n.t("msg_loaded_code"))
        except Exception as e:
            messagebox.showerror(i18n.t("msg_error"), f"{i18n.t('msg_bad_code')}\n{e}")


def main():
    app = CrosshairStudioApp()
    def _poll_hotkey():
        try:
            app.hotkey.poll_fallback()
        except Exception:
            pass
        try:
            app.after(50, _poll_hotkey)
        except Exception:
            pass
    app.after(50, _poll_hotkey)
    app.mainloop()


if __name__ == "__main__":
    main()
