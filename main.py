import flet as ft
import flet_audio as fta
import requests
import threading
import time
import os
import json
from datetime import datetime

# Default configuration constants
DEFAULT_AUDIO_URL = "https://www.soundjay.com/buttons/sounds/beep-07.mp3"
DEFAULT_FIREBASE_URL = "PLACEHOLDER_FIREBASE_URL"

# Absolute path for the configuration file (same directory as main.py)
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    """Loads configuration from local config.json file, falls back to defaults if file is missing or invalid."""
    default_config = {
        "firebase_url": DEFAULT_FIREBASE_URL,
        "alarm_path": DEFAULT_AUDIO_URL,
        "alarm_enabled": True
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            # Ensure all keys exist
            for k, v in default_config.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_config

def save_config(config_data):
    """Saves current state dictionary to the config.json file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Error saving local config: {e}")

def main(page: ft.Page):
    # App configuration
    page.title = "Titan Engine Live"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121214"
    page.padding = 16
    
    # Custom font configuration for a premium aesthetic
    page.fonts = {
        "Outfit": "https://github.com/google/fonts/raw/main/ofl/outfit/static/Outfit-Regular.ttf",
        "Outfit-Bold": "https://github.com/google/fonts/raw/main/ofl/outfit/static/Outfit-Bold.ttf",
        "CourierPrime": "https://github.com/google/fonts/raw/main/ofl/courierprime/CourierPrime-Regular.ttf"
    }
    page.theme = ft.Theme(font_family="Outfit")
    
    # Load configuration from config.json
    config_data = load_config()
    
    # Thread-safe in-memory state dictionary
    app_state = {
        "firebase_url": config_data.get("firebase_url", DEFAULT_FIREBASE_URL),
        "alarm_path": config_data.get("alarm_path", DEFAULT_AUDIO_URL),
        "alarm_enabled": config_data.get("alarm_enabled", True)
    }
    
    # State tracking variables (polling thread uses nonlocal)
    last_timestamp = None
    
    # Audio component initialization using flet_audio
    audio_alert = fta.Audio(
        src=app_state["alarm_path"],
        autoplay=False
    )
    page.services.append(audio_alert)
    page.update()
    
    # Log terminal scrollable content
    log_list = ft.ListView(
        expand=True,
        spacing=4,
        auto_scroll=True
    )
    
    # Thread-safe logging function
    def add_log(message: str, is_error: bool = False):
        now = datetime.now().strftime("%H:%M:%S")
        color = "#FF1744" if is_error else "#00E676"
        log_list.controls.append(
            ft.Text(
                value=f"[{now}] {message}",
                color=color if is_error else "#A5B4FC",
                size=12,
                font_family="CourierPrime"
            )
        )
        page.update()
        
    # Toast notification helper
    def show_toast(message: str, is_success: bool = True):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color="#121214" if is_success else "#FFFFFF", weight=ft.FontWeight.BOLD),
            bgcolor="#00E676" if is_success else "#FF1744",
            action="Dismiss"
        )
        page.snack_bar.open = True
        page.update()
        
    # Pulse indicator and text for connection status
    connection_indicator = ft.Container(
        width=10,
        height=10,
        border_radius=5,
        bgcolor="#FF1744",  # Starts as Red (Disconnected/Connecting)
        animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
    )
    connection_text = ft.Text("Configuring...", color="#8E9AA8", size=12, weight=ft.FontWeight.W_500)
    
    def set_connection_status(status_str: str, color_hex: str):
        connection_text.value = status_str
        connection_indicator.bgcolor = color_hex
        page.update()
        
    # Active Signal UI Display Components
    symbol_text = ft.Text(value="WAITING...", size=24, weight=ft.FontWeight.BOLD, color="#FFFFFF")
    status_badge = ft.Container(
        content=ft.Text(value="SCANNING MARKET...", size=11, weight=ft.FontWeight.BOLD, color="#121214"),
        bgcolor=ft.Colors.AMBER_ACCENT,
        padding=ft.Padding(left=12, top=4, right=12, bottom=4),
        border_radius=20,
    )
    entry_value = ft.Text(value="--", size=18, weight=ft.FontWeight.BOLD, color="#FFFFFF")
    sl_value = ft.Text(value="--", size=18, weight=ft.FontWeight.BOLD, color="#FFFFFF")
    time_value = ft.Text(value="Waiting for signal...", size=12, color="#8E9AA8")
    
    # Central Dynamic Card styled with Glassmorphism
    signal_card = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
        border=ft.Border(top=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE)), right=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE)), bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE)), left=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))),
        border_radius=16,
        padding=20,
        blur=ft.Blur(10, 10),
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("CURRENT TRADE", size=12, color="#8E9AA8", weight=ft.FontWeight.BOLD),
                        status_badge
                    ]
                ),
                symbol_text,
                ft.Divider(color=ft.Colors.with_opacity(0.08, ft.Colors.WHITE), height=1),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text("ENTRY PRICE", size=11, color="#8E9AA8"),
                                entry_value
                            ]
                        ),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text("STOP LOSS (SL)", size=11, color="#8E9AA8"),
                                sl_value
                            ]
                        )
                    ]
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        ft.Icon(ft.Icons.ACCESS_TIME, size=14, color="#8E9AA8"),
                        time_value
                    ]
                )
            ]
        )
    )
    
    # Thread-safe UI update helper when a new signal occurs
    def update_ui_with_signal(data: dict):
        symbol = data.get("symbol", "UNKNOWN")
        entry = data.get("entry", 0.0)
        sl = data.get("sl", 0.0)
        status = data.get("status", "SCANNING")
        ts = data.get("timestamp", "N/A")
        
        symbol_text.value = symbol
        entry_value.value = f"{entry:.2f}" if isinstance(entry, (int, float)) else str(entry)
        sl_value.value = f"{sl:.2f}" if isinstance(sl, (int, float)) else str(sl)
        time_value.value = f"Last Update: {ts}"
        
        # Style status badge & symbol color depending on action (BUY/SELL)
        status_upper = status.upper()
        status_badge.content.value = status_upper
        
        if "BUY" in status_upper:
            status_badge.bgcolor = "#00E676"  # Neon Green
            status_badge.content.color = "#121214"
            symbol_text.color = "#00E676"
        elif "SELL" in status_upper or "EXIT" in status_upper:
            status_badge.bgcolor = "#FF1744"  # Neon Red
            status_badge.content.color = "#FFFFFF"
            symbol_text.color = "#FF1744"
        else:
            status_badge.bgcolor = ft.Colors.AMBER_ACCENT
            status_badge.content.color = "#121214"
            symbol_text.color = "#FFFFFF"
            
        page.update()
        
    # URL Config input fields
    url_field = ft.TextField(
        value=app_state.get("firebase_url", ""),
        label="Firebase DB JSON Endpoint",
        focused_border_color="#00E676",
        text_style=ft.TextStyle(color="#FFFFFF"),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        border_radius=8,
        expand=True,
        content_padding=12,
        hint_text="https://your-database.firebaseio.com/signals.json"
    )
    
    def save_url_clicked(e):
        url = url_field.value.strip()
        app_state["firebase_url"] = url
        save_config(app_state)
        add_log(f"Firebase URL updated to: {url}")
        show_toast("Firebase URL saved!")
        
    url_save_button = ft.IconButton(
        icon=ft.Icons.SAVE,
        icon_color="#00E676",
        tooltip="Save Connection URL",
        on_click=save_url_clicked
    )
    
    # Custom alarm sound picker implementation
    sound_path_text = ft.Text(
        value=os.path.basename(app_state["alarm_path"]) if app_state["alarm_path"] != DEFAULT_AUDIO_URL else "Default Beep (Online)",
        size=11,
        color="#A5B4FC",
        italic=True,
        weight=ft.FontWeight.W_500
    )
    
    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    page.update()
    
    async def handle_file_picker_click(e):
        files = await file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["mp3", "wav"]
        )
        if files and len(files) > 0:
            selected_path = files[0].path
            if selected_path:
                app_state["alarm_path"] = selected_path
                save_config(app_state)
                audio_alert.src = selected_path
                page.update()  # Sync overlay audio source changes
                sound_path_text.value = os.path.basename(selected_path)
                sound_path_text.update()
                add_log(f"Alarm sound set to local: {selected_path}")
                show_toast("Custom audio path saved!")
            else:
                add_log("Error picking file: Path is empty.", is_error=True)
        else:
            add_log("Audio file selection cancelled.")

    select_file_btn = ft.Button(
        content="Choose Sound File",
        icon=ft.Icons.AUDIO_FILE,
        color="#121214",
        bgcolor="#00E676",
        on_click=handle_file_picker_click
    )
    
    # Reset sound path back to default
    def reset_sound_to_default(e):
        app_state["alarm_path"] = DEFAULT_AUDIO_URL
        save_config(app_state)
        audio_alert.src = DEFAULT_AUDIO_URL
        page.update()
        sound_path_text.value = "Default Beep (Online)"
        sound_path_text.update()
        add_log("Alarm sound reset to default beep.")
        show_toast("Reset to default alarm sound!")
        
    reset_sound_btn = ft.IconButton(
        icon=ft.Icons.SETTINGS_BACKUP_RESTORE,
        icon_color="#FF1744",
        tooltip="Reset to Default Sound",
        on_click=reset_sound_to_default
    )
    
    # Switch for enabling/disabling the alarm sound
    def alarm_switch_changed(e):
        val = e.control.value
        app_state["alarm_enabled"] = val
        save_config(app_state)
        add_log(f"Alarm status toggled: {'ENABLED' if val else 'DISABLED'}")

    alarm_switch = ft.Switch(
        label="Alarm Sound ON/OFF",
        value=app_state["alarm_enabled"],
        active_color="#00E676",
        on_change=alarm_switch_changed
    )
    
    # Test sound play button
    async def test_alarm(e):
        if app_state["alarm_enabled"]:
            try:
                await audio_alert.play()
                add_log("Tested audio alarm successfully.")
            except Exception as err:
                add_log(f"Test audio error: {err}", is_error=True)
        else:
            show_toast("Alarm is OFF! Turn it on first.")
            
    async def stop_alarm(e):
        try:
            await audio_alert.pause()
            add_log("Audio playback stopped manually.")
        except Exception as err:
            add_log(f"Stop audio error: {err}", is_error=True)
            
    test_alarm_btn = ft.IconButton(
        icon=ft.Icons.PLAY_CIRCLE_FILL,
        icon_color="#00E676",
        tooltip="Test Current Sound",
        on_click=test_alarm
    )
    
    stop_alarm_btn = ft.IconButton(
        icon=ft.Icons.STOP_CIRCLE,
        icon_color="#FF1744",
        tooltip="Stop Sound",
        on_click=stop_alarm
    )
    
    # Settings layout Container
    settings_card = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
        border=ft.Border(top=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)), right=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)), bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)), left=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE))),
        border_radius=16,
        padding=16,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Text("SYSTEM SETTINGS", size=11, color="#8E9AA8", weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        url_field,
                        url_save_button
                    ]
                ),
                ft.Divider(color=ft.Colors.with_opacity(0.05, ft.Colors.WHITE), height=1),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        alarm_switch,
                        ft.Row(
                            spacing=0,
                            controls=[test_alarm_btn, stop_alarm_btn]
                        )
                    ]
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row([select_file_btn, reset_sound_btn], spacing=4),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            controls=[
                                ft.Text("Active Sound File", size=10, color="#8E9AA8"),
                                sound_path_text
                            ]
                        )
                    ]
                )
            ]
        )
    )
    
    # Terminal Console Log box
    terminal_console = ft.Container(
        bgcolor="#09090B",
        border=ft.Border(top=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)), right=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)), bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)), left=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE))),
        border_radius=12,
        padding=12,
        height=180,
        content=log_list
    )
    
    # Core app layout rendering
    page.add(
        ft.Column(
            expand=True,
            spacing=16,
            controls=[
                # Top header bar
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Titan Engine Live 🚀", size=24, weight=ft.FontWeight.BOLD, font_family="Outfit-Bold", color="#00E676"),
                        ft.Row(
                            spacing=6,
                            controls=[
                                connection_indicator,
                                connection_text
                            ]
                        )
                    ]
                ),
                # Main visual components
                signal_card,
                settings_card,
                ft.Text("SYSTEM CONSOLE & LOGS", size=11, color="#8E9AA8", weight=ft.FontWeight.BOLD),
                terminal_console
            ]
        )
    )
    
    async def trigger_alarm_sound():
        try:
            await audio_alert.play()
        except Exception:
            pass
            
    # Background worker thread for polling Firebase
    def poll_firebase():
        while True:
            # Refresh Firebase url dynamically on each iteration from memory state
            current_url = app_state["firebase_url"]
            
            if not current_url or current_url == DEFAULT_FIREBASE_URL:
                set_connection_status("URL Required", "#FF8F00")  # Amber color
                time.sleep(2)
                continue
                
            try:
                response = requests.get(current_url, timeout=5)
                if response.status_code == 200:
                    set_connection_status("Connected", "#00E676")  # Green
                    try:
                        data = response.json()
                    except Exception:
                        set_connection_status("Invalid JSON", "#FF1744")
                        add_log("Error: Fetch succeeded but response was not valid JSON.", is_error=True)
                        time.sleep(2)
                        continue
                        
                    # Handle flat or nested trade structures from Firebase RTDB
                    target_data = None
                    if isinstance(data, dict):
                        if "timestamp" in data:
                            target_data = data
                        else:
                            # Firebase push structure support: {"-Nxyz...": {"timestamp": ..., "symbol": ...}}
                            # Filter keys where the value is a dictionary and contains a 'timestamp'
                            nested_records = {k: v for k, v in data.items() if isinstance(v, dict) and "timestamp" in v}
                            if nested_records:
                                # Retrieve latest key chronologically
                                latest_key = sorted(nested_records.keys())[-1]
                                target_data = nested_records[latest_key]
                                
                    if target_data:
                        new_timestamp = target_data.get("timestamp")
                        if new_timestamp != last_timestamp:
                            last_timestamp = new_timestamp
                            
                            # Safely update the signal UI components
                            update_ui_with_signal(target_data)
                            add_log(f"New trade alert: {target_data.get('status')} | {target_data.get('symbol')}")
                            
                            # Play alarm audio if user enables it
                            if app_state["alarm_enabled"]:
                                add_log("Triggering audio alert buzzer...")
                                try:
                                    page.run_task(trigger_alarm_sound)
                                except Exception as sound_err:
                                    add_log(f"Sound play failed: {sound_err}", is_error=True)
                        else:
                            # Data fetched successfully, but timestamp matches last seen trade
                            pass
                    elif data is None:
                        set_connection_status("No Signals", "#FF8F00")
                    else:
                        set_connection_status("Format Error", "#FF8F00")
                else:
                    set_connection_status(f"HTTP {response.status_code}", "#FF1744")
                    add_log(f"HTTP Connection Error: Server returned status {response.status_code}.", is_error=True)
            except requests.RequestException as e:
                set_connection_status("Connection Lost", "#FF1744")
                add_log(f"Network dropout detected: {str(e)}", is_error=True)
                
            time.sleep(2)
            
    # Launch polling thread as daemon
    poll_thread = threading.Thread(target=poll_firebase, daemon=True)
    poll_thread.start()

if __name__ == "__main__":
    ft.run(main)
