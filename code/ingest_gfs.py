"""Fetch only the indexed GFS GUST message and audit its native semantics."""
from pathlib import Path
import argparse
import csv
import json

from download_inputs import fetch, save


def grib2_sections(raw: bytes) -> dict:
    if raw[:4] != b'GRIB' or raw[7] != 2 or raw[-4:] != b'7777':
        raise ValueError('not one complete GRIB2 message')
    if int.from_bytes(raw[8:16], 'big') != len(raw):
        raise ValueError('GRIB2 declared length does not match response')
    result = {'discipline': raw[6], 'edition': raw[7]}
    pos = 16
    while pos < len(raw) - 4:
        length = int.from_bytes(raw[pos:pos + 4], 'big')
        if length < 5 or pos + length > len(raw) - 4:
            raise ValueError('invalid GRIB section length')
        section = raw[pos:pos + length]
        if section[4] == 4:
            result.update(product_definition_template=int.from_bytes(section[7:9], 'big'),
                          parameter_category=section[9], parameter_number=section[10])
        pos += length
    return result


def ingest(idx_path: Path, out: Path, stations: list[dict]) -> dict:
    import rasterio

    index_meta = json.loads(idx_path.with_suffix(idx_path.suffix + '.metadata.json').read_text())
    hits = index_meta['gust_ranges']
    if len(hits) != 1 or hits[0]['end_byte'] is None:
        raise ValueError('exactly one bounded GUST byte range required')
    lo, hi = hits[0]['start_byte'], hits[0]['end_byte']
    raw, meta = fetch(index_meta['grib_url'], headers={'Range': f'bytes={lo}-{hi}'},
                      require_partial=True)
    content_range = next((v for k, v in meta['headers'].items()
                          if k.lower() == 'content-range'), '')
    if not content_range.startswith(f'bytes {lo}-{hi}/') or len(raw) != hi - lo + 1:
        raise ValueError('server range or byte count differs from requested message')
    sections = grib2_sections(raw)
    save(raw, meta, out)
    with rasterio.open(out) as ds:
        tags = ds.tags(1)
        if ds.count != 1 or tags.get('GRIB_ELEMENT') != 'GUST':
            raise ValueError('decoded message is not single surface GUST')
        if tags.get('GRIB_UNIT') not in ('[m/s]', 'm/s'):
            raise ValueError('unexpected GUST units')
        rows = []
        for station in stations:
            lon, lat = station['longitude'], station['latitude']
            rr, cc = ds.index(lon, lat)
            if not (0 <= rr < ds.height and 0 <= cc < ds.width):
                raise ValueError('station outside decoded grid')
            gx, gy = ds.xy(rr, cc)
            value = float(next(ds.sample([(lon, lat)]))[0])
            rows.append({**station, 'grid_longitude': gx, 'grid_latitude': gy,
                         'GUST_ms': value, 'forecast_ref_unix': tags.get('GRIB_REF_TIME'),
                         'forecast_valid_unix': tags.get('GRIB_VALID_TIME'),
                         'forecast_seconds': tags.get('GRIB_FORECAST_SECONDS'),
                         'spatial_method': 'nearest_grid_cell'})
        meta.update(grib2_sections=sections, decoder='rasterio/GDAL',
                    decoder_version=rasterio.__version__, band_tags=tags,
                    grid_shape=[ds.height, ds.width], crs=str(ds.crs),
                    index_sha256=index_meta['sha256'],
                    temporal_support=('instantaneous forecast; not the KNMI preceding-hour maximum'
                                      if sections['product_definition_template'] == 0
                                      else 'requires template-specific temporal interpretation'),
                    information_time_status='object Last-Modified observed; publication proxy needs conservative latency rule')
    out.with_suffix(out.suffix + '.metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    with out.with_suffix('.stations.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return {'bytes': len(raw), 'sections': sections, 'stations': rows,
            'temporal_support': meta['temporal_support']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--idx', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(ingest(args.idx, args.out,
                           [{'station_id': '260', 'latitude': 52.1, 'longitude': 5.18}]), indent=2))
