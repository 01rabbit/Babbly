import math

from babbly.wake.vad import EnergyVad, VadEvent


def test_rms_of_constant_and_empty_frames():
    assert EnergyVad.rms([]) == 0.0
    assert EnergyVad.rms([0.0, 0.0, 0.0]) == 0.0
    assert math.isclose(EnergyVad.rms([0.5, -0.5, 0.5, -0.5]), 0.5)


def test_single_loud_frame_starts_speech():
    vad = EnergyVad(rms_threshold=0.1, start_frames=1, hangover_frames=3)
    assert vad.observe_rms(0.5) is VadEvent.SPEECH_START
    assert vad.in_speech is True
    assert vad.observe_rms(0.5) is VadEvent.SPEECH


def test_start_requires_consecutive_loud_frames():
    vad = EnergyVad(rms_threshold=0.1, start_frames=2, hangover_frames=3)
    assert vad.observe_rms(0.5) is VadEvent.SILENCE   # 1 loud, not enough
    assert vad.observe_rms(0.0) is VadEvent.SILENCE   # quiet resets the loud run
    assert vad.observe_rms(0.5) is VadEvent.SILENCE   # 1 again
    assert vad.observe_rms(0.5) is VadEvent.SPEECH_START  # 2 consecutive


def test_hangover_closes_utterance_and_loud_resets_quiet_run():
    vad = EnergyVad(rms_threshold=0.1, start_frames=1, hangover_frames=3)
    assert vad.observe_rms(0.5) is VadEvent.SPEECH_START
    assert vad.observe_rms(0.0) is VadEvent.SPEECH   # quiet 1
    assert vad.observe_rms(0.0) is VadEvent.SPEECH   # quiet 2
    assert vad.observe_rms(0.5) is VadEvent.SPEECH   # loud resets the quiet run
    assert vad.observe_rms(0.0) is VadEvent.SPEECH   # quiet 1 again
    assert vad.observe_rms(0.0) is VadEvent.SPEECH   # quiet 2
    assert vad.observe_rms(0.0) is VadEvent.SPEECH_END  # quiet 3 -> hangover
    assert vad.in_speech is False


def test_reset_clears_state():
    vad = EnergyVad(rms_threshold=0.1, start_frames=1, hangover_frames=2)
    vad.observe_rms(0.5)
    assert vad.in_speech is True
    vad.reset()
    assert vad.in_speech is False
    assert vad.observe_rms(0.0) is VadEvent.SILENCE


def test_speech_present_convenience():
    quiet = [[0.0] * 4 for _ in range(5)]
    loud = quiet[:2] + [[0.5, -0.5, 0.5, -0.5]] + quiet[:2]
    assert EnergyVad(rms_threshold=0.1).speech_present(quiet) is False
    assert EnergyVad(rms_threshold=0.1).speech_present(loud) is True


def test_capture_parity_appends_until_hangover():
    # Mirrors FasterWhisperASR._capture_utterance: append on any non-silence
    # event, break on SPEECH_END, sleep/skip on SILENCE.
    vad = EnergyVad(rms_threshold=0.1, start_frames=1, hangover_frames=2)
    rms_sequence = [0.0, 0.0, 0.5, 0.5, 0.0, 0.0, 0.5]  # trailing loud never reached
    appended = []
    broke_at = None
    for i, rms in enumerate(rms_sequence):
        event = vad.observe_rms(rms)
        if event is VadEvent.SILENCE:
            continue
        appended.append(i)
        if event is VadEvent.SPEECH_END:
            broke_at = i
            break
    # frames 0,1 are pre-speech silence (skipped); 2,3 speech; 4 quiet(1); 5 quiet(2)->end
    assert appended == [2, 3, 4, 5]
    assert broke_at == 5
