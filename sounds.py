from PySide6.QtCore import QUrl, QTimer
from PySide6.QtMultimedia import QSoundEffect

from utils import res_path

class SoundsEffects:
    def __init__(self):
        self.volume = 0.5
        self.cooldown_pop = False
        self.cooldown_swipe = False
        self.cooldown_short_pop = False
        self.cooldown_click_in = False
        self.cooldown_click_out = False
        self.cooldown_short_swipe = False
        self.cooldown_anti_pop = False

        self.sfx_pop = QSoundEffect()
        self.sfx_pop.setSource(QUrl.fromLocalFile(res_path("sounds/pop.wav")))
        self.sfx_pop.setVolume(0.5)

        self.sfx_swipe = QSoundEffect()
        self.sfx_swipe.setSource(QUrl.fromLocalFile(res_path("sounds/swipe.wav")))
        self.sfx_swipe.setVolume(0.5)

        self.sfx_short_pop = QSoundEffect()
        self.sfx_short_pop.setSource(QUrl.fromLocalFile(res_path("sounds/short_pop.wav")))
        self.sfx_short_pop.setVolume(0.5)

        self.sfx_click_in = QSoundEffect()
        self.sfx_click_in.setSource(QUrl.fromLocalFile(res_path("sounds/click_in.wav")))
        self.sfx_click_in.setVolume(0.5)

        self.sfx_click_out = QSoundEffect()
        self.sfx_click_out.setSource(QUrl.fromLocalFile(res_path("sounds/click_out.wav")))
        self.sfx_click_out.setVolume(0.5)

        self.sfx_short_swipe = QSoundEffect()
        self.sfx_short_swipe.setSource(QUrl.fromLocalFile(res_path("sounds/short_swipe.wav")))
        self.sfx_short_swipe.setVolume(0.5)

        self.sfx_anti_pop = QSoundEffect()
        self.sfx_anti_pop.setSource(QUrl.fromLocalFile(res_path("sounds/anti_pop.wav")))
        self.sfx_anti_pop.setVolume(0.5)

        self.sfx_prestart = QSoundEffect()
        self.sfx_prestart.setSource(QUrl.fromLocalFile(res_path("sounds/click_in.wav")))
        self.sfx_prestart.setVolume(0)

        self.all_sfx = [
            self.sfx_pop,
            self.sfx_swipe,
            self.sfx_short_pop,
            self.sfx_click_in,
            self.sfx_click_out,
            self.sfx_short_swipe,
            self.sfx_anti_pop
        ]

        self.prestart()

    def play_pop(self):
        if self.cooldown_pop:
            return

        self.cooldown_pop = True
        self.sfx_pop.play()

        QTimer.singleShot(60, lambda: setattr(self, "cooldown_pop", False))

    def play_swipe(self):
        if self.cooldown_swipe:
            return
        
        self.cooldown_swipe = True
        self.sfx_swipe.play()

        QTimer.singleShot(60, lambda: setattr(self, "cooldown_swipe", False))

    def play_short_pop(self):
        if self.cooldown_short_pop:
            return
        
        self.cooldown_short_pop = True
        self.sfx_short_pop.play()

        QTimer.singleShot(60, lambda: setattr(self, "cooldown_short_pop", False))

    def play_click_in(self):
        if self.cooldown_click_in:
            return
        
        self.cooldown_click_in = True
        self.sfx_click_in.play()

        QTimer.singleShot(60, lambda: setattr(self, "cooldown_click_in", False))

    def play_click_out(self):
        if self.cooldown_click_out:
            return
        
        self.cooldown_click_out = True
        self.sfx_click_out.play()

        QTimer.singleShot(60, lambda: setattr(self, "cooldown_click_out", False))

    def play_short_swipe(self):
        if self.cooldown_short_swipe:
            return
        
        self.cooldown_short_swipe = True
        self.sfx_short_swipe.play()

        QTimer.singleShot(60, lambda: setattr(self, "cooldown_short_swipe", False))

    def play_anti_pop(self):
        if self.cooldown_anti_pop:
            return
        
        self.cooldown_anti_pop = True
        self.sfx_anti_pop.play()

        QTimer.singleShot(60, lambda: setattr(self, "cooldown_anti_pop", False))

    def set_volume(self, volume: float):
        self.volume = volume
        for sfx in self.all_sfx:
            sfx.setVolume(self.volume)

    def prestart(self):
        self.sfx_prestart.play()
        self.sfx_prestart.play()
        self.sfx_prestart.play()