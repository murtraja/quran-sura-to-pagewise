from typing import List

import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment

import config
from shz_db import ShzSurawise

MS = 1000
SHOW_WINDOW = 1000
PAUSE_WINDOW = SHOW_WINDOW

class AyatCorrector:
    def __init__(self, page, sura, ayah, prev_slot, fixed_slot=None, win_l=PAUSE_WINDOW, win_r=PAUSE_WINDOW, sil_start=None, sil_end=None, is_last = False):
        self.page = page
        self.sura = sura
        self.ayah = ayah
        self.prev_slot = prev_slot
        
        if fixed_slot is None:
            fixed_slot = prev_slot
        self.fixed_slot = fixed_slot

        self.win_l = win_l
        self.win_r = win_r

        if sil_start is None:
            sil_start = prev_slot
        self.sil_start = sil_start

        if sil_end is None:
            sil_end = prev_slot
        self.sil_end = sil_end

        self.is_last = is_last
        if is_last:
            self.ayah = 999

        # derived
        self.diff = self.prev_slot-self.fixed_slot
        self.sil_dur = self.sil_end - self.sil_start

def get_audio_window(audio, slot, win_l=PAUSE_WINDOW, win_r=PAUSE_WINDOW):
    start = max(0, slot - win_l)
    end = min(len(audio), slot + win_r)
    return start, end

def get_raw(audio):
    y = np.array(audio.get_array_of_samples()).astype(np.float32)
    sr = audio.frame_rate * audio.channels
    return y, sr

def plot(y, sr, points):
    import librosa.display
    import matplotlib.pyplot as plt
    o = librosa.display.waveplot(y, sr=sr)
    colors = ['r', 'g']
    for point, col in zip(points, colors):
        plt.axvline(x=point/MS, ymin=0, ymax=1, color=col)
    plt.show()

def show(shz_surawise:ShzSurawise, timings:List[int]):
    sura = shz_surawise.sura
    audio_path = config.get_surawise_audio_path(sura)
    audio = AudioSegment.from_mp3(audio_path)
    for i, slot in enumerate(timings):
        if slot == 0:
            continue
        ayah = shz_surawise.start_ayah + i
        if shz_surawise.is_last and ayah > shz_surawise.end_ayah:
            # the last marker for the last ayah in the mp3, no need
            # continue
            pass
        slot = timings[i]
        start, end = get_audio_window(audio, slot, SHOW_WINDOW)
        audio_segment = audio[start:end]
        y, sr = get_raw(audio_segment)
        slot_relative = slot - start
        plot(y, sr, [slot_relative])

def get_interval_complement(intervals, start, end):
    # print(start,intervals,end)
    if intervals[0] == start:
        intervals = np.delete(intervals, 0)
    else:
        intervals = np.insert(intervals, 0, start)
    
    if intervals[-1] == end:
        intervals = np.delete(intervals, -1)
    else:
        intervals = np.append(intervals, end)
    # print(intervals)
    return intervals

def get_best_slot(slot, intervals, ayah):
    assert len(intervals) > 0
    for start,end in intervals:
        if slot>= start and slot <= end:
            return slot, start, end
    print(f"{slot} doesn't lie within any interval for {ayah}")
    # e.g. page 331, ayah 111, start
    if len(intervals) == 1:
        print(f"returning the only silence interval {intervals}")
        return (start+end)//2, start, end
    
    return None, None, None

def get_silence_intervals(y, sr, len_audio):
    intervals = librosa.effects.split(y, top_db=31)
    time_intervals = librosa.samples_to_time(intervals.flatten(), sr=sr)
    intervals_ms = (np.rint(time_intervals*1000).astype(int))
    intervals_ms = intervals_ms.reshape(-1, 2)
    silence_intervals = get_interval_complement(intervals_ms.flatten(), 0, len_audio).reshape(-1, 2)
    return silence_intervals

memoized_audios = {}

def get_audio(path):
    global memoized_audios
    if path in memoized_audios:
        return memoized_audios[path]
    audio = AudioSegment.from_mp3(path)
    memoized_audios[path] = audio
    return audio

def fix_timings_for_ayah_range(shz_surawise:ShzSurawise, timings:List[int]):
    sura = shz_surawise.sura
    page = shz_surawise.page_no
    audio_path = config.get_surawise_audio_path(sura)
    audio = get_audio(audio_path)
    # print(len(audio))
    audio.set_channels(1)
    fixed_timings = []
    for i, slot in enumerate(timings):
        ayah = shz_surawise.start_ayah + i
        is_first = (slot == 0)
        is_last = (shz_surawise.is_last and ayah > shz_surawise.end_ayah)
        if  is_first or is_last:
            correction = AyatCorrector(page, sura, ayah, slot, is_last=is_last)
            fixed_timings.append(correction)
            continue

        win_l = win_r = PAUSE_WINDOW
        prev_slot = slot
        while True:
            start, end = get_audio_window(audio, slot, win_l, win_r)
            audio_segment = audio[start:end]
            slot_relative = slot-start
            y, sr = get_raw(audio_segment)
            silence_intervals = get_silence_intervals(y, sr, len(audio_segment))
            slot_relative_changed, best_start, best_end = get_best_slot(slot_relative, silence_intervals, ayah)
            if slot_relative_changed is None:
                print(f"Couldn't determine best slot for ayah {ayah}")                
                plot(y, sr, [slot_relative])
            if slot_relative_changed != slot_relative:
                slot_changed = slot_relative_changed + start
                print(f"Changing slot {slot} -> {slot_changed} for ayah {ayah}")
                slot = slot_changed

            if best_start!=0 and best_end != 0:
                break

            if best_start == 0:
                win_l += 500
            if best_end == 0:
                win_r += 500

        best_slot_relative = (best_start + best_end)//2 
        best_slot =  best_slot_relative + start
        # print(f"Existing: {slot}, Got: {best_slot}, diff: {slot-best_slot}")
        sil_start = best_start + start
        sil_end = best_end + start
        correction = AyatCorrector(page, sura, ayah, prev_slot, best_slot, win_l, win_r, sil_start, sil_end)
        fixed_timings.append(correction)
        # plot(y, sr, [prev_slot-start, best_slot_relative])
    return fixed_timings
    
def find_max_silence(sura):
    audio_path = config.get_surawise_audio_path(sura)
    audio = AudioSegment.from_mp3(audio_path)
    y, sr = get_raw(audio)
    silence_intervals = get_silence_intervals(y, sr, len(audio))
    max_silence = max([(v[1]-v[0]) for v in silence_intervals])
    print(f"max_silence: {max_silence}")
    # sura 2: 3646

def separate_initial_phrase(audio):
    PHRASE_DURATION = 7500
    initial_audio = audio[:PHRASE_DURATION]
    y, sr = get_raw(initial_audio)
    silence_intervals = get_silence_intervals(y, sr, len(initial_audio))
    while True:
        if len(silence_intervals) == 0:
            raise Exception("no silence detected")
        if silence_intervals[0][0] == 0:
            # we do not care about the initial silence
            silence_intervals = silence_intervals[1:, :]
            continue
        if len(silence_intervals) == 1 and silence_intervals[0][1] == len(initial_audio):
            raise Exception("Should increase the PHRASE DURATION")
        interval = silence_intervals[0]
        phrase_duration = interval[1] - interval[0]
        if phrase_duration < 500:
            silence_intervals = silence_intervals[1:, :]
            continue
        slot = int(np.rint(np.mean(interval)))
        return slot
    
