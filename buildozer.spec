[app]
title = NFC Password Manager
package.name = nfcpasswordmanager
package.domain = org.nfc

source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,kv,atlas,json,txt

version = 1.0
requirements = python3,kivy==2.3.0,pycryptodome

android.permissions = NFC,INTERNET
android.features = android.hardware.nfc

android.minapi = 21
android.api = 30
android.arch = armeabi-v7a

orientation = portrait
fullscreen = 0
window.numwindows = 1
window.width = 360
window.height = 640

log_level = 2
