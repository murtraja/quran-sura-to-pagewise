from typing import List
from ayat_segmentation import AyatCorrector
import sqlite3
import config

conn_qari = sqlite3.connect(config.QARI_DB_PATH)
cur_qari = conn_qari.cursor()

TABLE = 'timings_corrections'

class Timings:
    def __init__(self, sura, ayah, start, end):
        self.sura = sura
        self.ayah = ayah
        self.start = start
        self.end = end
    
    def readable_timing(t):
        MS = 1000
        ms_rem = t % MS

        secs_total = t//MS
        secs_rem = secs_total % 60

        mins_total = secs_total // 60
        mins_rem = mins_total % 60

        hours_total = mins_total // 60
        rep = f'{secs_rem}s.{ms_rem:03}'
        if mins_total:
            rep = f'{mins_rem}m:' + rep
        if hours_total:
            rep = f'{hours_total}h:' + rep
        return rep

    def __str__(self):
        start = Timings.readable_timing(self.start)
        end = Timings.readable_timing(self.end)
        return f"{self.sura}:{self.ayah} {self.start}({start}) - {self.end}({end})"

def get_timings_for_ayah_range(sura, ayah_start, ayah_end):
    if ayah_end is None:
        ayah_end = 999
    
    query = f'''
        SELECT
            GROUP_CONCAT(time) AS timings
        FROM
            timings
        WHERE
            sura = {sura}
            AND ayah >= {ayah_start}
            AND ayah <= {ayah_end}
        GROUP BY
            sura
    '''
    
    cur_qari.execute(query)
    row = cur_qari.fetchone()
    timings = [int(v) for v in row[0].split(',')]
    return timings

def get_start_end_timings(sura):
    query = f"""
        SELECT
            *,
            lead(time, 1, 0) over () AS
        fin
        FROM
            timings
        WHERE
            sura = {sura}
        ORDER BY
            sura,
            ayah
    """
    cur_qari.execute(query)
    rows = cur_qari.fetchall()
    output = []
    for row in rows:
        values = [int(v) for v in row]
        timings = Timings(*values)
        output.append(timings)
    return output

def clear_corrections():
    query = f'''
    DROP TABLE IF EXISTS {TABLE}
    '''
    cur_qari.execute(query)

    query = f'''
        CREATE TABLE {TABLE}(
            page int,
            sura int,
            ayah int,
            prev_slot int,
            fixed_slot int,
            diff int,
            win_l int,
            win_r int,
            sil_start int,
            sil_end int,
            sil_dur int,
            is_last int,
            PRIMARY KEY(sura, ayah)
        )
    '''
    cur_qari.execute(query)

def write_corrections(corrections: List[AyatCorrector]):
    values = []
    for cor in corrections:
        data = [
            cor.page, 
            cor.sura, 
            cor.ayah,
            cor.prev_slot,
            cor.fixed_slot,
            cor.diff,
            cor.win_l,
            cor.win_r,
            cor.sil_start,
            cor.sil_end,
            cor.sil_dur,
            1 if cor.is_last else 0
        ]
        row = ",".join([str(v) for v in data])
        row = f"({row})"
        values.append(row)
    values = ",".join(values)
    query = f'''
        INSERT INTO
            {TABLE} (
                PAGE,
                sura,
                ayah,
                prev_slot,
                fixed_slot,
                diff,
                win_l,
                win_r,
                sil_start,
                sil_end,
                sil_dur,
                is_last
            )
        VALUES {values}
    '''
    cur_qari.execute(query)
    conn_qari.commit()

class CorrectionEntry:
    def __init__(self, page, sura, ayah, start_time, end_time):
        self.page = page
        self.sura = sura
        self.ayah = ayah
        self.start_time = start_time
        self.end_time = end_time
    
    def __str__(self):
        p = self.page
        s = self.sura
        a = self.ayah
        t = self.start_time
        e = self.end_time
        return f"p{p} {s}:{a} {t}({Timings.readable_timing(t)}) -> {e}({Timings.readable_timing(e)})"
    
    def __repr__(self):
        return self.__str__()

def get_corrections(page) -> List[CorrectionEntry]:
    # query = f"select page, sura, ayah, fixed_slot from {TABLE} where page={page}"
    query = f"""
        SELECT
            PAGE,
            sura,
            ayah,
            fixed_slot,
            lead(fixed_slot, 1, 0) over () AS
                fin
        FROM
            {TABLE}
        WHERE
            PAGE between {page} and {page+1}
    """
    cur_qari.execute(query)
    rows = cur_qari.fetchall()
    result = []
    for row in rows:
        values = [int(v) for v in row]
        if values[2] == 999:
            continue
        if values[0] != page:
            break
        entry = CorrectionEntry(*values)
        result.append(entry)
    return result
