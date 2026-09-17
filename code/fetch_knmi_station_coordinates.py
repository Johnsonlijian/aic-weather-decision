"""Obtain official KNMI station coordinates from a public, licensed source.

The KNMI station-list file on the provider CDN answers HTTP 403 to programmatic
clients, so the coordinates used for the grid lookup are taken from the published
CRAN package ``spatialrisk``, whose ``knmi_stations`` data set contains the KNMI
station table (station id, name, latitude, longitude).  The package source is
downloaded from CRAN, the ``.rda`` payload is extracted, and R reads it into CSV.

Nothing is typed from memory: every coordinate in the output comes out of that
published data set, and the extraction records the tarball hash.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CRAN = "https://cran.r-project.org/src/contrib"
PACKAGE = "spatialrisk"
RSCRIPT = r"C:\Program Files\R\R-4.6.0\bin\x64\Rscript.exe"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "sources" / "raw" / "knmi_stations"
    work.mkdir(parents=True, exist_ok=True)

    # current version from the CRAN index
    ua = {"User-Agent": "Mozilla/5.0 (research metadata retrieval)"}
    with urllib.request.urlopen(urllib.request.Request(f"{CRAN}/PACKAGES", headers=ua),
                                timeout=60) as resp:
        index = resp.read().decode("utf-8", "replace")
    block = index.split(f"Package: {PACKAGE}\n", 1)[1].split("\n\n", 1)[0]
    version = next(line.split(":", 1)[1].strip() for line in block.splitlines()
                   if line.startswith("Version:"))
    tarball_url = f"{CRAN}/{PACKAGE}_{version}.tar.gz"
    tarball = work / f"{PACKAGE}_{version}.tar.gz"
    with urllib.request.urlopen(urllib.request.Request(tarball_url, headers=ua), timeout=180) as resp:
        data = resp.read()
    tarball.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()

    rda_path = None
    with tarfile.open(tarball) as tar:
        for member in tar.getmembers():
            if member.name.endswith("data/knmi_stations.rda"):
                rda_path = work / "knmi_stations.rda"
                rda_path.write_bytes(tar.extractfile(member).read())
                break
    if rda_path is None:
        raise SystemExit(f"knmi_stations.rda not found inside {tarball.name}")

    csv_path = work / "knmi_stations.csv"
    r_script = work / "extract_stations.R"
    r_script.write_text(
        'load("' + str(rda_path).replace("\\", "/") + '")\n'
        'write.csv(knmi_stations, "' + str(csv_path).replace("\\", "/") + '", row.names = FALSE)\n'
        'cat(nrow(knmi_stations), "stations written\\n")\n'
        'cat(paste(names(knmi_stations), collapse = ","), "\\n")\n',
        encoding="utf-8")
    result = subprocess.run([RSCRIPT, str(r_script)], capture_output=True, text=True)
    print(result.stdout.strip() or result.stderr[:400])

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_package": PACKAGE,
        "source_version": version,
        "tarball_url": tarball_url,
        "tarball_sha256": digest,
        "extracted": "data/knmi_stations.rda",
        "csv": str(csv_path.relative_to(root)),
        "r_stdout": result.stdout.strip(),
        "why_this_source": ("KNMI's own station-list file returns HTTP 403 to programmatic "
                            "clients; this published CRAN data set carries the KNMI station "
                            "table and is fetched from CRAN with a recorded hash."),
    }
    (root / "outputs" / "gates" / "G3_knmi_station_coordinates_source.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"version": version, "sha256": digest[:16], "csv": report["csv"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
