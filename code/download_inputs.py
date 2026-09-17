"""Small, provenance-preserving data download utilities.

KNMI and bounded GFS transfers have been verified on the archived pilot.
These commands download inputs only; they do not run the proposed full
empirical study. Response metadata retain provenance headers only.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

UA='AcademicResearchInputClient/0.1'
MAX_BYTES=25_000_000


def fetch(url: str, body: bytes | None=None, headers: dict | None=None,
          require_partial: bool=False) -> tuple[bytes,dict]:
    hh={'User-Agent':UA};hh.update(headers or {})
    error=None
    for attempt in range(3):
        try:
            req=Request(url,data=body,headers=hh)
            with urlopen(req,timeout=45) as r:
                if require_partial and r.status != 206:
                    raise RuntimeError('Range request was not honoured; refusing full GRIB download')
                raw=r.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise RuntimeError('Download exceeded 25 MB guard')
                return raw,{'url':url,'http_status':r.status,
                            'retrieved_at':datetime.now(timezone.utc).isoformat(),
                            'sha256':hashlib.sha256(raw).hexdigest(),
                            'bytes':len(raw),'headers':{
                                k:v for k,v in r.headers.items() if k.lower() in {
                                    'date','content-length','content-type','content-range',
                                    'accept-ranges','etag','last-modified','x-amz-version-id',
                                    'x-amz-checksum-sha256'}}}
        except Exception as e:
            error=e
            if attempt<2:time.sleep(2**attempt)
    raise RuntimeError(f'Input transfer failed (no data substituted): {error}')


def save(raw:bytes, meta:dict, out:Path) -> None:
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(raw)
    out.with_suffix(out.suffix+'.metadata.json').write_text(
        json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')


def parse_knmi(text: str) -> list[dict]:
    header=None;rows=[]
    for line in text.splitlines():
        s=line.strip()
        if s.startswith('#'):
            candidate=s.lstrip('#').strip()
            if re.match(r'STN\s*,',candidate) and 'YYYYMMDD' in candidate:
                header=[x.strip() for x in candidate.split(',')]
            continue
        if not s:continue
        if header is None:raise ValueError('KNMI column header not found; possible HTML/error response')
        parts=[x.strip() for x in s.split(',')]
        if len(parts)!=len(header):raise ValueError('KNMI column mismatch')
        raw=dict(zip(header,parts))
        h=int(raw.get('HH',raw.get('H','-1')))
        if not 1<=h<=24:raise ValueError('hour must be 1..24')
        end=datetime.strptime(raw['YYYYMMDD'],'%Y%m%d').replace(tzinfo=timezone.utc)+timedelta(hours=h)
        item={'station_id':raw['STN'],'interval_start':(end-timedelta(hours=1)).isoformat(),
              'interval_end':end.isoformat(),'source_type':'station_observation',
              'availability_status':'historical_observation_latency_not_established'}
        for key in ('FH','FX'):
            v=raw.get(key,'')
            item[key+'_ms']=float(v)/10 if v else None
        # Extra variables.  Units follow the KNMI hourly-comment block:
        #   T  [0.1 degC]   U [%]   Q [J/cm2]   TD [0.1 degC]
        for key, out_key, scale in (('T','T_degC',10.0),('U','U_pct',1.0),
                                    ('Q','Q_Jcm2',1.0),('TD','TD_degC',10.0)):
            if key in raw:
                v=raw.get(key,'')
                item[out_key]=float(v)/scale if v not in ('',None) else None
        # Precipitation: R is a 0/1 occurrence flag, RH is the amount in 0.1 mm
        # (RH = -1 means "trace", i.e. < 0.05 mm) and DR is the duration in
        # 0.1 h.  Treating R as an amount (R/10 "mm") and renaming DR as a
        # degree value were both wrong; a trace is retained as censored data
        # rather than silently converted into a dry hour.
        if 'R' in raw:
            v=raw.get('R','')
            item['R_occurrence']=int(float(v)) if v not in ('',None) else None
            if item['R_occurrence'] not in (None,0,1):
                raise ValueError(f"KNMI R must be a 0/1 occurrence flag, got {v!r}")
        if 'RH' in raw:
            v=raw.get('RH','')
            rh=float(v) if v not in ('',None) else None
            if rh is not None and rh<0 and rh!=-1:
                raise ValueError(f"unknown negative KNMI RH code {rh!r}")
            trace=rh==-1
            item['RH_amount_mm']=None if rh is None or trace else rh/10
            item['RH_trace']=None if rh is None else bool(trace)
            item['RH_lower_mm']=0.0 if trace else (None if rh is None else rh/10)
            item['RH_upper_mm_exclusive']=0.05 if trace else None
        if 'DR' in raw:
            v=raw.get('DR','')
            item['DR_hours']=float(v)/10 if v not in ('',None) else None
        rows.append(item)
    if not rows:raise ValueError('No observation rows returned')
    return rows


def knmi_request_end(value: str) -> datetime:
    """Convert a provider YYYYMMDDHH interval-end stamp (HH is 01..24)."""
    if not re.fullmatch(r'\d{10}', value) or not 1 <= int(value[-2:]) <= 24:
        raise ValueError('KNMI request stamp must be YYYYMMDDHH with HH 01..24')
    return (datetime.strptime(value[:8], '%Y%m%d').replace(tzinfo=timezone.utc)
            + timedelta(hours=int(value[-2:])))


def restrict_knmi_rows(rows: list[dict], start: str, end: str,
                       stations: str) -> list[dict]:
    """Retain the requested inclusive interval ends, preserving raw response.

    The live endpoint may return complete extra dates. Its response extent is
    not the experiment's inclusion rule. Duplicate station-hours are rejected.
    """
    lo, hi = knmi_request_end(start), knmi_request_end(end)
    if hi < lo:
        raise ValueError('end precedes start')
    wanted = set(stations.split(':'))
    retained = [r for r in rows if r['station_id'] in wanted
                and lo <= datetime.fromisoformat(r['interval_end']) <= hi]
    keys = [(r['station_id'], r['interval_end']) for r in retained]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate KNMI station-hour in response')
    if not retained:
        raise ValueError('no KNMI rows in requested range')
    return retained


def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest='command',required=True)
    k=subs.add_parser('knmi');k.add_argument('--stations',default='235:240:260:280:344:380')
    k.add_argument('--start',required=True,help='YYYYMMDDHH, hour 01..24')
    k.add_argument('--end',required=True);k.add_argument('--out',type=Path,required=True)
    k.add_argument('--method',choices=['GET','POST'],default='POST')
    r=subs.add_parser('single-run');r.add_argument('--lat',type=float,required=True)
    r.add_argument('--lon',type=float,required=True);r.add_argument('--run',required=True)
    r.add_argument('--model',required=True);r.add_argument('--out',type=Path,required=True)
    r.add_argument('--record-type',choices=['unverified','operational_archive','hindcast'],default='unverified')
    g=subs.add_parser('gfs-index');g.add_argument('--date',required=True,help='YYYYMMDD')
    g.add_argument('--cycle',choices=['00','06','12','18'],default='00')
    g.add_argument('--lead',type=int,required=True);g.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.command=='knmi':
        params={'stns':a.stations,'start':a.start,'end':a.end,'vars':'FH:FX'}
        endpoint='https://www.daggegevens.knmi.nl/klimatologie/uurgegevens'
        encoded=urlencode(params)
        raw,meta=fetch(endpoint+'?'+encoded if a.method=='GET' else endpoint,
                       None if a.method=='GET' else encoded.encode(),
                       {'Content-Type':'application/x-www-form-urlencoded'})
        parsed=parse_knmi(raw.decode('utf-8-sig'))
        rows=restrict_knmi_rows(parsed,a.start,a.end,a.stations)
        meta.update(request_parameters=params,source_type='station_observation',
                    response_rows=len(parsed),retained_rows=len(rows),
                    excluded_outside_request=len(parsed)-len(rows),
                    warning='FX is preceding-hour maximum, not instantaneous launch-time gust')
        save(raw,meta,a.out)
        csvpath=a.out.with_suffix('.csv')
        with csvpath.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
        print(f'Saved {len(rows)} station-hour rows. No forecast performance calculated.')
    elif a.command=='single-run':
        params={'latitude':a.lat,'longitude':a.lon,'run':a.run,'models':a.model,
                'hourly':'wind_gusts_10m,wind_speed_10m','wind_speed_unit':'ms','timezone':'UTC','forecast_days':3}
        endpoint='https://single-runs-api.open-meteo.com/v1/forecast?'+urlencode(params)
        raw,meta=fetch(endpoint)
        payload=json.loads(raw)
        if payload.get('error') or 'hourly' not in payload:raise ValueError('No forecast data in response')
        meta.update(request_parameters=params,record_type=a.record_type,
                    availability_status='OPEN: establish publication latency before backtest')
        save(raw,meta,a.out);print('Saved one run. Archive type and availability still require verification.')
    else:
        if not re.fullmatch(r'\d{8}',a.date) or not 0<=a.lead<=384:raise ValueError('invalid date/lead')
        endpoint=(f'https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{a.date}/{a.cycle}/atmos/'
                  f'gfs.t{a.cycle}z.pgrb2.0p25.f{a.lead:03d}.idx')
        raw,meta=fetch(endpoint)
        text=raw.decode()
        lines=text.splitlines()
        hits=[]
        for j,line in enumerate(lines):
            if ':GUST:surface:' in line:
                parts=line.split(':');start=int(parts[1]);end=int(lines[j+1].split(':')[1])-1 if j+1<len(lines) else None
                hits.append({'index_entry':line,'start_byte':start,'end_byte':end})
        if not hits:raise ValueError('No surface GUST message found; do not substitute a different variable')
        meta.update(gust_ranges=hits,grib_url=endpoint[:-4],
                    status='INDEX_ONLY: field decoding and statistical-process semantics must be verified')
        save(raw,meta,a.out);print(json.dumps(hits,indent=2))

if __name__=='__main__':main()
