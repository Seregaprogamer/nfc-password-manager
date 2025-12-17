import json
from typing import Optional, Dict, Any

# Для работы с Android API
from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method, cast
    from android import mActivity

    # Классы Android
    Context = autoclass('android.content.Context')
    NfcAdapter = autoclass('android.nfc.NfcAdapter')
    Intent = autoclass('android.content.Intent')
    PendingIntent = autoclass('android.app.PendingIntent')
    IntentFilter = autoclass('android.content.IntentFilter')
    Ndef = autoclass('android.nfc.tech.Ndef')
    NdefMessage = autoclass('android.nfc.NdefMessage')
    NdefRecord = autoclass('android.nfc.NdefRecord')
    Tag = autoclass('android.nfc.Tag')
    String = autoclass('java.lang.String')
    Toast = autoclass('android.widget.Toast')

    # MIME тип для наших данных
    MIME_TYPE = 'application/org.nfc.passwordmanager'

else:
    # Эмуляция для тестирования на ПК
    NfcAdapter = None
    MIME_TYPE = 'application/org.nfc.passwordmanager'


class AndroidNFCManager:
    """Менеджер NFC для Android"""

    def __init__(self):
        self.nfc_adapter = None
        self.pending_intent = None
        self.intent_filters = None
        self.tech_lists = None

        if platform == 'android':
            self.initialize_nfc()

    def initialize_nfc(self):
        """Инициализация NFC на Android"""
        if platform != 'android':
            return False

        try:
            # Получаем NFC адаптер
            self.nfc_adapter = NfcAdapter.getDefaultAdapter(mActivity)

            if self.nfc_adapter is None:
                print("NFC не поддерживается устройством")
                return False

            if not self.nfc_adapter.isEnabled():
                print("NFC отключен. Включите NFC в настройках.")
                # Можно показать уведомление пользователю
                self.show_toast("Включите NFC в настройках устройства")
                return False

            # Создаем PendingIntent
            intent = Intent(mActivity, mActivity.getClass())
            intent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)

            self.pending_intent = PendingIntent.getActivity(
                mActivity, 0, intent,
                PendingIntent.FLAG_MUTABLE if hasattr(PendingIntent, 'FLAG_MUTABLE') else 0
            )

            # Настраиваем фильтр для наших данных
            ndef_filter = IntentFilter(NfcAdapter.ACTION_NDEF_DISCOVERED)
            try:
                ndef_filter.addDataType(MIME_TYPE)
            except:
                # Если не получается добавить MIME тип, фильтруем по всем данным
                ndef_filter.addDataType("*/*")

            self.intent_filters = [ndef_filter]
            self.tech_lists = [["android.nfc.tech.Ndef"]]

            return True

        except Exception as e:
            print(f"Ошибка инициализации NFC: {e}")
            return False

    def enable_foreground_dispatch(self):
        """Включить обработку NFC, когда приложение на переднем плане"""
        if platform != 'android' or not self.nfc_adapter:
            return False

        try:
            self.nfc_adapter.enableForegroundDispatch(
                mActivity,
                self.pending_intent,
                self.intent_filters,
                self.tech_lists
            )
            return True
        except Exception as e:
            print(f"Ошибка enableForegroundDispatch: {e}")
            return False

    def disable_foreground_dispatch(self):
        """Отключить обработку NFC"""
        if platform != 'android' or not self.nfc_adapter:
            return

        try:
            self.nfc_adapter.disableForegroundDispatch(mActivity)
        except Exception as e:
            print(f"Ошибка disableForegroundDispatch: {e}")

    def write_to_tag(self, data: str, tag: Any) -> bool:
        """Запись данных на NFC метку"""
        if platform != 'android':
            return False

        try:
            # Создаем NDEF сообщение
            mime_bytes = data.encode('utf-8')

            # Создаем NDEF запись
            mime_record = NdefRecord.createMime(MIME_TYPE, mime_bytes)

            # Создаем NDEF сообщение
            ndef_message = NdefMessage([mime_record])

            # Получаем NDEF объект из метки
            ndef = Ndef.get(tag)

            if ndef is None:
                print("Метка не поддерживает NDEF")
                return False

            # Подключаемся к метке
            ndef.connect()

            # Проверяем, доступна ли метка для записи
            if not ndef.isWritable():
                print("Метка доступна только для чтения")
                ndef.close()
                return False

            # Записываем данные
            ndef.writeNdefMessage(ndef_message)

            # Закрываем соединение
            ndef.close()

            return True

        except Exception as e:
            print(f"Ошибка записи на метку: {e}")
            return False

    def read_from_tag(self, tag: Any) -> Optional[str]:
        """Чтение данных с NFC метки"""
        if platform != 'android':
            return None

        try:
            # Получаем NDEF объект из метки
            ndef = Ndef.get(tag)

            if ndef is None:
                print("Метка не поддерживает NDEF")
                return None

            # Подключаемся к метке
            ndef.connect()

            # Читаем NDEF сообщение
            ndef_message = ndef.getNdefMessage()

            if ndef_message is None:
                print("На метке нет данных")
                ndef.close()
                return None

            # Получаем записи
            records = ndef_message.getRecords()

            for record in records:
                # Проверяем MIME тип
                tnf = record.getTnf()
                if tnf == NdefRecord.TNF_MIME_MEDIA:
                    mime_type = String(record.getType()).toString()
                    if mime_type == MIME_TYPE:
                        # Получаем данные
                        payload = record.getPayload()
                        data = String(payload, "UTF-8").toString()
                        ndef.close()
                        return data

            ndef.close()
            return None

        except Exception as e:
            print(f"Ошибка чтения метки: {e}")
            return None

    def show_toast(self, message: str):
        """Показать всплывающее уведомление на Android"""
        if platform != 'android':
            print(f"Toast: {message}")
            return

        try:
            Toast.makeText(mActivity, message, Toast.LENGTH_SHORT).show()
        except:
            pass

    def is_nfc_available(self) -> bool:
        """Проверка доступности NFC"""
        if platform != 'android':
            return False

        if self.nfc_adapter is None:
            return False

        return self.nfc_adapter.isEnabled()

    def open_nfc_settings(self):
        """Открыть настройки NFC"""
        if platform != 'android':
            return

        try:
            intent = Intent(NfcAdapter.ACTION_NFC_SETTINGS)
            mActivity.startActivity(intent)
        except:
            pass


# Синглтон для доступа к NFC менеджеру
nfc_manager = AndroidNFCManager()