"""
NFC Password Manager - главное приложение
Запись и чтение паролей с NFC меток с шифрованием
"""

import os
import json
import base64
from datetime import datetime
from typing import Dict, List, Optional

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform

# Для шифрования
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import hashlib

# Импортируем NFC менеджер
try:
    from android_nfc import nfc_manager
    from service import setup_intent_handler
except ImportError:
    # Заглушки для тестирования на ПК
    class MockNFCManager:
        def enable_foreground_dispatch(self): return True

        def disable_foreground_dispatch(self): pass

        def is_nfc_available(self): return False

        def show_toast(self, msg): print(f"Toast: {msg}")

        def open_nfc_settings(self): print("Открыть настройки NFC")

        def process_intent(self, intent): return None

        def write_to_tag(self, data, tag): return True

        def read_from_tag(self, tag): return None


    nfc_manager = MockNFCManager()


    def setup_intent_handler(callback):
        print(f"Intent handler setup called with callback: {callback}")

# Конфигурация
CONFIG_FILE = 'nfc_passwords.json'
MASTER_PIN = "1234"


class PasswordManager:
    """Менеджер паролей"""

    def __init__(self):
        self.passwords = self.load_passwords()

    def load_passwords(self) -> Dict:
        """Загрузка паролей из файла"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Создаем пустой файл при первом запуске
                default_data = {}
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
                return default_data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка загрузки паролей: {e}")
            return {}

    def save_passwords(self):
        """Сохранение паролей в файл"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.passwords, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Ошибка сохранения паролей: {e}")

    def add_password(self, service: str, username: str, password: str):
        """Добавление нового пароля"""
        if service not in self.passwords:
            self.passwords[service] = []

        self.passwords[service].append({
            'username': username,
            'password': password,
            'created': datetime.now().isoformat()
        })
        self.save_passwords()

    def get_services(self) -> List[str]:
        """Получение списка сервисов"""
        return list(self.passwords.keys())


class EncryptionManager:
    """Менеджер шифрования"""

    @staticmethod
    def derive_key(pin: str) -> bytes:
        """Создание ключа из PIN"""
        return hashlib.sha256(pin.encode()).digest()

    @staticmethod
    def encrypt_data(data: str, pin: str) -> str:
        """Шифрование данных"""
        key = EncryptionManager.derive_key(pin)
        iv = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)

        encrypted = cipher.encrypt(pad(data.encode(), AES.block_size))
        result = base64.b64encode(iv + encrypted).decode()
        return result

    @staticmethod
    def decrypt_data(encrypted_data: str, pin: str) -> Optional[str]:
        """Расшифрование данных"""
        try:
            key = EncryptionManager.derive_key(pin)
            data = base64.b64decode(encrypted_data)

            iv = data[:16]
            encrypted = data[16:]

            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
            return decrypted.decode()
        except Exception as e:
            print(f"Ошибка дешифровки: {e}")
            return None


