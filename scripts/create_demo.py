"""Generate explicitly SYNTHETIC sample detections for UX/testing, never cite as NASA observations."""
from pathlib import Path
import csv
import random
from datetime import datetime, timedelta

rnd = random.Random(26024)
base = Path(__file__).resolve().parents[1] / "data"
base.mkdir(exist_ok=True)
modis, viirs = [], []
SITES = [(-9.4,-74.7), (-10.6,-74.2), (-8.9,-75.3), (-9.9,-73.8), (-11.1,-75.0), (-8.5,-74.2)]
for year in range(2022, 2027):
    for month in range(1, (12 if year == 2026 else 13)):
        dry = 2.0 if month in (7,8,9,10) else 0.85
        anomaly = 2.9 if year == 2026 and month in (8,9,10) else 1.0
        n = max(2, int(rnd.randint(3, 7) * dry * anomaly))
        for _ in range(n):
            day = rnd.randint(1, 25)
            hour = rnd.choice([2, 7, 13, 18])
            minute = rnd.randint(0,59)
            date = f"{year}-{month:02d}-{day:02d}"
            lat,lon = rnd.choice(SITES)
            lat += rnd.uniform(-.045,.045)
            lon += rnd.uniform(-.045,.045)
            if rnd.random() < .80:
                modis.append({"latitude":round(lat,5), "longitude":round(lon,5),"acq_date":date,"acq_time":f"{hour:02d}{minute:02d}","satellite":"Terra","instrument":"MODIS","confidence":rnd.randint(30,98),"frp":round(rnd.uniform(4,45),2),"version":"6.1NRT"})
            # Multiple VIIRS 375m nominal detections from neighboring positions.
            for _ in range(rnd.choice([1,2,3])):
                viirs.append({"latitude":round(lat+rnd.uniform(-.002,.002),5),"longitude":round(lon+rnd.uniform(-.002,.002),5),"acq_date":date,"acq_time":f"{hour:02d}{minute:02d}","satellite":"N20","instrument":"VIIRS","confidence":rnd.choice(["n","n","h","l"]),"frp":round(rnd.uniform(1,30),2),"version":"2.0NRT"})
for name, rows in [("demo_modis.csv",modis), ("demo_viirs.csv",viirs)]:
    with (base/name).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
print("EJEMPLO SINTÉTICO (no NASA):", len(modis), "MODIS;", len(viirs), "VIIRS")
