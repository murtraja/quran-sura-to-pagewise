import requests
from pathlib import Path

BASE_MINSHAWI_URL = "https://download.quranicaudio.com/quran/muhammad_siddeeq_al-minshaawee"
BASE_MINSHAWI_BISMILLAH_FIX_URL = "https://download.quranicaudio.com/quran/muhammad_siddeeq_al-minshaawee/bismillah_bug_fix"
BASE_HUSARY_URL = "https://download.quranicaudio.com/quran/mahmood_khaleel_al-husaree_iza3a/128kbps"

def get_audio_url(base_url, page_no):
    return f"{base_url}/{page_no:03}.mp3"

def download(folder, base_url, page_no):
    audio_url = get_audio_url(base_url, page_no)
    while True:
        try:
            doc = requests.get(audio_url)
            break
        except Exception as e:
            pass

    path = Path(folder)
    if not path.exists():
        path.mkdir()
    path = path / Path(f'{page_no:03}.mp3')
    with open(str(path), 'wb') as f:
        f.write(doc.content)
    print(f"{page_no} done")

for i in range(1, 115):
    download("husary_128", BASE_HUSARY_URL, i)