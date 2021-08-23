from typing import List
from pydub import AudioSegment
import surawise_db
from surawise_db import CorrectionEntry
import shz_db
from shz_db import ShzPagewise, ShzSurawise
import ayat_segmentation as aseg
import config

def split_initial_phrase(sura, shz_pagewises:List[ShzPagewise], slot):
    index = None
    for i, pw in enumerate(shz_pagewises):
        if pw.sura == sura and pw.ayah == 1:
            index = i
            break
    if index is None:
        raise Exception("Couldn't find")
    pw = shz_pagewises[index]
    phrase_pagewise = ShzPagewise(pw.page, pw.sura, 0, 0, slot)
    pw.start_time = slot
    shz_pagewises.insert(index, phrase_pagewise)
    
    

def generate_page(page):
    print(f"page: {page}")
    entry_list = surawise_db.get_corrections(page)
    page_duration = 0
    shz_pagewises = []
    surawises: List[ShzSurawise] = []
    for entry in entry_list:
        ayah_duration = entry.end_time - entry.start_time
        ayah_start_time = page_duration
        ayah_end_time = page_duration + ayah_duration
        page_duration = ayah_end_time
        shz_pagewise = ShzPagewise(page, entry.sura, entry.ayah, ayah_start_time, ayah_end_time)
        shz_pagewises.append(shz_pagewise)
        if len(surawises) == 0 or entry.sura != surawises[-1].sura:
            sw = ShzSurawise(page, entry.sura, entry.start_time, entry.end_time)
            surawises.append(sw)
            continue
        surawises[-1].end_ayah = entry.end_time
    
    # now use the surawises list to stitch the mp3
    page_audio = None
    for sw in surawises:
        sura = sw.sura
        sura_audio_path = config.get_surawise_audio_path(sura)
        sura_audio = aseg.get_audio(sura_audio_path)
        if sw.start_ayah == 0 and sura != 9:
            ayah_start = aseg.separate_initial_phrase(sura_audio)
            assert ayah_start < sw.end_ayah
            print(f"detected initial phrase at {ayah_start} for {sura}:1")
            split_initial_phrase(sura, shz_pagewises, ayah_start)
        page_sura_audio = sura_audio[sw.start_ayah:sw.end_ayah]
        if page_audio == None:
            page_audio = page_sura_audio
        else:
            page_audio = page_audio + page_sura_audio
    audio_path = config.get_pagewise_audio_path(page)
    page_audio.export(audio_path, format='mp3', bitrate='64k')
    shz_db.write_pagewise(shz_pagewises)


def generate_pages(pages):
    shz_db.clear_pagewise()
    for page in pages:
        generate_page(page)
        
def main():
    pages = range(1, 605)
    generate_pages(pages)

if __name__ == '__main__':
    main()
    # print(surawise_db.Timings.readable_timing(83093))
    # print(surawise_db.Timings.readable_timing(90230))
    # audio_path = config.get_pagewise_audio_path(1)
    # audio_path = audio_path.replace('husary_pagewise_128', 'husary_pagewise')
    # br = mediainfo(audio_path)['bit_rate']
    # print(br)
    # audio_path = config.get_surawise_audio_path(1)
    # audio = aseg.get_audio(audio_path)
    # print(audio)
    # y, sr = aseg.get_raw(audio)
    # print(sr)
