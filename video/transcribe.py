"""voice/chN.wav -> words/chN.json: [[word, start, end], ...] in seconds."""
import json
import sys
import subprocess
import numpy as np
from pathlib import Path
from faster_whisper import WhisperModel

here = Path(__file__).parent
(here / "words").mkdir(exist_ok=True)
model = WhisperModel("small.en", device="cpu", compute_type="int8")
for wav in sorted((here / "voice").glob(f"{sys.argv[1] if len(sys.argv) > 1 else 'ch*'}.wav")):  # e.g. ch1
    # Decode with ffmpeg: the bundled PyAV rejects faster-whisper's open() arguments.
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segments, _ = model.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, vad_filter=True, beam_size=5)
    words = [[w.word.strip(), round(w.start, 2), round(w.end, 2)] for s in segments for w in s.words]
    (here / "words" / f"{wav.stem}.json").write_text(json.dumps(words))
    print(f"{wav.stem}: {len(words)} words, {words[0][1]:.2f}-{words[-1][2]:.2f}s")
    print("   ", " ".join(w for w, *_ in words))
