[app]

# Название приложения
title = NFC Password Manager

# Имя пакета
package.name = nfcpasswordmanager

# Домен пакета
package.domain = org.nfc

# Исходная директория
source.dir = .

# Включить файлы с расширениями
source.include_exts = py,png,jpg,kv,atlas,json

# Главный файл приложения
source.main = main.py

# Версия приложения
version = 1.0

# Требования
requirements = python3,kivy==2.3.0,pycryptodome,pyjnius,android

# Разрешения Android
android.permissions = NFC,INTERNET

# Функции NFC
android.features = android.hardware.nfc,android.hardware.nfc.hce

# Минимальная версия Android
android.minapi = 21

# Целевая версия Android
android.api = 33

# Архитектура (arm64-v8a лучше для современных телефонов)
android.arch = arm64-v8a

# Ориентация экрана
orientation = portrait

# Полноэкранный режим
fullscreen = 0

# Иконка (создайте файл icon.png 512x512 в папке проекта)
# icon.filename = icon.png

# Заставка при запуске
# presplash.filename = presplash.png

# Логирование
log_level = 2

# Окно
window.numwindows = 1
window.width = 360
window.height = 640