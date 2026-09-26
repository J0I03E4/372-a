"""
generate_chiptune.py -- synthesizes a small, fully original 8-bit-style
background loop for the dashboard, entirely from scratch (square/triangle
waves via basic waveform math). No samples, no licensed material, no
external audio library -- just stdlib `wave` + `math`. Safe for a public
repo: nothing here is copied from any existing game or recording.

Run: python generate_chiptune.py
Writes: audio/chiptune-loop.wav
"""
import math
import os
import wave
import struct

SR = 11025           # retro-appropriate low sample rate (also keeps file small)
AMP = 0.28            # overall volume headroom so mixed channels don't clip
BPM = 140
BEAT = 60.0 / BPM     # seconds per beat
STEP = BEAT / 2       # eighth-note step

# Original 2-bar-repeated chord progression (A minor, natural minor feel --
# classic chiptune territory, but these are just chord roots, not a melody
# copied from anywhere).
NOTE_FREQS = {
    'A2': 110.00, 'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00,
    'A3': 220.00, 'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00,
    'A4': 440.00, 'B4': 493.88, 'C5': 523.25, 'E5': 659.25, None: 0.0,
}

# Bassline: one root note held per bar (4 beats), square wave, low octave.
BASS_PATTERN = ['A2', 'F3', 'C3', 'G3']  # Am - F - C - G, one per bar

# Lead melody: original 8-step-per-bar arpeggio/riff, plain public-domain-style
# chiptune noodling -- deliberately simple and not derived from any existing
# game soundtrack.
LEAD_PATTERN = [
    ['A4', 'C5', 'E5', 'C5', 'A4', 'E4', 'A4', 'C5'],   # over Am
    ['F4', 'A4', 'C5', 'A4', 'F4', 'C4', 'F4', 'A4'],   # over F
    ['C4', 'E4', 'G4', 'E4', 'C4', 'G3', 'C4', 'E4'],   # over C
    ['G3', 'B4', 'D4', 'B4', 'G3', 'D3', 'G3', 'B4'],   # over G
]


def square_wave(freq, n_samples, duty=0.5):
    if freq <= 0:
        return [0.0] * n_samples
    period = SR / freq
    out = []
    for i in range(n_samples):
        phase = (i % period) / period
        out.append(1.0 if phase < duty else -1.0)
    return out


def envelope(n_samples, attack=60, release=120):
    out = [1.0] * n_samples
    for i in range(min(attack, n_samples)):
        out[i] = i / attack
    for i in range(min(release, n_samples)):
        out[n_samples - 1 - i] = i / release
    return out


def render_note(freq, seconds, duty=0.5):
    n = max(1, int(SR * seconds))
    wav = square_wave(freq, n, duty)
    env = envelope(n)
    return [w * e for w, e in zip(wav, env)]


def main():
    lead_track = []
    bass_track = []
    for bar_i, bass_note in enumerate(BASS_PATTERN):
        # bass: one held note per bar, duty 0.5, one octave down feel via low freq
        lead_notes = LEAD_PATTERN[bar_i]
        bar_seconds = STEP * len(lead_notes)
        bass_track += render_note(NOTE_FREQS[bass_note], bar_seconds, duty=0.5)
        for note in lead_notes:
            lead_track += render_note(NOTE_FREQS[note], STEP, duty=0.25)

    n = min(len(lead_track), len(bass_track))
    mixed = [
        max(-1.0, min(1.0, (lead_track[i] * 0.7 + bass_track[i] * 0.5) * AMP))
        for i in range(n)
    ]

    out_dir = os.path.join(os.path.dirname(__file__), 'audio')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'chiptune-loop.wav')

    with wave.open(out_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        frames = b''.join(struct.pack('<h', int(s * 32767)) for s in mixed)
        wf.writeframes(frames)

    print(f'wrote {out_path} ({os.path.getsize(out_path)/1024:.1f} KB, '
          f'{n/SR:.1f}s loop @ {SR}Hz)')


if __name__ == '__main__':
    main()
