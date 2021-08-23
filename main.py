import sqlite3
import config
import surawise_db
from shz_db import ShzSurawise
import shz_db
import ayat_segmentation as aseg

def generate_page(page):
    shz_surawises = shz_db.get_surawise_page_ayahs(page)
    surawise_corrections = []
    for shz_surawise in shz_surawises:
        print(f"{shz_surawise}")
        sura = shz_surawise.sura
        start = shz_surawise.start_ayah
        end = shz_surawise.end_ayah
        if shz_surawise.is_last:
            end = None
        timings = surawise_db.get_timings_for_ayah_range(sura, start, end)
        # aseg.show(shz_surawise, timings)
        correction = aseg.fix_timings_for_ayah_range(shz_surawise, timings)
        surawise_corrections.extend(correction)
        # aseg.find_max_silence(2)
    return surawise_corrections

def generate_pages(pages):
    # surawise_db.clear_corrections()
    for page in pages:
        corrections = generate_page(page)
        surawise_db.write_corrections(corrections)
    
def main():
    # page 331, ayah 111
    pages = range(331, 605)
    generate_pages(pages)
    
if __name__ == '__main__':
    main()