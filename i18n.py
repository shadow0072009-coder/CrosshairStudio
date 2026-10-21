"""i18n for Crosshair Studio Pro: Uzbek, Russian, English.

All UI strings live here in one place. The chosen language is persisted to
settings.json next to the app, so it survives restarts.
"""
import os
import sys
import json

# In a PyInstaller --onefile build, __file__ points into the temporary
# extraction folder (_MEIxxxx), which is wiped after every run. Save settings
# next to the executable instead, so the language survives restarts.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")

LANG_ORDER = ("uz", "ru", "en")
LANG_LABELS = {"uz": "O'zbek", "ru": "Русский", "en": "English"}

# key -> {uz, ru, en}
STRINGS = {
    "app_title": {
        "uz": "🎯 Crosshair Studio Pro",
        "ru": "🎯 Crosshair Studio Pro",
        "en": "🎯 Crosshair Studio Pro",
    },
    "hotkey_hint": {
        "uz": "F8 = yoqish/o'chirish",
        "ru": "F8 = вкл/выкл",
        "en": "F8 = toggle on/off",
    },
    "master_toggle": {
        "uz": "Nishonni yoqish / o'chirish",
        "ru": "Прицел вкл / выкл",
        "en": "Enable / disable crosshair",
    },
    "tab_designer": {"uz": "🎨 Konstruktor", "ru": "🎨 Конструктор", "en": "🎨 Designer"},
    "tab_analyzer": {"uz": "📸 Rasm Analiz (AI)", "ru": "📸 Анализ картинки (AI)", "en": "📸 Image Analysis (AI)"},
    "tab_presets": {"uz": "📁 Profillar & Ulashish", "ru": "📁 Профили и обмен", "en": "📁 Profiles & Sharing"},
    "preview_title": {"uz": "Jonli ko'rinish (Preview)", "ru": "Живой предпросмотр", "en": "Live Preview"},
    "quick_awp": {"uz": "🎯 AWP Nuqta", "ru": "🎯 AWP Точка", "en": "🎯 AWP Dot"},
    "quick_valorant": {"uz": "💎 Valorant Cyan", "ru": "💎 Valorant Cyan", "en": "💎 Valorant Cyan"},
    "lbl_style": {"uz": "Uslub (Style):", "ru": "Стиль:", "en": "Style:"},
    "style_cross": {"uz": "Xoch", "ru": "Крест", "en": "Cross"},
    "style_dot": {"uz": "Nuqta", "ru": "Точка", "en": "Dot"},
    "style_cross_dot": {"uz": "Xoch+Nuqta", "ru": "Крест+Точка", "en": "Cross+Dot"},
    "style_circle": {"uz": "Aylana", "ru": "Круг", "en": "Circle"},
    "style_t": {"uz": "T", "ru": "T", "en": "T"},
    "lbl_size": {"uz": "Uzunligi (Size):", "ru": "Длина (Size):", "en": "Length (Size):"},
    "lbl_thickness": {"uz": "Qalinligi (Thickness):", "ru": "Толщина (Thickness):", "en": "Thickness:"},
    "lbl_gap": {"uz": "Oraliq (Gap):", "ru": "Зазор (Gap):", "en": "Gap:"},
    "lbl_dot_size": {"uz": "Nuqta kattaligi:", "ru": "Размер точки:", "en": "Dot size:"},
    "lbl_opacity": {"uz": "Shaffoflik (Opacity):", "ru": "Прозрачность (Opacity):", "en": "Opacity:"},
    "lbl_colors": {"uz": "Rang tanlash:", "ru": "Выбор цвета:", "en": "Color:"},
    "lbl_hex": {"uz": "HEX kodi:", "ru": "HEX-код:", "en": "HEX code:"},
    "cb_outline": {
        "uz": "Qora kontur (Outline) qo'shish",
        "ru": "Добавить контур (Outline)",
        "en": "Add outline",
    },
    "lbl_offset": {"uz": "Nozik moslash (Offset):", "ru": "Точная подстройка (Offset):", "en": "Fine-tune (Offset):"},
    "btn_reset": {"uz": "Nolga", "ru": "Сброс", "en": "Reset"},
    "analyzer_intro": {
        "uz": "Istalgan o'yindagi (CS2, Valorant, CS 1.6) crosshair skrinshotini\nyuklang, dastur undagi nishonni avtomatik aniqlab beradi!",
        "ru": "Загрузите скриншот прицела из любой игры (CS2, Valorant, CS 1.6) —\nпрограмма автоматически определит его параметры!",
        "en": "Upload a crosshair screenshot from any game (CS2, Valorant, CS 1.6)\nand the app will detect its parameters automatically!",
    },
    "btn_upload": {
        "uz": "📁 Rasm yuklash (Screenshot tanlash)",
        "ru": "📁 Загрузить картинку (выбрать скриншот)",
        "en": "📁 Upload image (choose screenshot)",
    },
    "analyzer_placeholder": {
        "uz": "Hozircha rasm tanlanmadi",
        "ru": "Изображение пока не выбрано",
        "en": "No image selected yet",
    },
    "btn_apply": {
        "uz": "✅ Aniqlangan nishonni qo'llash",
        "ru": "✅ Применить найденный прицел",
        "en": "✅ Apply detected crosshair",
    },
    "lbl_presets": {"uz": "Tayyor shablonlar (Presets):", "ru": "Готовые шаблоны (пресеты):", "en": "Ready presets:"},
    "lbl_save_file": {"uz": "Fayl orqali saqlash:", "ru": "Сохранение в файл:", "en": "Save to a file:"},
    "btn_export": {"uz": "💾 Eksport (.json)", "ru": "💾 Экспорт (.json)", "en": "💾 Export (.json)"},
    "btn_import": {"uz": "📥 Import (.json)", "ru": "📥 Импорт (.json)", "en": "📥 Import (.json)"},
    "lbl_share": {"uz": "Ulashish kodi (Share Code):", "ru": "Код обмена (Share Code):", "en": "Share Code:"},
    "btn_copy_code": {"uz": "📋 Kodni nusxalash", "ru": "📋 Скопировать код", "en": "📋 Copy code"},
    "btn_load_code": {"uz": "🔄 Kodni yuklash", "ru": "🔄 Загрузить код", "en": "🔄 Load code"},
    "lang_label": {"uz": "🌐 Til", "ru": "🌐 Язык", "en": "🌐 Language"},
    # --- analyzer results ---
    "res_ok": {"uz": "✅ Analiz muvaffaqiyatli!", "ru": "✅ Анализ выполнен!", "en": "✅ Analysis complete!"},
    "res_color": {"uz": "🎨 Rang:", "ru": "🎨 Цвет:", "en": "🎨 Color:"},
    "res_style": {"uz": "📐 Uslub:", "ru": "📐 Стиль:", "en": "📐 Style:"},
    "res_size": {
        "uz": "📏 Uzunlik: {size} px | Qalinlik: {thickness} px",
        "ru": "📏 Длина: {size} px | Толщина: {thickness} px",
        "en": "📏 Length: {size} px | Thickness: {thickness} px",
    },
    "res_gap": {"uz": "⭕ Oraliq (Gap): {gap} px", "ru": "⭕ Зазор (Gap): {gap} px", "en": "⭕ Gap: {gap} px"},
    "res_outline": {"uz": "⬛ Kontur:", "ru": "⬛ Контур:", "en": "⬛ Outline:"},
    "val_yes": {"uz": "Mavjud", "ru": "Есть", "en": "Yes"},
    "val_no": {"uz": "Yo'q", "ru": "Нет", "en": "No"},
    # --- dialogs / messages ---
    "dlg_pick_image": {"uz": "Nishon rasmini tanlang", "ru": "Выберите изображение прицела", "en": "Select a crosshair image"},
    "dlg_images": {"uz": "Rasm fayllari", "ru": "Файлы изображений", "en": "Image files"},
    "dlg_save_crosshair": {"uz": "Nishonni saqlash", "ru": "Сохранить прицел", "en": "Save crosshair"},
    "dlg_json": {"uz": "JSON fayllar", "ru": "Файлы JSON", "en": "JSON files"},
    "dlg_load_profile": {"uz": "Nishon profilini yuklash", "ru": "Загрузить профиль прицела", "en": "Load crosshair profile"},
    "msg_copied_title": {"uz": "Nusxalandi", "ru": "Скопировано", "en": "Copied"},
    "msg_copied_body": {
        "uz": "Ulashish kodi xotiraga (clipboard) nusxalandi!",
        "ru": "Код обмена скопирован в буфер обмена!",
        "en": "Share code copied to the clipboard!",
    },
    "msg_loaded_title": {"uz": "Yuklandi", "ru": "Загружено", "en": "Loaded"},
    "msg_loaded_code": {
        "uz": "Nishon kodi muvaffaqiyatli qo'llandi!",
        "ru": "Код прицела успешно применён!",
        "en": "Crosshair code applied successfully!",
    },
    "msg_loaded_file": {
        "uz": "Profil muvaffaqiyatli yuklandi!",
        "ru": "Профиль успешно загружен!",
        "en": "Profile loaded successfully!",
    },
    "msg_error": {"uz": "Xatolik", "ru": "Ошибка", "en": "Error"},
    "msg_bad_code": {"uz": "Noto'g'ri kod:", "ru": "Неверный код:", "en": "Invalid code:"},
    "msg_load_error": {"uz": "Faylni yuklashda xatolik:", "ru": "Ошибка при загрузке файла:", "en": "Error loading the file:"},
    "msg_save_error": {"uz": "Saqlashda xatolik:", "ru": "Ошибка при сохранении:", "en": "Error saving the file:"},
    "msg_saved_title": {"uz": "Saqlandi", "ru": "Сохранено", "en": "Saved"},
    "msg_saved_body": {
        "uz": "Profil muvaffaqiyatli saqlandi:\n{name}",
        "ru": "Профиль успешно сохранён:\n{name}",
        "en": "Profile saved successfully:\n{name}",
    },
    "msg_analyze_error": {
        "uz": "Rasmni tahlil qilishda xatolik yuz berdi:",
        "ru": "Ошибка при анализе изображения:",
        "en": "Error while analyzing the image:",
    },
    "msg_applied_title": {"uz": "Muvaffaqiyatli", "ru": "Успешно", "en": "Success"},
    "msg_applied_body": {
        "uz": "Aniqlangan nishon o'rnatildi!",
        "ru": "Найденный прицел применён!",
        "en": "Detected crosshair applied!",
    },
    "msg_bad_hex_title": {"uz": "Noto'g'ri rang", "ru": "Неверный цвет", "en": "Invalid color"},
    "msg_bad_hex_body": {
        "uz": "'{val}' — noto'g'ri HEX kod.\n6 ta belgi ishlatiladi: #00FF66",
        "ru": "'{val}' — неверный HEX-код.\nИспользуется 6 символов: #00FF66",
        "en": "'{val}' is not a valid HEX code.\nUse 6 characters: #00FF66",
    },
    "msg_empty_hex_body": {
        "uz": "HEX kod bo'sh bo'lishi mumkin emas.\nNamuna: #00FF66",
        "ru": "HEX-код не может быть пустым.\nПример: #00FF66",
        "en": "HEX code cannot be empty.\nExample: #00FF66",
    },
}

# Default language on first launch (no saved preference yet)
_current = "en"
_listeners = []


def get_language() -> str:
    return _current


def lang_label(code: str = None) -> str:
    return LANG_LABELS.get(code or _current, LANG_LABELS["uz"])


def code_for_label(label: str) -> str:
    for code, lab in LANG_LABELS.items():
        if lab == label:
            return code
    return _current


def t(key: str, **fmt) -> str:
    """Translate key for the current language; fall back to uz then to the key."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry.get("en") or entry.get("uz") or key
    if fmt:
        try:
            text = text.format(**fmt)
        except (KeyError, IndexError):
            pass
    return text


def on_change(fn):
    """Register a callback fired after the language changes."""
    _listeners.append(fn)


def set_language(code: str):
    global _current
    if code not in LANG_ORDER or code == _current:
        return
    _current = code
    save_settings()
    for fn in list(_listeners):
        try:
            fn()
        except Exception:
            pass


def load_settings():
    """Load persisted settings (language) from settings.json."""
    global _current
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        code = data.get("language")
        if code in LANG_ORDER:
            _current = code
    except Exception:
        pass


def save_settings():
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({"language": _current}, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # persistence is best-effort


# Load persisted language at import time
load_settings()
