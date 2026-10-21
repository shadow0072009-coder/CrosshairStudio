"""Headless verification suite for Crosshair Studio Pro.

Run:  python test_crosshair.py
Exits non-zero on any failure.
"""
import os
import sys
import traceback

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
FAILURES = []


def check(name, fn):
    try:
        fn()
        print(f"  OK   {name}")
    except Exception:
        FAILURES.append(name)
        print(f"  FAIL {name}")
        traceback.print_exc()


def t_compile():
    import py_compile
    here = os.path.dirname(os.path.abspath(__file__))
    for f in ("config.py", "crosshair_render.py", "analyzer.py", "overlay.py", "i18n.py", "main.py"):
        py_compile.compile(os.path.join(here, f), doraise=True)


def t_i18n():
    import i18n
    # every key must exist in all three languages and be non-empty
    for key, entry in i18n.STRINGS.items():
        for lang in i18n.LANG_ORDER:
            assert lang in entry, f"{key}: missing {lang}"
            assert entry[lang].strip(), f"{key}: empty {lang}"
    # identical placeholder sets across languages (e.g. {size}, {name})
    import re as _re
    for key, entry in i18n.STRINGS.items():
        ph = {tuple(sorted(_re.findall(r"\{\w+\}", entry[l]))) for l in i18n.LANG_ORDER}
        assert len(ph) == 1, f"{key}: placeholder mismatch across languages: {ph}"
    # t() resolves in every language; formatting works
    i18n.set_language("ru")
    assert "Длина" in i18n.t("res_size", size=5, thickness=2)
    i18n.set_language("en")
    assert i18n.t("lbl_gap") == "Gap:"
    i18n.set_language("uz")
    assert i18n.t("lbl_gap") == "Oraliq (Gap):"
    i18n.set_language("en")  # leave default
    # unknown key falls back to itself, bad format kwargs never raises
    assert i18n.t("no_such_key") == "no_such_key"
    assert "{size}" in i18n.t("res_size") or i18n.t("res_size", wrong=1)
    # label <-> code mapping round trips
    for code in i18n.LANG_ORDER:
        assert i18n.code_for_label(i18n.lang_label(code)) == code


def t_i18n_persistence():
    import importlib
    import i18n
    settings = i18n.SETTINGS_PATH
    # save ru, reload module -> ru persists
    i18n.set_language("ru")
    assert os.path.exists(settings), "settings.json not written"
    importlib.reload(i18n)
    assert i18n.get_language() == "ru", f"persisted lang={i18n.get_language()}"
    # corrupted settings.json -> no crash, falls back to default (en)
    with open(settings, "w", encoding="utf-8") as f:
        f.write("{broken json")
    importlib.reload(i18n)
    assert i18n.get_language() == "en", i18n.get_language()
    # a new valid choice still persists after corruption was healed
    i18n.set_language("ru")
    importlib.reload(i18n)
    assert i18n.get_language() == "ru"
    # leave the suite in the default language (en)
    i18n.set_language("en")


def t_config_validation():
    from config import CrosshairConfig
    # Bad hex never crashes; falls back to default
    c = CrosshairConfig(color="GGGGGG")
    assert c.color == "#00FF00", c.color
    c = CrosshairConfig(color="#ff00")          # short
    assert c.color == "#00FF00", c.color
    c = CrosshairConfig(color="#00ff66")        # valid lower-case gets normalized
    assert c.color == "#00FF66", c.color
    # Out-of-range numbers are clamped
    c = CrosshairConfig(size=999, thickness=0, gap=-5, dot_size=0, opacity=5.0)
    assert (c.size, c.thickness, c.gap, c.dot_size, c.opacity) == (60, 1, 0, 1, 1.0)
    c = CrosshairConfig(size=-1, opacity=0.01)
    assert (c.size, c.opacity) == (0, 0.2)
    # Invalid style replaced
    c = CrosshairConfig(style="nope")
    assert c.style == "cross"
    # from_dict ignores unknown keys, validates bad values
    c = CrosshairConfig.from_dict({"color": "XYZ", "size": "12", "junk": 1})
    assert c.size == 12 and c.color == "#00FF00"
    # non-dict input rejected
    try:
        CrosshairConfig.from_dict([1, 2])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # bool coercion
    c = CrosshairConfig(outline="false", enabled="true")
    assert c.outline is False and c.enabled is True


