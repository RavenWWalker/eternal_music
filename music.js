const NOTES = {
    'E2': 82.41, 'F2': 87.31, 'G2': 98.00, 'A2': 110.00,
    'B2': 123.47, 'Bb2': 116.54,
    'C3': 130.81, 'D3': 146.83, 'Eb3': 155.56, 'E3': 164.81,
    'F3': 174.61, 'F#3': 185.00, 'G3': 196.00, 'A3': 220.00,
    'Bb3': 233.08, 'B3': 246.94,
    'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'E4': 329.63,
    'F4': 349.23, 'F#4': 369.99, 'G4': 392.00, 'A4': 440.00,
    'Bb4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'E5': 659.25,
    'F5': 698.46, 'F#5': 739.99, 'G5': 783.99,
};

const CHORD_PROGRESSIONS = [
    ['C', 'G', 'Am', 'F'],
    ['G', 'D', 'Em', 'C'],
    ['F', 'C', 'Dm', 'Bb'],
    ['C', 'Am', 'F', 'G'],
    ['C', 'F', 'G', 'C'],
    ['Am', 'F', 'C', 'G'],
    ['Dm', 'G', 'C', 'F'],
];

const CHORDS = {
    'C':  ['C4', 'E4', 'G4', 'C5', 'E5', 'G5'],
    'G':  ['G3', 'B3', 'D4', 'G4', 'B4', 'D5'],
    'D':  ['D4', 'F#4', 'A4', 'D5', 'F#5'],
    'Am': ['A3', 'C4', 'E4', 'A4', 'C5', 'E5'],
    'Em': ['E3', 'G3', 'B3', 'E4', 'G4', 'B4'],
    'Dm': ['D4', 'F4', 'A4', 'D5', 'F5'],
    'F':  ['F3', 'A3', 'C4', 'F4', 'A4', 'C5'],
    'Bb': ['Bb3', 'D4', 'F4', 'Bb4', 'D5'],
};

const PAD_CHORDS = {
    'C':  ['C3', 'E3', 'G3', 'C4'],
    'G':  ['G3', 'B3', 'D4', 'G4'],
    'D':  ['D3', 'F#3', 'A3', 'D4'],
    'Am': ['A3', 'C4', 'E4', 'A4'],
    'Em': ['E3', 'G3', 'B3', 'E4'],
    'Dm': ['D3', 'F3', 'A3', 'D4'],
    'F':  ['F3', 'A3', 'C4', 'F4'],
    'Bb': ['Bb3', 'D4', 'F4', 'Bb4'],
};

const PATTERNS = [
    [0, 2, 4, 5, 4, 2],
    [0, 1, 2, 3, 4, 5],
    [0, 2, 4, 2, 5, 3],
    [0, 3, 1, 4, 2, 5],
    [4, 2, 0, 2, 3, 5],
];

class MusicBox {
    constructor() {
        this.audioCtx = null;
        this.masterGain = null;
        this.reverbNode = null;
        this.analyser = null;
        this.isPlaying = false;
        this.volume = 0.5;
        this.tempoMultiplier = 1.0;
        this.timeoutId = null;
    }

    async init() {
        if (this.audioCtx) return;
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();

        this.masterGain = this.audioCtx.createGain();
        this.masterGain.gain.value = this.volume;

        // Анализатор для визуализации
        this.analyser = this.audioCtx.createAnalyser();
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.85;

        this.masterGain.connect(this.analyser);
        this.analyser.connect(this.audioCtx.destination);

        this.reverbNode = this.audioCtx.createConvolver();
        this.reverbNode.buffer = this.createReverbImpulse(3.0, 2.5);

        const reverbGain = this.audioCtx.createGain();
        reverbGain.gain.value = 0.35;
        this.reverbNode.connect(reverbGain);
        reverbGain.connect(this.masterGain);

        this.dryGain = this.audioCtx.createGain();
        this.dryGain.gain.value = 0.7;
        this.dryGain.connect(this.masterGain);
    }

