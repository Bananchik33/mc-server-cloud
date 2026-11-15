import customtkinter as ctk
import minecraft_launcher_lib
import subprocess
import os
import threading
import sys

# ==========================================
# 1. ОСНОВНЫЕ НАСТРОЙКИ СЕРВЕРА
# ==========================================
MC_VERSION = "1.20.1"
FORGE_VERSION = "1.20.1-47.2.0"
VERSION_ID = f"{MC_VERSION}-forge-{FORGE_VERSION.split('-')[1]}" 

# Папка, куда будет скачиваться игра (в AppData)
CLIENT_DIR = os.path.join(os.environ["APPDATA"], ".my_custom_server")

# Настройки оформления окна
ctk.set_appearance_mode("dark")  # Темная тема
ctk.set_default_color_theme("blue")  # Синие кнопки

# ==========================================
# 2. ГЛАВНЫЙ КЛАСС ИНТЕРФЕЙСА
# ==========================================
class LauncherWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Настройка самого окна
        self.title("Мой Майнкрафт Лаунчер")
        self.geometry("400x300")
        self.resizable(False, False) # Запрещаем менять размер окна

        # Заголовок
        self.label_title = ctk.CTkLabel(self, text="Добро пожаловать!", font=("Arial", 20, "bold"))
        self.label_title.pack(pady=20)

        # Поле для ввода логина
        self.entry_login = ctk.CTkEntry(self, placeholder_text="Введите ваш никнейм", width=250)
        self.entry_login.pack(pady=10)

        # Текстовая строка для статуса (что происходит прямо сейчас)
        self.label_status = ctk.CTkLabel(self, text="", text_color="gray")
        self.label_status.pack(pady=10)

        # Кнопка ИГРАТЬ
        self.button_play = ctk.CTkButton(self, text="ИГРАТЬ", width=200, height=40, command=self.start_game_thread)
        self.button_play.pack(pady=10)

    # ==========================================
    # 3. ЛОГИКА ЗАПУСКА (МНОГОПОТОЧНОСТЬ)
    # ==========================================
    def update_status(self, text):
        """Метод для обновления текста статуса на экране"""
        self.label_status.configure(text=text)
        self.update() # Принудительно обновляем окно

    def start_game_thread(self):
        """
        Запускает установку и игру в отдельном потоке.
        Если делать это в основном потоке, окно лаунчера намертво зависнет, 
        пока игра не скачается. Threading решает эту проблему.
        """
        username = self.entry_login.get()
        
        if not username:
            self.update_status("Ошибка: Введите никнейм!")
            return

        # Блокируем кнопку и поле ввода, чтобы не нажали дважды
        self.button_play.configure(state="disabled")
        self.entry_login.configure(state="disabled")
        
        # Запускаем фоновый поток для функции launch_logic
        threading.Thread(target=self.launch_logic, args=(username,), daemon=True).start()

    def launch_logic(self, username):
        """Сама логика скачивания и запуска (выполняется в фоне)"""
        try:
            # 1. Установка ванильного Майнкрафта
            self.update_status("Проверка файлов игры (Vanilla)...")
            minecraft_launcher_lib.install.install_minecraft_version(MC_VERSION, CLIENT_DIR)

            # 2. Установка Forge
            self.update_status("Проверка файлов Forge...")
            minecraft_launcher_lib.forge.install_forge_version(FORGE_VERSION, CLIENT_DIR)

            # 3. Подготовка параметров запуска
            self.update_status("Генерация команды запуска...")
            options = {
                "username": username,
                "uuid": "00000000-0000-0000-0000-000000000000", # Заглушка для пиратки
                "token": "access_token"
            }

            command = minecraft_launcher_lib.command.get_minecraft_command(VERSION_ID, CLIENT_DIR, options)

            # 4. Запуск игры и закрытие лаунчера
            self.update_status("Игра запускается! Лаунчер закроется.")
            subprocess.Popen(command) # Запускаем игру независимым процессом
            
            # Закрываем окно лаунчера (чтобы не висел в фоне, пока идет игра)
            self.destroy() 
            sys.exit()

        except Exception as e:
            # Если что-то сломалось, выводим ошибку и разблокируем кнопку
            self.update_status(f"Ошибка запуска: {e}")
            self.button_play.configure(state="normal")
            self.entry_login.configure(state="normal")

# ==========================================
# 4. ТОЧКА ВХОДА (СТАРТ ПРОГРАММЫ)
# ==========================================
if __name__ == "__main__":
    app = LauncherWindow()
    app.mainloop() # Запускает бесконечный цикл отрисовки окна