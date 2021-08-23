SHZ_DB_PATH = '/home/murtraja/quran/quran-subayat/hifz_10.db'
QARI_DB_PATH = 'husary_fast.db'

QARI_SURAWISE_PATH = 'husary_128'
QARI_PAGEWISE_PATH = 'husary_pagewise'

def _get_audio_path(base_path, arg, prefix=''):
    return f"{base_path}/{prefix}{arg:03}.mp3"

def get_surawise_audio_path(sura):
    return _get_audio_path(QARI_SURAWISE_PATH, sura)

def get_pagewise_audio_path(page):
    return _get_audio_path(QARI_PAGEWISE_PATH, page, 'Page')
