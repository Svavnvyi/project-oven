from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout

from player import Player


class GameWorld(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_keys = set()

        self.player = Player()
        self.add_widget(self.player)

        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        if self._keyboard:
            self._keyboard.bind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)

        self.bind(size=self._center_player)
        Clock.schedule_interval(self.update, 1 / 60.0)

    def _center_player(self, *_):
        self.player.center = self.center

    def _on_keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)
        self._keyboard = None

    def _on_key_down(self, _keyboard, keycode, _text, _modifiers):
        self.active_keys.add(keycode[1].lower())
        return True

    def _on_key_up(self, _keyboard, keycode):
        self.active_keys.discard(keycode[1].lower())
        return True

    def update(self, dt):
        self.player.update(dt, self.active_keys, self.width, self.height)


class FridgeGameApp(App):
    def build(self):
        Window.clearcolor = (0.08, 0.08, 0.1, 1)
        return GameWorld()


if __name__ == "__main__":
    FridgeGameApp().run()