def t_share_code():
    from config import CrosshairConfig, PRESETS
    c = PRESETS["AWP Red Sniper Dot"]
    code = c.to_share_code()
    assert code.startswith("CRX-")
    c2 = CrosshairConfig.from_share_code(code)
    assert c2.to_dict() == c.to_dict()
    # leading/trailing whitespace tolerated
    c3 = CrosshairConfig.from_share_code(f"  {code}  ")
    assert c3.to_dict() == c.to_dict()
    # corrupted code -> ValueError, never crash
    for bad in ("", "CRX-@@@@", "hello", "CRX-!!!!"):
        try:
            CrosshairConfig.from_share_code(bad)
            raise AssertionError(f"expected ValueError for {bad!r}")
        except ValueError:
            pass


def _center_is(img, rgb, tol=12):
    px = img.getpixel((img.width // 2, img.height // 2))
    return all(abs(a - b) <= tol for a, b in zip(px[:3], rgb))


def t_renderer():
    from config import CrosshairConfig, PRESETS, VALID_STYLES
    from crosshair_render import render_crosshair
    for style in VALID_STYLES:
        cfg = CrosshairConfig(style=style, color="#FF0000", opacity=1.0)
        img = render_crosshair(cfg, canvas=200, bg=None)
        assert img.size == (200, 200) and img.mode == "RGBA"
        a = img.getchannel("A")
        assert a.getextrema()[1] > 0, f"{style}: nothing rendered"
    # preset renders, center dot style has center pixel colored
    img = render_crosshair(PRESETS["AWP Red Sniper Dot"], canvas=200, bg=None)
    assert _center_is(img, (255, 30, 30), tol=40), img.getpixel((100, 100))
    # cross style has transparent center (gap)
    cfg = CrosshairConfig(style="cross", gap=5, size=10, thickness=2, dot_size=3)
    img = render_crosshair(cfg, canvas=200, bg=None)
    assert img.getpixel((100, 100))[3] == 0, "cross center should be transparent"
    # opacity actually dims the image
    full = render_crosshair(CrosshairConfig(style="dot", dot_size=8, opacity=1.0), 100)
    half = render_crosshair(CrosshairConfig(style="dot", dot_size=8, opacity=0.5), 100)
    assert sum(full.getchannel("A").tobytes()) > 1.5 * sum(half.getchannel("A").tobytes())
    # preview variant with background composites
    img = render_crosshair(CrosshairConfig(), canvas=100, bg=(9, 9, 11, 255))
    assert img.getpixel((2, 2))[:3] == (9, 9, 11)
    # overlay never covers the whole canvas with the crosshair color
    cfg = CrosshairConfig(style="cross", size=10, thickness=2, gap=4, color="#00FF00")
    img = render_crosshair(cfg, canvas=200, bg=None)
    corner = img.getpixel((3, 3))
    assert corner[3] < 10, f"corner should be transparent, got {corner}"


def t_analyzer():
    import numpy as np
    from PIL import Image
    from config import PRESETS, CrosshairConfig
    from analyzer import analyze_crosshair_image
    import tempfile
    # render a known crosshair on a dark background and analyze it
    from crosshair_render import render_crosshair
    cfg = CrosshairConfig(style="cross", size=10, thickness=2, gap=4,
                          color="#00FF66", outline=False)
    img = render_crosshair(cfg, canvas=400, bg=(40, 40, 45, 255))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
        img.save(path)
    try:
        got, metrics = analyze_crosshair_image(path)
        assert metrics["status"] == "success", metrics
        assert got.style == "cross", got.style
        assert abs(got.size - 10) <= 2, got.size
        assert abs(got.gap - 4) <= 2, got.gap
        assert got.thickness in (2, 3), got.thickness  # antialiased edges may add 1
    finally:
        os.unlink(path)
    # uniform image -> fallback config, no crash
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
        Image.new("RGB", (300, 300), (128, 128, 128)).save(path)
    try:
        got, metrics = analyze_crosshair_image(path)
        assert metrics["status"] == "warning"
    finally:
        os.unlink(path)


def t_overlay_smoke():
    """Create the real Win32 overlay, render, move, hide, destroy — no crash."""
    import tkinter as tk
    from config import CrosshairConfig
    from overlay import CrosshairOverlay
    root = tk.Tk()
    root.withdraw()
    try:
        ov = CrosshairOverlay(root, CrosshairConfig(color="#FF1E1E"))
        assert ov.hwnd, "no hwnd"
        import win32gui
        ov.set_visible(True)
        root.update()
        assert win32gui.IsWindowVisible(ov.hwnd), "overlay not visible"
        ov.set_offset(10, -5)
        ov.update_config(CrosshairConfig(style="dot", dot_size=5, opacity=0.5))
        root.update()
        ov.set_visible(False)
        root.update()
        assert not win32gui.IsWindowVisible(ov.hwnd), "overlay should hide"
        ov.set_visible(True)
        root.update()
        ov.destroy()
        root.update()
        assert not win32gui.IsWindow(ov.hwnd), "overlay window should be destroyed"
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def t_analyzer_module_import_main():
    """main.py imports cleanly (no Tk loop) — catches syntax/import errors."""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("main_under_test",
                                                  os.path.join(here, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "CrosshairStudioApp")


def t_app_full_lifecycle():
    """Start the real app, exercise every handler headlessly, then close."""
    import tkinter.messagebox as mb
    # modal dialogs would block the automated test
    for fn in ("showinfo", "showerror", "showwarning", "askyesno"):
        setattr(mb, fn, lambda *a, **k: None)
    import main as m
    app = m.CrosshairStudioApp()
    try:
        app.update()
        # style cycling through every style
        for label in ("Xoch", "Nuqta", "Xoch+Nuqta", "Aylana", "T"):
            app.on_style_change(label)
        app.update()
        # sliders
        app.size_slider.set(20); app.thick_slider.set(4)
        app.gap_slider.set(8); app.dot_slider.set(6)
        app.on_slider_change()
        app.opacity_slider.set(0.4); app.on_opacity_change()
        # colors + hex validation (valid, invalid, restore)
        app.set_color("#FF1E1E")
        app.hex_entry.delete(0, "end"); app.hex_entry.insert(0, "GGGGGG")
        app.on_hex_enter()                       # invalid -> restored, no crash
        assert app.hex_entry.get() == "#FF1E1E"
        app.hex_entry.delete(0, "end"); app.hex_entry.insert(0, "00FFFF")
        app.on_hex_enter()                       # missing # -> normalized
        assert app.config.color == "#00FFFF"
        # outline toggle, preview refresh
        app.on_outline_toggle()
        app.update_preview()
        # presets
        for name in __import__("config").PRESETS:
            app.load_preset(name)
        # offsets
        app.off_x_slider.set(12); app.off_y_slider.set(-7)
        app.on_offset_change()
        app.reset_offset()
        # share code round trip through UI
        code = app.config.to_share_code()
        app.share_code_entry.delete(0, "end"); app.share_code_entry.insert(0, code)
        app.load_share_code()
        app.share_code_entry.delete(0, "end"); app.share_code_entry.insert(0, "CRX-JUNK@@")
        app.load_share_code()                    # invalid -> messagebox, no crash
        # master toggle + hotkey handler
        app.toggle_crosshair()
        assert app.overlay.enabled is False
        app.toggle_crosshair()
        assert app.overlay.enabled is True
        app.update()
        # language switching through the menu handler, keeping the config
        import i18n
        assert i18n.get_language() == "en", "default launch language must be en"
        saved = app.config.to_dict()
        for label in ("O'zbek", "Русский", "English"):
            app.on_language_select(label)
            app.update()
            assert i18n.get_language() == i18n.code_for_label(label)
            assert app.config.to_dict() == saved, "config lost on language change"
            # rebuilt UI must exist and match the language
            assert app.tabs.tab(i18n.t("tab_designer")) is not None
            assert app.toggle_switch.cget("text") == i18n.t("master_toggle")
        # overlay kept working through rebuilds
        assert app.overlay.enabled is True
        app.update()
    finally:
        app.on_close()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("Crosshair Studio test suite:")
    check("py_compile (barcha modullar)", t_compile)
    check("config validatsiya/clamp", t_config_validation)
    check("share code roundtrip + noto'g'ri kodlar", t_share_code)
    check("renderer (uslublar, opacity, shaffoflik)", t_renderer)
    check("analyzer (sintetik rasm + fallback)", t_analyzer)
    check("overlay Win32 smoke test (yarat/ko'r/yashir/yop)", t_overlay_smoke)
    check("i18n (uch til, placeholder parity)", t_i18n)
    check("i18n persistence (settings.json)", t_i18n_persistence)
    check("main.py import", t_analyzer_module_import_main)
    check("app to'liq lifecycle (GUI + 3 til)", t_app_full_lifecycle)
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} -> {FAILURES}")
        sys.exit(1)
    print("BARCHA TESTLAR O'TDI")
    sys.exit(0)
