import sqlite3
from typing import List
import config

conn_hifz = sqlite3.connect(config.SHZ_DB_PATH)
cur_hifz = conn_hifz.cursor()

TABLE = "husaryaudio"

class ShzSurawise:
    def __init__(self, page_no=None, sura=None, start_ayah=None, end_ayah=None, is_last=None):
        self.page_no = page_no
        self.sura = sura
        self.start_ayah = start_ayah
        self.end_ayah = end_ayah
        self.is_last = is_last
    
    def __str__(self):
        end = self.end_ayah
        if self.is_last:
            end = f'...{end}'
        return f"p{self.page_no} {self.sura}:{self.start_ayah} -> {end}"

class ShzPagewise:
    def __init__(self, page, sura, ayah, start_time, end_time):
        self.page = page
        self.sura = sura
        self.ayah = ayah
        self.start_time = start_time
        self.end_time = end_time

def get_surawise_page_ayahs(page_no) -> List[ShzSurawise]:
    query = f'''
        SELECT
            sura_number,
            max(min(ayah_number), 1) AS start_ayah,
            max(ayah_number) AS end_ayah,
            (
                max(ayah_number) = (
                    SELECT
                        max(ayah_number)
                    FROM
                        shzaudio
                    WHERE
                        sura_number = a.sura_number
                )
            ) AS last_ayah
        FROM
            shzaudio a
        WHERE
            page_number = {page_no}
        GROUP BY
            sura_number
        ORDER BY
            sura_number
    '''
    cur_hifz.execute(query)
    rows = cur_hifz.fetchall()
    output = []
    for row in rows:
        values = [int(v) for v in row]
        sura = values[0]
        start = values[1]
        end = values[2]
        is_last = bool(values[3])
        surawise = ShzSurawise(page_no=page_no, sura=sura, start_ayah=start, end_ayah=end, is_last=is_last)
        output.append(surawise)
    return output

def clear_pagewise():
    query = f'''
    DROP TABLE IF EXISTS {TABLE}
    '''
    cur_hifz.execute(query)

    query = f'''
        CREATE TABLE {TABLE} (
            track_id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_number INTEGER,
            sura_number INTEGER,
            ayah_number INTEGER,
            start_time INTEGER,
            end_time INTEGER,
            UNIQUE(sura_number, ayah_number)
        )
    '''
    cur_hifz.execute(query)

def write_pagewise(shz_pagewises:List[ShzPagewise]):
    values = []
    for pw in shz_pagewises:
        data = [
            pw.page, 
            pw.sura, 
            pw.ayah,
            pw.start_time,
            pw.end_time
        ]
        row = ",".join([str(v) for v in data])
        row = f"({row})"
        values.append(row)
    values = ",".join(values)
    query = f'''
        INSERT INTO
            {TABLE} (
                page_number,
                sura_number,
                ayah_number,
                start_time,
                end_time
            )
        VALUES {values}
    '''
    cur_hifz.execute(query)
    conn_hifz.commit()
