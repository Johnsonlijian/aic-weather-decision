"""Download a bounded set of public primary evidence and probe inputs.

Raw third-party files stay private and are excluded from the future code repo.
No dataset is treated as licensed for redistribution merely because it is public.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json

from download_inputs import fetch, save

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    'weatherwise_author.pdf': 'https://riunet.upv.es/server/api/core/bitstreams/57e3609d-0f9a-4d82-9fc1-29a8f16a93ed/content',
    'mohamed_2021_lookahead.pdf': 'https://mdpi-res.com/d_attachment/sustainability/sustainability-13-10060/article_deploy/sustainability-13-10060.pdf',
    'hs2_weather_2025.html': 'https://learninglegacy.hs2.org.uk/document/a-weather-resilient-approach-to-construction-lessons-from-align-joint-venture-on-hs2/',
    'weatherwise_crossref.json': 'https://api.crossref.org/works/10.1016/j.autcon.2017.08.022',
    'kerkhove_crossref.json': 'https://api.crossref.org/works/10.1016/j.omega.2016.01.011',
    'zhou_crossref.json': 'https://api.crossref.org/works/10.1016/j.cie.2021.107322',
    'mohamed_crossref.json': 'https://api.crossref.org/works/10.3390/su131810060',
    'j30.sm.zip': 'https://www.om-db.wi.tum.de/psplib/download_dataset.php?set=j30&mode=sm&format=zip',
    'psplib_home.html': 'https://www.om-db.wi.tum.de/psplib/',
    'dslib_repo.json': 'https://api.github.com/repos/MarioVanhoucke/DSLIB-Dynamic-Scheduling-Empirical-Project-Library',
}


def one(name, url):
    dest = ROOT / ('data/raw/networks' if name.endswith('.zip') else 'sources/raw') / name
    if dest.exists() and dest.with_suffix(dest.suffix + '.metadata.json').exists():
        return {'file': str(dest.relative_to(ROOT)), 'status': 'CACHED'}
    raw, meta = fetch(url)
    if name.endswith('.pdf') and not raw.startswith(b'%PDF-'):
        raise ValueError('expected PDF, refused error page')
    if name.endswith('.zip') and not raw.startswith(b'PK'):
        raise ValueError('expected ZIP, refused error page')
    if name.endswith('.json'):
        json.loads(raw)
    save(raw, meta, dest)
    return {'file': str(dest.relative_to(ROOT)), 'status': 'DOWNLOADED',
            'bytes': len(raw), 'sha256': meta['sha256']}


def main():
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(one, n, u): n for n, u in TARGETS.items()}
        for future in as_completed(pending):
            try:
                result = future.result()
            except Exception as exc:
                result = {'file': pending[future], 'status': 'FAILED', 'error': str(exc)}
            results.append(result)
            print(json.dumps(result, ensure_ascii=True), flush=True)
    (ROOT / 'outputs/public_intake_20260914.json').write_text(
        json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
