"""Retrieve station-year chunks and enforce requested KNMI interval bounds."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
import csv
import json

from download_inputs import fetch, parse_knmi, restrict_knmi_rows, save

ROOT = Path(__file__).resolve().parents[1]
STATIONS = ('240', '260', '344')


def chunk(station, year):
    start = f'{year}060101' if year == 2021 else f'{year}010101'
    end = f'{year}123124'
    params = {'stns': station, 'start': start, 'end': end, 'vars': 'FH:FX'}
    dest = ROOT / 'data/raw/knmi' / f'{station}_{year}.txt'
    if dest.exists():
        raw = dest.read_bytes()
        meta = json.loads(dest.with_suffix('.txt.metadata.json').read_text(encoding='utf-8'))
    else:
        raw, meta = fetch('https://www.daggegevens.knmi.nl/klimatologie/uurgegevens?' + urlencode(params))
    parsed = parse_knmi(raw.decode('utf-8-sig'))
    rows = restrict_knmi_rows(parsed, start, end, station)
    meta.update(request_parameters=params, response_rows=len(parsed), retained_rows=len(rows),
                excluded_outside_request=len(parsed) - len(rows),
                source_type='station_observation',
                availability_status='historical archive; operational observation latency not established')
    save(raw, meta, dest)
    with dest.with_suffix('.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    return {'station': station, 'year': year, 'rows': len(rows),
            'FX_missing': sum(r['FX_ms'] is None for r in rows), 'sha256': meta['sha256']}


def main():
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(chunk, s, y): (s, y) for s in STATIONS for y in range(2021, 2026)}
        for f in as_completed(futures):
            try:
                r = {'status': 'OK', **f.result()}
            except Exception as exc:
                r = {'status': 'FAILED', 'station_year': futures[f], 'error': str(exc)}
            results.append(r); print(json.dumps(r), flush=True)
    (ROOT / 'outputs/knmi_study_coverage.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    if any(r['status'] != 'OK' for r in results):
        raise SystemExit('Some station-year chunks failed; no combined dataset declared complete')


if __name__ == '__main__':
    main()