    createReverbImpulse(duration, decay) {
        const sampleRate = this.audioCtx.sampleRate;
        const length = sampleRate * duration;
        const impulse = this.audioCtx.createBuffer(2, length, sampleRate);
        for (let ch = 0; ch < 2; ch++) {
            const data = impulse.getChannelData(ch);
            for (let i = 0; i < length; i++) {
                data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay);
            }
        }
        return impulse;
    }

    playBell(noteName, velocity = 1.0) {
        const freq = NOTES[noteName];
        if (!freq) return;
        const now = this.audioCtx.currentTime;
        const duration = 3.0;
        const partials = [
            { ratio: 0.5,  amp: 0.35, decay: 1.0 },
            { ratio: 1.0,  amp: 1.0,  decay: 1.3 },
            { ratio: 2.0,  amp: 0.45, decay: 2.2 },
            { ratio: 2.76, amp: 0.35, decay: 2.8 },
            { ratio: 3.0,  amp: 0.20, decay: 3.5 },
            { ratio: 5.40, amp: 0.10, decay: 5.5 },
            { ratio: 8.93, amp: 0.04, decay: 7.5 },
        ];
        const bellGain = this.audioCtx.createGain();
        bellGain.gain.value = 0.18 * velocity;
        const filter = this.audioCtx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.value = 5000;
        const panner = this.audioCtx.createStereoPanner();
        panner.pan.value = (Math.random() - 0.5) * 0.6;
        bellGain.connect(filter);
        filter.connect(panner);
        panner.connect(this.dryGain);
        panner.connect(this.reverbNode);
        partials.forEach(p => {
            const f = freq * p.ratio;
            if (f >= this.audioCtx.sampleRate / 2) return;
            const osc = this.audioCtx.createOscillator();
            osc.type = 'sine';
            osc.frequency.value = f;
            const g = this.audioCtx.createGain();
            g.gain.setValueAtTime(0, now);
            g.gain.linearRampToValueAtTime(p.amp, now + 0.008);
            g.gain.exponentialRampToValueAtTime(0.0001, now + duration * (1.5 / p.decay));
            osc.connect(g);
            g.connect(bellGain);
            osc.start(now);
            osc.stop(now + duration);
        });
    }

    playPad(chordName) {
        const notes = PAD_CHORDS[chordName];
        if (!notes) return;
        const now = this.audioCtx.currentTime;
        const duration = 6.0;
        const padGain = this.audioCtx.createGain();
        padGain.gain.setValueAtTime(0, now);
        padGain.gain.linearRampToValueAtTime(0.12, now + 1.5);
        padGain.gain.setValueAtTime(0.12, now + duration - 2.0);
        padGain.gain.linearRampToValueAtTime(0, now + duration);
        const filter = this.audioCtx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(1200, now);
        filter.frequency.linearRampToValueAtTime(3500, now + duration / 2);
        filter.frequency.linearRampToValueAtTime(1500, now + duration);
        filter.Q.value = 1;
        padGain.connect(filter);
        filter.connect(this.dryGain);
        filter.connect(this.reverbNode);
        notes.forEach(noteName => {
            const freq = NOTES[noteName];
            if (!freq) return;
            [0, 0.004, -0.004].forEach(detune => {
                const osc = this.audioCtx.createOscillator();
                osc.type = 'sine';
                osc.frequency.value = freq * (1 + detune);
                const g = this.audioCtx.createGain();
                g.gain.value = 0.15;
                osc.connect(g);
                g.connect(padGain);
                osc.start(now);
                osc.stop(now + duration);
            });
            const oscOct = this.audioCtx.createOscillator();
            oscOct.type = 'sine';
            oscOct.frequency.value = freq * 2;
            const gOct = this.audioCtx.createGain();
            gOct.gain.value = 0.05;
            oscOct.connect(gOct);
            gOct.connect(padGain);
            oscOct.start(now);
            oscOct.stop(now + duration);
        });
    }

    async playPattern(chordName, pattern) {
        if (!this.isPlaying) return;
        this.playPad(chordName);
        const notes = CHORDS[chordName];
        if (!notes) return;
        for (let i = 0; i < pattern.length; i++) {
            if (!this.isPlaying) return;
            const step = pattern[i];
            if (step < notes.length) {
                const velocity = 0.7 + Math.random() * 0.3;
                const isDownbeat = i === 0;
                this.playBell(notes[step], velocity * (isDownbeat ? 1.1 : 0.85));
            }
            const baseWait = 0.28 + Math.random() * 0.14;
            const extraWait = Math.random() < 0.12 ? 0.1 + Math.random() * 0.1 : 0;
            await this.sleep((baseWait + extraWait) * 1000 / this.tempoMultiplier);
        }
    }

    async loop() {
        let progressionCount = 0;
        while (this.isPlaying) {
            progressionCount++;
            const progression = CHORD_PROGRESSIONS[Math.floor(Math.random() * CHORD_PROGRESSIONS.length)];
            const pattern = PATTERNS[Math.floor(Math.random() * PATTERNS.length)];
            this.updateStatus(`🎶 Прогрессия #${progressionCount}: ${progression.join(' → ')}`);
            for (const chord of progression) {
                if (!this.isPlaying) return;
                await this.playPattern(chord, pattern);
            }
            const pause = 600 + Math.random() * 600;
            await this.sleep(pause / this.tempoMultiplier);
        }
    }

    sleep(ms) {
        return new Promise(resolve => {
            this.timeoutId = setTimeout(resolve, ms);
        });
    }

    updateStatus(text) {
        const el = document.getElementById('status');
        if (el) el.textContent = text;
    }

    async start() {
        await this.init();
        if (this.audioCtx.state === 'suspended') {
            await this.audioCtx.resume();
        }
        this.isPlaying = true;
        this.loop();
    }

    stop() {
        this.isPlaying = false;
        if (this.timeoutId) clearTimeout(this.timeoutId);
        this.updateStatus('Нажмите кнопку, чтобы начать');
    }

    setVolume(value) {
        this.volume = value;
        if (this.masterGain) {
            this.masterGain.gain.linearRampToValueAtTime(
                value,
                this.audioCtx.currentTime + 0.1
            );
        }
    }

    setTempo(value) {
        this.tempoMultiplier = value;
    }
}

