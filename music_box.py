import numpy as np
import pygame
import time
import random
from threading import Thread, Lock
from scipy.signal import butter, lfilter


class HybridInstrument:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        self.sample_rate = 44100
        self.is_playing = False
        self.active_sounds = []

        self._cache = {}
        self._cache_lock = Lock()

        self.notes = {
            'E2': 82.41, 'F2': 87.31, 'F#2': 92.50, 'G2': 98.00,
            'A2': 110.00, 'A#2': 116.54, 'Bb2': 116.54, 'B2': 123.47,
            'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56,
            'Eb3': 155.56, 'E3': 164.81, 'F3': 174.61, 'F#3': 185.00,
            'G3': 196.00, 'G#3': 207.65, 'A3': 220.00, 'A#3': 233.08,
            'Bb3': 233.08, 'B3': 246.94,
            'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13,
            'E4': 329.63, 'F4': 349.23, 'F#4': 369.99, 'G4': 392.00,
            'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'Bb4': 466.16,
            'B4': 493.88,
            'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'E5': 659.25,
            'F5': 698.46, 'G5': 783.99, 'A5': 880.00,
        }

        # Радостные прогрессии — больше мажора, меньше минора
        self.chord_progressions = [
            ['C', 'G', 'Am', 'F'],      # I-V-vi-IV — "счастливая" поп-прогрессия
            ['G', 'D', 'Em', 'C'],      # тот же паттерн в G
            ['F', 'C', 'Dm', 'Bb'],     # тёплый, "ламповый"
            ['C', 'Am', 'F', 'G'],      # 50s прогрессия
            ['C', 'F', 'G', 'C'],       # чистый мажор
            ['G', 'C', 'D', 'G'],       # народно-радостная
            ['Am', 'F', 'C', 'G'],      # меланхоличная, но светлая
            ['Dm', 'G', 'C', 'F'],      # джазовая, тёплая
        ]

        # Аккорды для арпеджио — более высокий регистр, добавлены "цветные" ноты
        self.chords = {
            'C':  ['C4', 'E4', 'G4', 'C5', 'E5', 'G5'],
            'G':  ['G3', 'B3', 'D4', 'G4', 'B4', 'D5'],
            'D':  ['D4', 'F#4', 'A4', 'D5', 'F#5'],
            'Am': ['A3', 'C4', 'E4', 'A4', 'C5', 'E5'],
            'Em': ['E3', 'G3', 'B3', 'E4', 'G4', 'B4'],
            'Dm': ['D4', 'F4', 'A4', 'D5', 'F5'],
            'F':  ['F3', 'A3', 'C4', 'F4', 'A4', 'C5'],
            'Bb': ['Bb3', 'D4', 'F4', 'Bb4', 'D5'],
            'A':  ['A3', 'C#4', 'E4', 'A4', 'C#5'],
            'Cm': ['C4', 'Eb3', 'G4', 'C5'],
        }

        # Пэд теперь выше — обволакивает, а не давит
        self.pad_chords = {
            'C':  ['C3', 'E3', 'G3', 'C4'],
            'G':  ['G3', 'B3', 'D4', 'G4'],
            'D':  ['D3', 'F#3', 'A3', 'D4'],
            'Am': ['A3', 'C4', 'E4', 'A4'],
            'Em': ['E3', 'G3', 'B3', 'E4'],
            'Dm': ['D3', 'F3', 'A3', 'D4'],
            'F':  ['F3', 'A3', 'C4', 'F4'],
            'Bb': ['Bb3', 'D4', 'F4', 'Bb4'],
            'A':  ['A3', 'C#4', 'E4', 'A4'],
            'Cm': ['C3', 'Eb3', 'G3', 'C4'],
        }

        # Паттерны с восходящим движением — даёт ощущение полёта
        self.patterns = [
            [0, 2, 4, 5, 4, 2],
            [0, 1, 2, 3, 4, 5],
            [0, 2, 4, 2, 5, 3],
            [0, 3, 1, 4, 2, 5],
            [4, 2, 0, 2, 3, 5],
            [0, 2, 4, 3, 5, 4, 2, 1],
        ]

    # ============= УТИЛИТЫ =============

    def _fade_edges(self, wave, fade_samples=512):
        f = min(fade_samples, len(wave) // 20)
        if f > 0:
            wave[:f] *= np.linspace(0, 1, f)
            wave[-f:] *= np.linspace(1, 0, f)
        return wave

    def _butter_lowpass(self, signal, cutoff, order=2):
        ny = self.sample_rate / 2
        b, a = butter(order, min(cutoff / ny, 0.99), btype='low')
        return lfilter(b, a, signal)

    def _to_stereo_int16(self, mono, pan=0.0):
        left = mono * (1 - pan) * 0.95
        right = mono * (1 + pan) * 0.95
        stereo = np.column_stack((left, right))
        return (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

    # ============= КОЛОКОЛЬЧИК =============

    def generate_bell(self, frequency, duration=3.0, volume=0.4):
        """Мягкий тёплый колокольчик — меньше высоких обертонов"""
        try:
            t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)

            # Более тёплый набор обертонов — высокие "звенящие" ослаблены
            partials = [
                (0.5,   0.35, 1.0),   # суб — тепло
                (1.0,   1.0,  1.3),   # основной тон
                (2.0,   0.45, 2.2),   # октава — поёт
                (2.76,  0.35, 2.8),   # колокольность, но мягче
                (3.0,   0.20, 3.5),   # квинта над октавой — мажорный оттенок
                (5.40,  0.10, 5.5),   # звон — тише, чтоб не резало
                (8.93,  0.04, 7.5),   # блеск — почти невидимый
            ]

            wave = np.zeros_like(t)
            for ratio, amp, decay in partials:
                f = frequency * ratio
                if f < self.sample_rate / 2:
                    envelope = np.exp(-decay * t / duration * 3)
                    phase = 2 * np.pi * f * t + random.uniform(0, 2 * np.pi)
                    wave += amp * np.sin(phase) * envelope

            # Мягкая атака (8 мс вместо 3) — менее "стеклянно", более "колокольно"
            attack_samples = int(0.008 * self.sample_rate)
            if attack_samples > 0:
                wave[:attack_samples] *= np.linspace(0, 1, attack_samples) ** 0.6

            # Сильнее срезаем верх — теплее
            wave = self._butter_lowpass(wave, 5000)

            wave = self._bell_reverb(wave, wet=0.3)

            max_val = np.max(np.abs(wave))
            if max_val > 0:
                wave = wave / max_val * volume

            wave = self._fade_edges(wave)

            pan = random.uniform(-0.3, 0.3)
            return self._to_stereo_int16(wave, pan)

        except Exception as e:
            print(f"Bell error: {e}")
            return None

    def _bell_reverb(self, signal, wet=0.3):
        try:
            comb_delays = [1557, 1617, 1491, 1422]
            comb_gains = [0.82, 0.81, 0.83, 0.80]
            wet_sig = np.zeros_like(signal)
            for delay, gain in zip(comb_delays, comb_gains):
                b = np.zeros(delay + 1); b[0] = 1.0
                a = np.zeros(delay + 1); a[0] = 1.0; a[delay] = -gain
                wet_sig += lfilter(b, a, signal) / len(comb_delays)
            for delay, gain in [(225, 0.7), (556, 0.7)]:
                b = np.zeros(delay + 1); b[0] = -gain; b[delay] = 1.0
                a = np.zeros(delay + 1); a[0] = 1.0;   a[delay] = -gain
                wet_sig = lfilter(b, a, wet_sig)
            return signal * (1 - wet) + wet_sig * wet
        except Exception:
            return signal

    # ============= ПЭД =============

    def generate_pad_chord(self, note_names, duration=7.0, volume=0.5):
        """Тёплый светлый пэд"""
        try:
            n = int(self.sample_rate * duration)
            t = np.linspace(0, duration, n, endpoint=False)
            wave = np.zeros_like(t)

            for note in note_names:
                freq = self.notes.get(note)
                if freq is None:
                    continue

                detune = 0.004
                osc = (
                    np.sin(2 * np.pi * freq * t) +
                    np.sin(2 * np.pi * freq * (1 + detune) * t) +
                    np.sin(2 * np.pi * freq * (1 - detune) * t)
                ) / 3.0

                osc += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
                osc += 0.18 * np.sin(2 * np.pi * freq * 3 * t)

                lfo_rate = random.uniform(0.15, 0.4)
                lfo_phase = random.uniform(0, 2 * np.pi)
                lfo = 1.0 + 0.15 * np.sin(2 * np.pi * lfo_rate * t + lfo_phase)
                osc *= lfo

                wave += osc

            wave /= max(len(note_names), 1)

            # Более яркий фильтр — пэд "светится"
            sweep_lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)
            dark = self._butter_lowpass(wave, 1200)
            bright = self._butter_lowpass(wave, 4000)
            wave = dark * (1 - sweep_lfo) + bright * sweep_lfo

            envelope = np.ones(n)
            fade_in = int(0.25 * n)
            fade_out = int(0.35 * n)
            envelope[:fade_in] = np.linspace(0, 1, fade_in) ** 1.5
            envelope[-fade_out:] = np.linspace(1, 0, fade_out) ** 1.5
            wave *= envelope

            wave = self._long_reverb(wave)

            max_val = np.max(np.abs(wave))
            if max_val > 0:
                wave = wave / max_val * volume

            wave = self._fade_edges(wave, fade_samples=2048)

            left = wave * 0.95
            right_shift = int(0.012 * self.sample_rate)
            right = np.concatenate([np.zeros(right_shift), wave])[:n] * 0.95
            stereo = np.column_stack((left, right))
            return (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

        except Exception as e:
            print(f"Pad error: {e}")
            return None

    def _long_reverb(self, signal, wet=0.4):
        try:
            comb_delays = [2205, 2469, 2690, 2998, 3175, 3439]
            comb_gains = [0.86, 0.85, 0.84, 0.83, 0.82, 0.81]
            wet_sig = np.zeros_like(signal)
            for delay, gain in zip(comb_delays, comb_gains):
                b = np.zeros(delay + 1); b[0] = 1.0
                a = np.zeros(delay + 1); a[0] = 1.0; a[delay] = -gain
                wet_sig += lfilter(b, a, signal) / len(comb_delays)
            for delay, gain in [(225, 0.7), (556, 0.7), (1013, 0.6)]:
                b = np.zeros(delay + 1); b[0] = -gain; b[delay] = 1.0
                a = np.zeros(delay + 1); a[0] = 1.0;   a[delay] = -gain
                wet_sig = lfilter(b, a, wet_sig)
            return signal * (1 - wet) + wet_sig * wet
        except Exception:
            return signal

    # ============= КЭШ =============

    def _get_bell(self, note_name, dur_key):
        key = ('bell', note_name, dur_key)
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]
        freq = self.notes.get(note_name)
        if freq is None:
            return None
        data = self.generate_bell(freq, dur_key, volume=0.4)
        if data is not None:
            with self._cache_lock:
                self._cache[key] = data
        return data

    def _get_pad(self, chord_name, dur_key):
        key = ('pad', chord_name, dur_key)
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]
        notes = self.pad_chords.get(chord_name)
        if not notes:
            return None
        data = self.generate_pad_chord(notes, dur_key, volume=0.5)
        if data is not None:
            with self._cache_lock:
                self._cache[key] = data
        return data

    # ============= ВОСПРОИЗВЕДЕНИЕ =============

    def play_bell(self, note_name, velocity=1.0, is_downbeat=False):
        try:
            data = self._get_bell(note_name, 3.0)
            if data is None:
                return
            s = pygame.sndarray.make_sound(data)
            # Колокольчик тише — не бьёт по ушам
            vol = velocity * (1.1 if is_downbeat else 0.85) * 0.15
            s.set_volume(min(vol, 1.0))
            s.play()
            self.active_sounds.append(s)
            if len(self.active_sounds) > 40:
                self.active_sounds = self.active_sounds[-20:]
        except Exception as e:
            print(f"Bell play error: {e}")

    def play_pad(self, chord_name):
        try:
            data = self._get_pad(chord_name, 7.0)
            if data is None:
                return
            s = pygame.sndarray.make_sound(data)
            # Пэд громче — он теперь основа
            s.set_volume(0.2)
            s.play()
            self.active_sounds.append(s)
        except Exception as e:
            print(f"Pad play error: {e}")

    def mute_active_sounds(self):
        for sound in self.active_sounds:
            try:
                sound.fadeout(500)
            except Exception:
                pass
        self.active_sounds.clear()

    def play_chord_pattern(self, chord_name, pattern):
        if not self.is_playing or chord_name not in self.chords:
            return

        self.play_pad(chord_name)

        chord_notes = self.chords[chord_name]
        for step_idx, step in enumerate(pattern):
            if not self.is_playing:
                break
            if step < len(chord_notes):
                note = chord_notes[step]
                velocity = random.uniform(0.7, 1.0)
                is_downbeat = (step_idx == 0)
                self.play_bell(note, velocity, is_downbeat)

                # Темп чуть бодрее
                wait = random.uniform(0.28, 0.42)
                if random.random() < 0.12:
                    wait += random.uniform(0.08, 0.18)
                time.sleep(wait)

    def warmup_cache(self):
        try:
            unique_notes = set()
            for chord_notes in self.chords.values():
                unique_notes.update(chord_notes)
            for note in unique_notes:
                if not self.is_playing:
                    break
                self._get_bell(note, 3.0)
            for chord in self.chords.keys():
                if not self.is_playing:
                    break
                self._get_pad(chord, 7.0)
        except Exception as e:
            print(f"Warmup error: {e}")

    def eternal_melody(self):
        self.is_playing = True
        progression_count = 0

        print("🔔 Светлая музыкальная шкатулка запущена...")
        print("⏳ Идёт прогрев кэша...")

        Thread(target=self.warmup_cache, daemon=True).start()

        while self.is_playing:
            progression_count += 1
            progression = random.choice(self.chord_progressions)
            pattern = random.choice(self.patterns)

            print(f"\n🎶 Прогрессия #{progression_count}: {' → '.join(progression)}")

            for chord in progression:
                if not self.is_playing:
                    break
                print(f"   {chord} (🔔+🌊)...", end=" ", flush=True)
                self.play_chord_pattern(chord, pattern)
                print()

            if self.is_playing:
                # Короткие паузы — меньше "уныния"
                pause = random.uniform(0.6, 1.2)
                print(f"⏸️  Пауза: {pause:.1f}с")
                time.sleep(pause)

    def start(self):
        print("=" * 60)
        print("🔔 СВЕТЛАЯ МУЗЫКАЛЬНАЯ ШКАТУЛКА")
        print("=" * 60)
        print("✨ Тёплый пэд + мягкие колокольчики")
        print("🌞 Мажорные прогрессии, восходящие паттерны")
        print()
        print("⏹️  Нажмите Enter для остановки")
        print("-" * 60)

        self.thread = Thread(target=self.eternal_melody, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_playing = False
        self.mute_active_sounds()
        print("\n💤 Музыка остановлена")


if __name__ == "__main__":
    instrument = None
    try:
        instrument = HybridInstrument()
        instrument.start()
        input()
    except KeyboardInterrupt:
        print("\n🎵 Остановлено")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if instrument is not None:
            instrument.stop()
        pygame.mixer.quit()
