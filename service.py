"""
Service для обработки Android Intent
"""

from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method


    # Создаем Java класс для обработки NFC
    class NfcIntentHandler(PythonJavaClass):
        __javacontext__ = 'application'

        def __init__(self, callback=None):
            super().__init__()
            self.callback = callback

        @java_method('(Landroid/content/Intent;)V')
        def onNewIntent(self, intent):
            print("Получен новый Intent в NfcIntentHandler")
            if self.callback:
                self.callback(intent)


    # Создаем обработчик
    nfc_intent_handler = NfcIntentHandler()


    # Функция для установки обработчика
    def setup_intent_handler(callback):
        global nfc_intent_handler
        nfc_intent_handler = NfcIntentHandler(callback)

        # Регистрируем обработчик в активности
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            activity.nfc_handler = nfc_intent_handler
        except Exception as e:
            print(f"Ошибка настройки обработчика Intent: {e}")

else:
    # Заглушка для не-Android платформ
    def setup_intent_handler(callback):
        print("Эмуляция: обработчик Intent установлен")