class LoginScreen(Screen):
    """Экран ввода PIN"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Темная тема
        Window.clearcolor = (0.1, 0.1, 0.1, 1)

        layout = BoxLayout(orientation='vertical', padding=50, spacing=30)

        # Заголовок
        title = Label(
            text='NFC Password Manager',
            font_size=36,
            size_hint_y=0.4,
            color=(1, 1, 1, 1)
        )

        # Поле для PIN
        self.pin_input = TextInput(
            hint_text='Введите PIN',
            hint_text_color=(0.7, 0.7, 0.7, 1),
            password=True,
            multiline=False,
            size_hint_y=0.2,
            font_size=28,
            background_color=(0.2, 0.2, 0.2, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            input_filter='int'
        )

        # Метка ошибки
        self.error_label = Label(
            text='',
            color=(1, 0.3, 0.3, 1),
            size_hint_y=0.1
        )

        # Кнопка входа
        login_btn = Button(
            text='ВОЙТИ',
            size_hint_y=0.3,
            font_size=24,
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1)
        )
        login_btn.bind(on_release=self.verify_pin)

        layout.add_widget(title)
        layout.add_widget(self.pin_input)
        layout.add_widget(self.error_label)
        layout.add_widget(login_btn)

        self.add_widget(layout)

    def verify_pin(self, instance):
        """Проверка PIN"""
        pin = self.pin_input.text.strip()
        if pin == MASTER_PIN:
            self.manager.current = 'main'
            self.pin_input.text = ""
        else:
            self.error_label.text = "Неверный PIN"
            Clock.schedule_once(self.clear_error, 2)

    def clear_error(self, dt):
        self.error_label.text = ""


class MainScreen(Screen):
    """Главный экран"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layout = BoxLayout(orientation='vertical')

        # Верхняя панель
        top_bar = BoxLayout(size_hint_y=0.12, padding=10)
        title = Label(
            text='Главное меню',
            font_size=28,
            color=(1, 1, 1, 1)
        )
        logout_btn = Button(
            text='Выход',
            size_hint_x=0.3,
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1)
        )
        logout_btn.bind(on_release=self.logout)
        top_bar.add_widget(title)
        top_bar.add_widget(logout_btn)

        # Список сервисов
        self.services_layout = GridLayout(cols=1, spacing=5, size_hint_y=None, padding=10)
        self.services_layout.bind(minimum_height=self.services_layout.setter('height'))

        scroll = ScrollView(size_hint=(1, 0.7))
        scroll.add_widget(self.services_layout)

        # Нижняя панель с кнопками
        bottom_bar = BoxLayout(size_hint_y=0.18, spacing=15, padding=10)

        write_btn = Button(
            text='[ Запись NFC ]',
            background_color=(0.2, 0.8, 0.2, 1),
            color=(1, 1, 1, 1),
            font_size=20
        )
        read_btn = Button(
            text='[ Чтение NFC ]',
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            font_size=20
        )

        write_btn.bind(on_release=self.go_to_write)
        read_btn.bind(on_release=self.go_to_read)

        bottom_bar.add_widget(write_btn)
        bottom_bar.add_widget(read_btn)

        self.layout.add_widget(top_bar)
        self.layout.add_widget(scroll)
        self.layout.add_widget(bottom_bar)

        self.add_widget(self.layout)

    def on_enter(self):
        """Обновление списка сервисов при входе"""
        self.update_service_list()

    def update_service_list(self):
        """Обновление списка сервисов"""
        app = App.get_running_app()
        services = app.password_manager.get_services()

        self.services_layout.clear_widgets()

        if not services:
            label = Label(
                text='Нет сохраненных паролей\n\nНажмите "[ Запись NFC ]"\nчтобы добавить первый пароль',
                size_hint_y=None,
                height=150,
                color=(0.7, 0.7, 0.7, 1),
                halign='center',
                valign='middle'
            )
            label.bind(size=label.setter('text_size'))
            self.services_layout.add_widget(label)
            return

        for service in services:
            btn = Button(
                text=f'● {service}',
                size_hint_y=None,
                height=60,
                background_color=(0.3, 0.3, 0.5, 1),
                color=(1, 1, 1, 1),
                font_size=18
            )
            btn.bind(on_release=lambda x, s=service: self.show_service_details(s))
            self.services_layout.add_widget(btn)

    def show_service_details(self, service: str):
        """Показать детали сервиса"""
        app = App.get_running_app()
        passwords = app.password_manager.passwords.get(service, [])

        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        content.add_widget(Label(
            text=f'● {service}',
            font_size=24,
            color=(0.2, 0.8, 1, 1),
            size_hint_y=0.2
        ))

        scroll_content = GridLayout(cols=1, spacing=5, size_hint_y=None)
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        if not passwords:
            scroll_content.add_widget(Label(
                text='Нет сохраненных паролей',
                color=(0.7, 0.7, 0.7, 1)
            ))

        for i, pwd in enumerate(passwords, 1):
            entry_box = BoxLayout(orientation='vertical', spacing=2, size_hint_y=None, height=80)

            user_label = Label(
                text=f'Логин: {pwd["username"]}',
                color=(1, 1, 1, 1),
                halign='left',
                size_hint_y=0.5
            )
            user_label.bind(size=user_label.setter('text_size'))

            pass_label = Label(
                text=f'Пароль: {"*" * 10}',
                color=(0.7, 0.7, 0.7, 1),
                halign='left',
                size_hint_y=0.3
            )
            pass_label.bind(size=pass_label.setter('text_size'))

            date_label = Label(
                text=f'Дата: {pwd["created"][:10]}',
                color=(0.5, 0.5, 0.5, 1),
                font_size=12,
                halign='left',
                size_hint_y=0.2
            )
            date_label.bind(size=date_label.setter('text_size'))

            entry_box.add_widget(user_label)
            entry_box.add_widget(pass_label)
            entry_box.add_widget(date_label)
            scroll_content.add_widget(entry_box)

        scroll_view = ScrollView(size_hint=(1, 0.7))
        scroll_view.add_widget(scroll_content)

        close_btn = Button(
            text='Закрыть',
            size_hint_y=0.15,
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1)
        )

        content.add_widget(scroll_view)
        content.add_widget(close_btn)

        popup = Popup(
            title='',
            content=content,
            size_hint=(0.85, 0.85),
            background_color=(0.15, 0.15, 0.15, 1)
        )
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def logout(self, instance):
        self.manager.current = 'login'

    def go_to_write(self, instance):
        self.manager.current = 'write'

    def go_to_read(self, instance):
        self.manager.current = 'read'


