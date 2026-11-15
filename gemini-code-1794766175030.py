import customtkinter as ctk
import minecraft_launcher_lib
import subprocess
import os
import threading
import hashlib
import json
import time
import zipfile
import requests

# ==========================================
# 1. КОНФИГУРАЦИЯ ПРОЕКТА (Bananchik33)
# ==========================================
TEST_AUTH_MODE = True

MC_VERSION = "1.20.1"
FORGE_VERSION = "1.20.1-47.2.0"
VERSION_ID = f"{MC_VERSION}-forge-{FORGE_VERSION.split('-')[1]}"

# Папка клиента на ПК игрока: C:\Users\Имя\AppData\Roaming\.my_custom_server
CLIENT_DIR = os.path.join(os.environ["APPDATA"], ".my_custom_server")
MODS_DIR = os.path.join(CLIENT_DIR, "mods")
CONFIG_FILE = os.path.join(CLIENT_DIR, "launcher_config.json")

# Ссылка на ваш манифест в репозитории Bananchik33/mc-server-cloud
MODS_MANIFEST_URL = "https://raw.githubusercontent.com/Bananchik33/mc-server-cloud/main/mods_manifest.json"
AUTH_API_URL = "https://your-server.com/api/login"

# Тестовые аккаунты (Логин : Пароль)
MOCK_USERS = {
    "Bananchik33": "12345",
    "Admin": "12345",
    "Player1": "pass123"
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def get_file_md5(filepath):
    """Считает MD5-хэш локального файла"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# ==========================================
# 2. ОКНО ЛАУНЧЕРА И РАБОЧАЯ ЛОГИКА
# ==========================================
class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Minecraft Launcher — Bananchik33")
        self.geometry("480x500")
        self.resizable(False, False)

        os.makedirs(MODS_DIR, exist_ok=True)

        self.label_title = ctk.CTkLabel(self, text="ЛАУНЧЕР СЕРВЕРА", font=("Arial", 22, "bold"))
        self.label_title.pack(pady=(20, 5))

        self.label_sub = ctk.CTkLabel(
            self,
            text="Облако: GitHub (Chunk Sync) | Вход: Bananchik33 / 12345",
            font=("Arial", 11, "bold"),
            text_color="#2ECC71"
        )
        self.label_sub.pack(pady=(0, 15))

        self.entry_login = ctk.CTkEntry(self, placeholder_text="Ваш логин (Bananchik33)", width=280, height=35)
        self.entry_login.pack(pady=8)

        self.entry_pass = ctk.CTkEntry(self, placeholder_text="Ваш пароль (12345)", show="*", width=280, height=35)
        self.entry_pass.pack(pady=8)

        self.ram_label = ctk.CTkLabel(self, text="Выделено ОЗУ: 4096 МБ", font=("Arial", 13))
        self.ram_label.pack(pady=(12, 0))

        self.ram_slider = ctk.CTkSlider(
            self, from_=2048, to=8192, number_of_steps=12, width=280, command=self.update_ram_label
        )
        self.ram_slider.set(4096)
        self.ram_slider.pack(pady=8)

        self.status_label = ctk.CTkLabel(
            self, text="Готов к запуску", text_color="#A0A0A0", font=("Arial", 12), wraplength=440
        )
        self.status_label.pack(pady=(15, 5))

        self.progress_bar = ctk.CTkProgressBar(self, width=340)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=5)

        self.btn_play = ctk.CTkButton(
            self, text="ВОЙТИ И ИГРАТЬ", width=240, height=45, font=("Arial", 15, "bold"), command=self.start_workflow
        )
        self.btn_play.pack(pady=15)

        self.btn_folder = ctk.CTkButton(
            self, text="Открыть папку клиента (.my_custom_server)", width=240, height=28, fg_color="#3B3B3B", command=self.open_client_folder
        )
        self.btn_folder.pack(pady=2)

        self.max_progress = 100
        self.load_settings()

    def update_ram_label(self, value):
        self.ram_label.configure(text=f"Выделено ОЗУ: {int(value)} МБ")

    def set_status(self, text, color="#A0A0A0"):
        self.status_label.configure(text=text, text_color=color)
        self.update_idletasks()

    def open_client_folder(self):
        os.startfile(CLIENT_DIR)

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entry_login.insert(0, data.get("username", ""))
                    ram = data.get("ram", 4096)
                    self.ram_slider.set(ram)
                    self.update_ram_label(ram)
            except Exception:
                pass

    def save_settings(self, username, ram):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"username": username, "ram": int(ram)}, f)
        except Exception:
            pass

    def lock_ui(self, locked=True):
        state = "disabled" if locked else "normal"
        self.btn_play.configure(state=state)
        self.entry_login.configure(state=state)
        self.entry_pass.configure(state=state)
        self.ram_slider.configure(state=state)

    def authenticate(self, username, password):
        self.set_status("Проверка логина и пароля...", "#3498DB")
        if TEST_AUTH_MODE:
            if username in MOCK_USERS and MOCK_USERS[username] == password:
                fake_uuid = hashlib.md5(username.encode("utf-8")).hexdigest()
                return True, fake_uuid, "test_session_token"
            return False, None, "Неверный логин или пароль! (Вход: Bananchik33 / 12345)"
        else:
            try:
                resp = requests.post(AUTH_API_URL, json={"username": username, "password": password}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return True, data["uuid"], data["token"]
                return False, None, f"Отказ сервера: {resp.text}"
            except Exception as e:
                return False, None, f"Ошибка связи с сервером: {e}"

    # ==========================================
    # 3. СКАЧИВАНИЕ КУСКОВ ПО 19 МБ И СКЛЕЙКА В ZIP
    # ==========================================
    def sync_mods(self):
        self.set_status("Запрос манифеста с GitHub...", "#3498DB")
        self.progress_bar.set(0.05)

        nocache_url = f"{MODS_MANIFEST_URL}?t={int(time.time())}"
        resp = requests.get(nocache_url, timeout=15)

        if resp.status_code == 404:
            raise Exception(
                "Файл mods_manifest.json не найден на GitHub (404)! "
                "Загрузите все файлы из папки 'ЗАГРУЗИТЬ_НА_GITHUB' в корень репозитория."
            )
        resp.raise_for_status()

        manifest = resp.json()
        cloud_mods = manifest.get("mods", [])
        chunks_list = manifest.get("chunks", [])
        allowed_filenames = [m["name"] for m in cloud_mods]

        # 1. Античит: удаляем любые посторонние файлы из папки mods
        for existing_file in os.listdir(MODS_DIR):
            file_path = os.path.join(MODS_DIR, existing_file)
            if os.path.isfile(file_path) and existing_file not in allowed_filenames:
                self.set_status(f"Удаление лишнего файла: {existing_file}", "#E67E22")
                os.remove(file_path)

        # 2. Проверяем, все ли моды уже установлены и совпадают по MD5
        need_update = False
        for mod in cloud_mods:
            mod_path = os.path.join(MODS_DIR, mod["name"])
            if not os.path.exists(mod_path) or get_file_md5(mod_path) != mod["md5"].lower():
                need_update = True
                break

        # 3. Если нужно обновление — качаем куски по 19 МБ и склеиваем их в архив
        if need_update and chunks_list:
            combined_zip_path = os.path.join(CLIENT_DIR, "_downloaded_mods.zip")
            total_chunks = len(chunks_list)

            with open(combined_zip_path, "wb") as merged_zip:
                for idx, chunk_info in enumerate(chunks_list):
                    c_name = chunk_info["name"]
                    c_url = chunk_info["url"]

                    self.set_status(f"Скачивание части ({idx + 1}/{total_chunks}): {c_name}...", "#3498DB")
                    r = requests.get(c_url, stream=True, timeout=120)
                    if r.status_code == 404:
                        raise Exception(f"Часть архива '{c_name}' не найдена на GitHub! Проверьте загрузку файлов.")
                    r.raise_for_status()

                    for data_block in r.iter_content(chunk_size=65536):
                        merged_zip.write(data_block)

                    self.progress_bar.set((idx + 1) / (total_chunks + 1))

            # 4. Распаковываем склеенный ZIP-архив в папку mods
            self.set_status("Распаковка архива с модами...", "#3498DB")
            with zipfile.ZipFile(combined_zip_path, "r") as zf:
                zf.extractall(MODS_DIR)

            # Удаляем временный архив после распаковки
            if os.path.exists(combined_zip_path):
                os.remove(combined_zip_path)

        self.set_status(f"Все моды синхронизированы ({len(cloud_mods)} шт.)!", "#2ECC71")
        self.progress_bar.set(1.0)

    # ==========================================
    # 4. ЗАПУСК ИГРЫ
    # ==========================================
    def set_max_progress(self, new_max):
        self.max_progress = max(1, new_max)

    def set_current_progress(self, current):
        self.progress_bar.set(current / self.max_progress)
        self.update_idletasks()

    def start_workflow(self):
        username = self.entry_login.get().strip()
        password = self.entry_pass.get().strip()
        ram_mb = int(self.ram_slider.get())

        if not username or not password:
            self.set_status("Ошибка: Введите логин и пароль!", "#E74C3C")
            return

        self.lock_ui(True)
        threading.Thread(
            target=self.core_worker, args=(username, password, ram_mb), daemon=True
        ).start()

    def core_worker(self, username, password, ram_mb):
        try:
            ok, uuid_str, token_or_err = self.authenticate(username, password)
            if not ok:
                self.set_status(token_or_err, "#E74C3C")
                self.lock_ui(False)
                return

            self.save_settings(username, ram_mb)
            self.sync_mods()

            callback_dict = {
                "setStatus": lambda text: self.set_status(f"Файлы игры: {text}", "#3498DB"),
                "setProgress": self.set_current_progress,
                "setMax": self.set_max_progress
            }

            self.set_status("Проверка файлов Minecraft 1.20.1...", "#3498DB")
            minecraft_launcher_lib.install.install_minecraft_version(
                MC_VERSION, CLIENT_DIR, callback=callback_dict
            )

            self.set_status("Проверка и установка Forge...", "#3498DB")
            minecraft_launcher_lib.forge.install_forge_version(
                FORGE_VERSION, CLIENT_DIR, callback=callback_dict
            )

            self.set_status("Запуск Minecraft...", "#2ECC71")
            options = {
                "username": username,
                "uuid": uuid_str,
                "token": token_or_err,
                "jvmArguments": [f"-Xmx{ram_mb}M", f"-Xms2048M"]
            }

            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                VERSION_ID, CLIENT_DIR, options
            )

            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.Popen(minecraft_command, cwd=CLIENT_DIR, creationflags=creation_flags)

            self.after(2000, self.destroy)

        except Exception as e:
            self.set_status(f"Ошибка: {e}", "#E74C3C")
            self.lock_ui(False)


if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()