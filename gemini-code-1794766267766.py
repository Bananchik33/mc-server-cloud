import os
import hashlib
import json
import zipfile
import traceback

# ==========================================
# 1. НАСТРОЙКИ УПАКОВЩИКА (Строго до 19 МБ)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Папка с вашими исходными .jar модами
SOURCE_MODS_DIR = os.path.join(BASE_DIR, "mods")

# Папка с готовыми кусочками по 19 МБ для загрузки в браузер GitHub
UPLOAD_DIR = os.path.join(BASE_DIR, "ЗАГРУЗИТЬ_НА_GITHUB")

# Прямая ссылка на ваш репозиторий GitHub
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/Bananchik33/mc-server-cloud/main/"

# ЖЕСТКИЙ ЛИМИТ РАЗМЕРА КУСКА: 19 Мегабайт (19 * 1024 * 1024 байт)
# Ни один файл гарантированно не превысит этот размер!
CHUNK_SIZE_BYTES = 19 * 1024 * 1024


def get_md5(filepath):
    """Считает MD5-хэш файла"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def build_split_cloud():
    print(f"Рабочая папка: {BASE_DIR}\n")

    # 1. Проверяем наличие папки mods и .jar файлов
    if not os.path.exists(SOURCE_MODS_DIR):
        os.makedirs(SOURCE_MODS_DIR)
        print(f"[!] Папка 'mods' создана: {SOURCE_MODS_DIR}")
        print("[!] Положите туда ваши .jar моды и запустите скрипт еще раз!")
        os.startfile(SOURCE_MODS_DIR)
        return

    jar_files = [f for f in os.listdir(SOURCE_MODS_DIR) if f.lower().endswith(".jar")]
    if not jar_files:
        print(f"[!] ОШИБКА: В папке '{SOURCE_MODS_DIR}' нет ни одного .jar мода!")
        os.startfile(SOURCE_MODS_DIR)
        return

    # 2. Очищаем папку выгрузки от старых тяжелых файлов
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    for old_f in os.listdir(UPLOAD_DIR):
        old_path = os.path.join(UPLOAD_DIR, old_f)
        if os.path.isfile(old_path):
            os.remove(old_path)

    print(f"Найдено модов: {len(jar_files)} шт.")
    print("Этап 1/2: Упаковка всех модов во временный общий архив...")

    temp_full_zip = os.path.join(BASE_DIR, "_temp_full_mods.zip")
    mods_metadata = []

    # Собираем все моды в один временный ZIP
    with zipfile.ZipFile(temp_full_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in jar_files:
            filepath = os.path.join(SOURCE_MODS_DIR, filename)
            print(f"  + Добавлен мод: {filename}")
            zf.write(filepath, arcname=filename)
            mods_metadata.append({
                "name": filename,
                "md5": get_md5(filepath)
            })

    total_size_mb = os.path.getsize(temp_full_zip) / (1024 * 1024)
    print(f"\nОбщий вес архива: {total_size_mb:.1f} МБ.")
    print("Этап 2/2: Нарезка архива на ровные части строго по 19 МБ...\n")

    # 3. Разрезаем большой ZIP на куски ровно по 19 МБ
    chunks_info = []
    part_num = 1

    with open(temp_full_zip, "rb") as src_file:
        while True:
            chunk_data = src_file.read(CHUNK_SIZE_BYTES)
            if not chunk_data:
                break

            chunk_name = f"mods_chunk_{part_num}.bin"
            chunk_path = os.path.join(UPLOAD_DIR, chunk_name)

            with open(chunk_path, "wb") as out_chunk:
                out_chunk.write(chunk_data)

            chunk_md5 = hashlib.md5(chunk_data).hexdigest()
            chunk_size_mb = len(chunk_data) / (1024 * 1024)

            chunks_info.append({
                "name": chunk_name,
                "url": f"{GITHUB_RAW_BASE_URL}{chunk_name}",
                "md5": chunk_md5
            })
            print(f"  [ГОТОВ КУСОК #{part_num}] {chunk_name} — Вес: {chunk_size_mb:.2f} МБ (Лимит GitHub 25 МБ соблюден!)")
            part_num += 1

    # Удаляем временный гигантский архив
    if os.path.exists(temp_full_zip):
        os.remove(temp_full_zip)

    # 4. Создаем mods_manifest.json
    manifest_data = {
        "chunks": chunks_info,
        "mods": mods_metadata
    }
    manifest_path = os.path.join(UPLOAD_DIR, "mods_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(f"УСПЕХ! Создано частей: {len(chunks_info)} шт. (каждая НЕ БОЛЕЕ 19 МБ).")
    print(f"Папка с готовыми файлами сейчас откроется: {UPLOAD_DIR}")
    print("Просто перетащите ВСЕ файлы из неё в окно GitHub в браузере!")
    print("=" * 65)
    os.startfile(UPLOAD_DIR)


if __name__ == "__main__":
    try:
        build_split_cloud()
    except Exception:
        print("\n[КРИТИЧЕСКАЯ ОШИБКА]:")
        traceback.print_exc()

    print("\n" + "-" * 65)
    input("Нажмите Enter, чтобы закрыть это окно...")