class WriteNFCScreen(Screen):
    """Экран записи на NFC"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Данные для записи
        self.encrypted_data_to_write = None

        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Верхняя панель
        top_bar = BoxLayout(size_hint_y=0.1, padding=5)
        title = Label(
            text='Запись на NFC',
            font_size=26,
            color=(1, 1, 1, 1)
        )
        back_btn = Button(
            text='← Назад',
            size_hint_x=0.3,
            background_color=(0.5, 0.5, 0.5, 1),
            color=(1, 1, 1, 1)
        )
        back_btn.bind(on_release=self.go_back)
        top_bar.add_widget(title)
        top_bar.add_widget(back_btn)

        # Форма
        form_layout = BoxLayout(orientation='vertical', spacing=10, padding=20)

        # Поля ввода
        fields = [
            ('service_input', 'Сервис (например: gmail.com)'),
            ('username_input', 'Имя пользователя'),
            ('password_input', 'Пароль'),
            ('pin_input', 'PIN для шифрования (4 цифры)')
        ]

        for field_name, hint in fields:
            label = Label(
                text=hint,
                size_hint_y=0.1,
                color=(0.8, 0.8, 0.8, 1),
                halign='left'
            )
            label.bind(size=label.setter('text_size'))
            form_layout.add_widget(label)

            is_password = 'Пароль' in hint or 'PIN' in hint
            text_input = TextInput(
                multiline=False,
                size_hint_y=0.15,
                background_color=(0.2, 0.2, 0.2, 1),
                foreground_color=(1, 1, 1, 1),
                cursor_color=(1, 1, 1, 1),
                password=is_password
            )

            if 'PIN' in hint:
                text_input.input_filter = 'int'

            setattr(self, field_name, text_input)
            form_layout.add_widget(text_input)

        # Статус сообщение
        self.status_label = Label(
            text='',
            size_hint_y=0.2,
            color=(0, 1, 0, 1),
            halign='center',
            valign='middle'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        form_layout.add_widget(self.status_label)

        # Кнопка записи
        write_btn = Button(
            text='ПОДГОТОВИТЬ ДАННЫЕ',
            size_hint_y=0.2,
            background_color=(0.2, 0.8, 0.2, 1),
            color=(1, 1, 1, 1),
            font_size=22
        )
        write_btn.bind(on_release=self.prepare_data_for_write)

        self.layout.add_widget(top_bar)
        self.layout.add_widget(form_layout)
        self.layout.add_widget(write_btn)

        self.add_widget(self.layout)

    def on_enter(self):
        """При входе на экран включить NFC"""
        print("Вход на экран записи NFC")
        if platform == 'android':
            if not nfc_manager.is_nfc_available():
                self.show_message("Включите NFC в настройках устройства!", (1, 0.3, 0.3, 1))
                # Показать предупреждение через секунду
                Clock.schedule_once(self.show_nfc_warning, 1)
            else:
                success = nfc_manager.enable_foreground_dispatch()
                if success:
                    self.show_message("Готово к записи. Поднесите NFC метку", (0.3, 1, 0.3, 1))
                else:
                    self.show_message("Не удалось включить NFC", (1, 0.3, 0.3, 1))
        else:
            self.show_message("Эмуляционный режим NFC", (1, 1, 0.3, 1))

    def on_leave(self):
        """При выходе с экрана отключить NFC"""
        if platform == 'android':
            nfc_manager.disable_foreground_dispatch()

    def show_nfc_warning(self, dt):
        """Показать предупреждение о выключенном NFC"""
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)
        content.add_widget(Label(
            text='NFC выключен',
            font_size=24,
            color=(1, 1, 1, 1)
        ))
        content.add_widget(Label(
            text='Для работы с NFC метками\nнеобходимо включить NFC\nв настройках устройства',
            halign='center'
        ))

        btn_layout = BoxLayout(size_hint_y=0.4, spacing=10)
        settings_btn = Button(text='Открыть настройки')
        cancel_btn = Button(text='Позже')

        def open_settings(instance):
            nfc_manager.open_nfc_settings()
            popup.dismiss()

        settings_btn.bind(on_release=open_settings)
        cancel_btn.bind(on_release=popup.dismiss)

        btn_layout.add_widget(settings_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(
            title='',
            content=content,
            size_hint=(0.8, 0.5),
            background_color=(0.2, 0.2, 0.2, 1)
        )
        popup.open()

    def prepare_data_for_write(self, instance):
        """Подготовка данных для записи на NFC"""
        service = self.service_input.text.strip()
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        pin = self.pin_input.text.strip()

        # Валидация
        if not all([service, username, password, pin]):
            self.show_message("ОШИБКА: Заполните все поля!", (1, 0.3, 0.3, 1))
            return

        if len(pin) != 4 or not pin.isdigit():
            self.show_message("ОШИБКА: PIN должен быть 4 цифры!", (1, 0.3, 0.3, 1))
            return

        # Добавление в менеджер паролей
        app = App.get_running_app()
        app.password_manager.add_password(service, username, password)

        # Подготовка данных для записи
        data_to_write = json.dumps({
            'service': service,
            'username': username,
            'password': password
        })

        # Шифрование данных
        encrypted_data = EncryptionManager.encrypt_data(data_to_write, pin)

        # Сохраняем данные для записи
        self.encrypted_data_to_write = encrypted_data

        # Показываем результат
        self.show_message(
            f"Данные подготовлены!\n\n"
            f"Поднесите NFC метку к телефону\n"
            f"для записи данных.\n\n"
            f"Шифр (первые 30 символов):\n{encrypted_data[:30]}...",
            (0.3, 1, 0.3, 1)
        )

        # Обновление списка на главном экране
        Clock.schedule_once(lambda dt: self.update_main_screen(), 1)

        # Если не Android, эмулируем запись
        if platform != 'android':
            self.show_message("Эмуляция: Данные готовы к записи", (0.3, 1, 0.3, 1))
            print(f"Данные для записи: {encrypted_data}")

    def process_nfc_intent(self, intent):
        """Обработка NFC Intent для записи"""
        if not self.encrypted_data_to_write:
            self.show_message("Сначала подготовьте данные для записи", (1, 1, 0.3, 1))
            return

        tag = nfc_manager.process_intent(intent)
        if tag:
            success = nfc_manager.write_to_tag(self.encrypted_data_to_write, tag)
            if success:
                self.show_message("ДАННЫЕ ЗАПИСАНЫ НА NFC МЕТКУ!", (0.3, 1, 0.3, 1))
                nfc_manager.show_toast("Данные записаны успешно!")

                # Очищаем данные
                self.encrypted_data_to_write = None
                self.clear_fields(None)
            else:
                self.show_message("ОШИБКА ЗАПИСИ НА МЕТКУ", (1, 0.3, 0.3, 1))

    def clear_fields(self, dt):
        """Очистка полей ввода"""
        self.service_input.text = ""
        self.username_input.text = ""
        self.password_input.text = ""
        self.pin_input.text = ""

    def show_message(self, message: str, color=(0.3, 1, 0.3, 1)):
        """Показать сообщение"""
        self.status_label.text = message
        self.status_label.color = color

    def update_main_screen(self):
        """Обновление главного экрана"""
        main_screen = self.manager.get_screen('main')
        main_screen.update_service_list()

    def go_back(self, instance):
        self.manager.current = 'main'


class ReadNFCScreen(Screen):
    """Экран чтения NFC"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Верхняя панель
        top_bar = BoxLayout(size_hint_y=0.1, padding=5)
        title = Label(
            text='Чтение NFC',
            font_size=26,
            color=(1, 1, 1, 1)
        )
        back_btn = Button(
            text='← Назад',
            size_hint_x=0.3,
            background_color=(0.5, 0.5, 0.5, 1),
            color=(1, 1, 1, 1)
        )
        back_btn.bind(on_release=self.go_back)
        top_bar.add_widget(title)
        top_bar.add_widget(back_btn)

        # Форма
        form_layout = BoxLayout(orientation='vertical', spacing=10, padding=20)

        # Поле для PIN
        pin_label = Label(
            text='Введите PIN для расшифровки (4 цифры):',
            size_hint_y=0.08,
            color=(0.8, 0.8, 0.8, 1),
            halign='left'
        )
        pin_label.bind(size=pin_label.setter('text_size'))
        form_layout.add_widget(pin_label)

        self.pin_input = TextInput(
            multiline=False,
            size_hint_y=0.1,
            background_color=(0.2, 0.2, 0.2, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            password=True,
            input_filter='int'
        )
        form_layout.add_widget(self.pin_input)

        # Поле для данных
        data_label = Label(
            text='Зашифрованные данные (считайте NFC или вставьте текст):',
            size_hint_y=0.08,
            color=(0.8, 0.8, 0.8, 1),
            halign='left'
        )
        data_label.bind(size=data_label.setter('text_size'))
        form_layout.add_widget(data_label)

        self.data_input = TextInput(
            multiline=True,
            size_hint_y=0.3,
            background_color=(0.2, 0.2, 0.2, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1)
        )
        form_layout.add_widget(self.data_input)

        # Кнопка для тестовых данных
        test_btn = Button(
            text='Вставить тестовые данные',
            size_hint_y=0.08,
            background_color=(0.4, 0.4, 0.6, 1),
            color=(1, 1, 1, 1)
        )
        test_btn.bind(on_release=self.insert_test_data)
        form_layout.add_widget(test_btn)

        # Статус сообщение
        self.status_label = Label(
            text='',
            size_hint_y=0.1,
            color=(1, 1, 0, 1),
            halign='center',
            valign='middle'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        form_layout.add_widget(self.status_label)

        # Кнопка чтения
        read_btn = Button(
            text='РАСШИФРОВАТЬ ДАННЫЕ',
            size_hint_y=0.15,
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            font_size=20
        )
        read_btn.bind(on_release=self.read_data)
        form_layout.add_widget(read_btn)

        # Результат
        result_label = Label(
            text='Результат:',
            size_hint_y=0.05,
            color=(0.8, 0.8, 0.8, 1),
            font_size=18,
            halign='left'
        )
        result_label.bind(size=result_label.setter('text_size'))
        form_layout.add_widget(result_label)

        self.result_text = Label(
            text='',
            size_hint_y=0.4,
            color=(1, 1, 1, 1),
            halign='left',
            valign='top'
        )
        self.result_text.bind(size=self.result_text.setter('text_size'))
        form_layout.add_widget(self.result_text)

        self.layout.add_widget(top_bar)
        self.layout.add_widget(form_layout)

        self.add_widget(self.layout)

    def on_enter(self):
        """При входе на экран включить NFC"""
        print("Вход на экран чтения NFC")
        if platform == 'android':
            if not nfc_manager.is_nfc_available():
                self.show_message("Включите NFC в настройках устройства!", (1, 0.3, 0.3, 1))
            else:
                success = nfc_manager.enable_foreground_dispatch()
                if success:
                    self.show_message("Готово к чтению. Поднесите NFC метку", (0.3, 1, 0.3, 1))
                else:
                    self.show_message("Не удалось включить NFC", (1, 0.3, 0.3, 1))
        else:
            self.show_message("Эмуляционный режим NFC", (1, 1, 0.3, 1))

    def on_leave(self):
        """При выходе с экрана отключить NFC"""
        if platform == 'android':
            nfc_manager.disable_foreground_dispatch()

    def process_nfc_intent(self, intent):
        """Обработка NFC Intent для чтения"""
        tag = nfc_manager.process_intent(intent)
        if tag:
            data = nfc_manager.read_from_tag(tag)
            if data:
                self.data_input.text = data
                self.show_message("ДАННЫЕ СЧИТАНЫ С NFC МЕТКИ!\nВведите PIN и нажмите 'РАСШИФРОВАТЬ ДАННЫЕ'",
                                  (0.3, 1, 0.3, 1))
                nfc_manager.show_toast("Данные считаны успешно!")
            else:
                self.show_message("НЕ УДАЛОСЬ СЧИТАТЬ ДАННЫЕ С МЕТКИ", (1, 0.3, 0.3, 1))

    def insert_test_data(self, instance):
        """Вставить тестовые данные для демонстрации"""
        # Создаем тестовые данные
        test_data = json.dumps({
            'service': 'example.com',
            'username': 'demo_user',
            'password': 'demo123'
        })
        test_encrypted = EncryptionManager.encrypt_data(test_data, "1234")

        self.data_input.text = test_encrypted
        self.pin_input.text = "1234"
        self.show_message("Тестовые данные загружены! Нажмите 'РАСШИФРОВАТЬ ДАННЫЕ'", (0.3, 1, 0.3, 1))

    def read_data(self, instance):
        """Чтение данных с NFC чипа"""
        pin = self.pin_input.text.strip()
        encrypted_data = self.data_input.text.strip()

        # Валидация
        if not pin:
            self.show_message("ОШИБКА: Введите PIN для расшифровки", (1, 0.3, 0.3, 1))
            return

        if len(pin) != 4 or not pin.isdigit():
            self.show_message("ОШИБКА: PIN должен быть 4 цифры!", (1, 0.3, 0.3, 1))
            return

        if not encrypted_data:
            self.show_message("ВНИМАНИЕ: Введите данные или нажмите 'Вставить тестовые данные'", (1, 1, 0.3, 1))
            return

        # Расшифровка данных
        decrypted = EncryptionManager.decrypt_data(encrypted_data, pin)

        if decrypted:
            try:
                data = json.loads(decrypted)

                # Форматируем результат
                result = f"УСПЕШНО РАСШИФРОВАНО!\n\n"
                result += f"Сервис: {data['service']}\n"
                result += f"Пользователь: {data['username']}\n"
                result += f"Пароль: {data['password']}\n\n"
                result += f"Данные сохранены в менеджер паролей"

                self.result_text.text = result
                self.show_message("Данные успешно расшифрованы и сохранены!", (0.3, 1, 0.3, 1))

                # Добавление в менеджер паролей
                app = App.get_running_app()
                app.password_manager.add_password(
                    data['service'],
                    data['username'],
                    data['password']
                )

                # Обновление списка на главном экране
                Clock.schedule_once(lambda dt: self.update_main_screen(), 1)

            except json.JSONDecodeError:
                self.result_text.text = "ОШИБКА: неверный формат данных"
                self.show_message("ОШИБКА: Не удалось распарсить данные", (1, 0.3, 0.3, 1))
        else:
            self.result_text.text = "ОШИБКА: неверный PIN или поврежденные данные"
            self.show_message("ОШИБКА: Неверный PIN или данные повреждены", (1, 0.3, 0.3, 1))

    def show_message(self, message: str, color=(1, 1, 0.3, 1)):
        """Показать сообщение"""
        self.status_label.text = message
        self.status_label.color = color

    def update_main_screen(self):
        """Обновление главного экрана"""
        main_screen = self.manager.get_screen('main')
        main_screen.update_service_list()

    def go_back(self, instance):
        self.manager.current = 'main'


class NFCPasswordManagerApp(App):
    """Главное приложение"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.password_manager = PasswordManager()
        self.screen_manager = ScreenManager()

    def build(self):
        """Сборка интерфейса"""
        # Настройка темного фона
        Window.clearcolor = (0.1, 0.1, 0.1, 1)

        # Создание экранов
        screens = {
            'login': LoginScreen(name='login'),
            'main': MainScreen(name='main'),
            'write': WriteNFCScreen(name='write'),
            'read': ReadNFCScreen(name='read')
        }

        for name, screen in screens.items():
            self.screen_manager.add_widget(screen)

        # Настраиваем обработчик Intent
        self.setup_intent_handling()

        return self.screen_manager

    def setup_intent_handling(self):
        """Настройка обработки Intent"""

        def intent_callback(intent):
            print(f"Callback Intent получен, текущий экран: {self.screen_manager.current}")

            # Передаем Intent текущему экрану
            current_screen = self.screen_manager.current_screen
            if current_screen:
                if hasattr(current_screen, 'process_nfc_intent'):
                    current_screen.process_nfc_intent(intent)
                else:
                    print(f"Экран {current_screen.name} не имеет метода process_nfc_intent")
            else:
                print("Нет текущего экрана")

        if platform == 'android':
            try:
                setup_intent_handler(intent_callback)
                print("Обработчик Intent настроен")
            except Exception as e:
                print(f"Ошибка настройки обработчика Intent: {e}")
        else:
            print("Эмуляционный режим: обработчик Intent не требуется")

    def on_start(self):
        """Вызывается при запуске приложения"""
        print("Приложение запущено")

        # Создаем тестовые данные при первом запуске (для отладки)
        if not self.password_manager.passwords:
            print("Создаю тестовые данные...")
            self.create_sample_data()

    def create_sample_data(self):
        """Создание тестовых данных для демонстрации"""
        from datetime import datetime

        sample_data = {
            "example.com": [{
                "username": "demo_user",
                "password": "demo123",
                "created": datetime.now().isoformat()
            }],
            "gmail.com": [{
                "username": "test@gmail.com",
                "password": "TestPassword123",
                "created": datetime.now().isoformat()
            }]
        }

        self.password_manager.passwords = sample_data
        self.password_manager.save_passwords()
        print("Тестовые данные созданы")

    def on_stop(self):
        """Вызывается при остановке приложения"""
        if platform == 'android':
            nfc_manager.disable_foreground_dispatch()
        print("Приложение остановлено")

    def on_pause(self):
        """При паузе приложения"""
        if platform == 'android':
            nfc_manager.disable_foreground_dispatch()
        return True

    def on_resume(self):
        """При возобновлении приложения"""
        if platform == 'android':
            current_screen = self.screen_manager.current_screen
            if current_screen and current_screen.name in ['write', 'read']:
                nfc_manager.enable_foreground_dispatch()


if __name__ == '__main__':
    NFCPasswordManagerApp().run()