// ============= МЕДУЗКА =============

class Jellyfish {
    constructor(musicBox, svgPath) {
        this.musicBox = musicBox;
        this.path = svgPath;
        this.numPoints = 64;           // точек по окружности
        this.baseRadius = 55;          // базовый радиус
        this.currentOffsets = new Float32Array(this.numPoints);
        this.targetOffsets = new Float32Array(this.numPoints);
        this.time = 0;
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }

    animate() {
        this.time += 0.016;

        let bass = 0, mid = 0, treble = 0;

        if (this.musicBox.analyser && this.musicBox.isPlaying) {
            const bufferLength = this.musicBox.analyser.frequencyBinCount;
            const data = new Uint8Array(bufferLength);
            this.musicBox.analyser.getByteFrequencyData(data);

            // Разбиваем спектр на три полосы
            const bassEnd = Math.floor(bufferLength * 0.1);
            const midEnd = Math.floor(bufferLength * 0.4);

            for (let i = 0; i < bassEnd; i++) bass += data[i];
            for (let i = bassEnd; i < midEnd; i++) mid += data[i];
            for (let i = midEnd; i < bufferLength; i++) treble += data[i];

            bass = (bass / bassEnd) / 255;
            mid = (mid / (midEnd - bassEnd)) / 255;
            treble = (treble / (bufferLength - midEnd)) / 255;
        }

        // Рассчитываем целевые смещения для каждой точки
        for (let i = 0; i < this.numPoints; i++) {
            const angle = (i / this.numPoints) * Math.PI * 2;

            // Три волны "дыхания" с разными частотами — медуза всегда живая
            const breath =
                Math.sin(this.time * 0.7 + angle * 2) * 3 +
                Math.sin(this.time * 1.3 + angle * 3) * 2 +
                Math.sin(this.time * 0.4 + angle) * 4;

            // Аудио-реакция: басы толкают низ медузы, верха — верх,
            // средние — равномерно во все стороны
            const bassInfluence = bass * 25 * Math.max(0, -Math.cos(angle));
            const trebleInfluence = treble * 18 * Math.max(0, Math.cos(angle));
            const midInfluence = mid * 12 * (0.5 + 0.5 * Math.sin(angle * 4 + this.time));

            this.targetOffsets[i] = breath + bassInfluence + trebleInfluence + midInfluence;
        }

        // Плавная интерполяция к целевым значениям — медузка не дёргается
        const smoothing = 0.15;
        for (let i = 0; i < this.numPoints; i++) {
            this.currentOffsets[i] += (this.targetOffsets[i] - this.currentOffsets[i]) * smoothing;
        }

        // Строим SVG-путь из точек, соединённых плавной кривой
        const points = [];
        for (let i = 0; i < this.numPoints; i++) {
            const angle = (i / this.numPoints) * Math.PI * 2;
            const r = this.baseRadius + this.currentOffsets[i];
            points.push({
                x: Math.cos(angle) * r,
                y: Math.sin(angle) * r,
            });
        }

        this.path.setAttribute('d', this.buildSmoothPath(points));

        requestAnimationFrame(this.animate);
    }

    // Замкнутая гладкая кривая через все точки (Catmull-Rom-подобный сплайн)
    buildSmoothPath(points) {
        const n = points.length;
        let d = '';
        for (let i = 0; i < n; i++) {
            const p0 = points[(i - 1 + n) % n];
            const p1 = points[i];
            const p2 = points[(i + 1) % n];
            const p3 = points[(i + 2) % n];

            if (i === 0) {
                d += `M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)} `;
            }

            // Контрольные точки для кубической Безье
            const c1x = p1.x + (p2.x - p0.x) / 6;
            const c1y = p1.y + (p2.y - p0.y) / 6;
            const c2x = p2.x - (p3.x - p1.x) / 6;
            const c2y = p2.y - (p3.y - p1.y) / 6;

            d += `C ${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)} `;
        }
        return d + 'Z';
    }
}

// === UI ===
const musicBox = new MusicBox();
const jellyPath = document.getElementById('jellyPath');
const jellyfish = new Jellyfish(musicBox, jellyPath);

const playBtn = document.getElementById('playBtn');
const btnText = document.getElementById('btnText');
const volumeSlider = document.getElementById('volume');
const tempoSlider = document.getElementById('tempo');

playBtn.addEventListener('click', async () => {
    if (musicBox.isPlaying) {
        musicBox.stop();
        btnText.textContent = '▶ Включить музыку';
    } else {
        await musicBox.start();
        btnText.textContent = '⏸ Остановить';
    }
});

volumeSlider.addEventListener('input', (e) => {
    musicBox.setVolume(e.target.value / 100);
});

tempoSlider.addEventListener('input', (e) => {
    musicBox.setTempo(e.target.value / 100);
});
