"""Offline Indonesian TTS using bundled espeak-ng (pip: espeakng-loader). Returns float32 numpy at 22050Hz."""
import ctypes, numpy as np, espeakng_loader as el
_lib = ctypes.CDLL(el.get_library_path())
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
_buf = []
@CB
def _cb(wav, n, ev):
    if n > 0: _buf.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
    return 0
SR = _lib.espeak_Initialize(2, 0, el.get_data_path().encode(), 0)
_lib.espeak_SetSynthCallback(_cb)
def say(text, voice="id+m3", rate=165, pitch=45, rng=60):
    _buf.clear()
    _lib.espeak_SetVoiceByName(voice.encode())
    _lib.espeak_SetParameter(1, rate, 0); _lib.espeak_SetParameter(3, pitch, 0); _lib.espeak_SetParameter(4, rng, 0)
    b = text.encode("utf-8")
    _lib.espeak_Synth(b, len(b) + 1, 0, 0, 0, 1, None, None)
    return np.concatenate(_buf).astype(np.float32) / 32768.0
