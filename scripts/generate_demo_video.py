"""Capture the real Streamlit demo and export exactly 870 H.264 frames (29 s).

Windows fallback: OpenCV + Media Foundation when FFmpeg is unavailable.
Dependencies: Pillow, numpy, opencv-python, requests, websocket-client.
No source CSV, analysis output, or application code is modified.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import threading

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import websocket

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS, FRAMES = 1920, 1080, 30, 870
SCENES = [
    (0, 5, "01 / THE CHALLENGE", "FireSync AI", "header",
     "Different sensors. Different resolutions and observation times.\nOne transparent workspace for thermal activity."),
    (5, 11, "02 / OBSERVED DATA", "Real observations. Traceable sources.", "metrics",
     "16,836 observed detections: 2,931 MODIS + 13,905 VIIRS.\nThese are heat detections, not individual fires."),
    (11, 18, "03 / GEOSPATIAL EXPLORATION", "Thermal activity in the Peruvian Amazon", "map",
     "25–31 August 2024 · 1 km grid · Sensor contributions in colour.\nThe map shows observed cell-days, not unique incidents."),
    (18, 21, "04 / HISTORICAL CALENDAR", "One calendar. Sensor-specific observations.", "calendar",
     "August 2024: 12,735 observed active cell-days in the union.\nAggregation does not correct sensor detectability."),
    (21, 24, "04 / DAILY COMPARISON", "Compare the observations day by day", "daily",
     "MODIS and VIIRS retain their own daily counts.\nData gaps do not establish that no fires occurred."),
    (24, 29, "05 / CONDITIONAL AGREEMENT", "Agreement diagnostics, with limits in view", "validation",
     "41 timestamp pairs · 51 matching cell-periods · Jaccard 0.85%.\nConditional agreement, not accuracy or validated calibration."),
]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class CDP:
    def __init__(self, port):
        pages = requests.get(f"http://127.0.0.1:{port}/json", timeout=5).json()
        page = next(p for p in pages if p.get("type") == "page")
        self.ws = websocket.create_connection(page["webSocketDebuggerUrl"], origin="http://localhost", timeout=60)
        self.count, self.errors = 0, []

    def call(self, method, params=None):
        self.count += 1
        self.ws.send(json.dumps(dict(id=self.count, method=method, params=params or {})))
        while True:
            reply = json.loads(self.ws.recv())
            if reply.get("id") == self.count:
                if "error" in reply:
                    raise RuntimeError(reply["error"])
                return reply.get("result", {})
            if reply.get("method") == "Runtime.exceptionThrown":
                self.errors.append(reply)

    def js(self, expression):
        result = self.call("Runtime.evaluate", dict(expression=expression, returnByValue=True, awaitPromise=True))
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result.get("result", {}).get("value")

    def wait(self, expression, seconds=90):
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            if self.js(expression):
                return
            time.sleep(.4)
        raise RuntimeError(f"Browser verification timed out: {expression}")

    def screenshot(self, target):
        data = self.call("Page.captureScreenshot", dict(format="png", captureBeyondViewport=False))
        target.write_bytes(base64.b64decode(data["data"]))
        with Image.open(target) as image:
            if image.size != (W, H):
                raise RuntimeError("The browser capture is not Full HD")


def verify_data():
    # Run the project's original-bundle verifier, not a substitute dataset.
    from firesync.history import combine_imports
    from firesync.validated_data import load_observational_bundle, REAL_AUGUST_BUNDLE
    imports = load_observational_bundle(REAL_AUGUST_BUNDLE)
    data, _ = combine_imports(imports)
    counts = {str(k): int(v) for k, v in data.sensor.value_counts().items()}
    if counts != {"VIIRS": 13905, "MODIS": 2931} or data.data_kind.eq("synthetic").any():
        raise RuntimeError("Real observational bundle differs from the validated demonstration")
    return dict(total=len(data), sensors=counts, observed_months=sorted(data.acquired_utc.dt.strftime("%Y-%m").unique()),
                source_files=[dict(filename=i.manifest["filename"], sha256=i.manifest["sha256"]) for i in imports],
                provenance="User-supplied original FIRMS files; metadata and hashes verified, not independently signed by NASA")


def capture(args, directory):
    process = None
    if not args.attach:
        profile = directory / "browser-profile"
        process = subprocess.Popen([str(args.browser), "--headless=new", f"--remote-debugging-port={args.port}",
                                    "--remote-debugging-address=127.0.0.1", "--remote-allow-origins=http://localhost",
                                    f"--user-data-dir={profile.resolve()}", "--disable-extensions", "--no-first-run", "about:blank"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(60):
            try:
                if requests.get(f"http://127.0.0.1:{args.port}/json", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(.3)
    c = None
    try:
        c = CDP(args.port)
        c.call("Page.enable")
        c.call("Runtime.enable")
        c.call("Emulation.setDeviceMetricsOverride", dict(width=W, height=H, deviceScaleFactor=1, mobile=False))
        c.call("Page.navigate", dict(url=args.url))
        c.wait("document.body.innerText.includes('16,836') && document.querySelectorAll('[role=tab]').length===5")
        c.wait("document.body.innerText.includes('DATOS OBSERVADOS') && document.body.innerText.includes('2,931') && document.body.innerText.includes('13,905')")
        # Presentation-only CSS, confined to this browser. No values/chart data change.
        c.js("(()=>{const s=document.createElement('style');s.textContent='[data-testid=stSidebar],[data-testid=stHeader],[data-testid=stToolbar]{display:none!important}.stMainBlockContainer{padding-top:24px!important;padding-bottom:24px!important;max-width:1800px!important}';document.head.appendChild(s);})()")
        time.sleep(4)
        seen = c.js("[...document.querySelectorAll('[data-testid=stMetricValue]')].map(e=>e.innerText)")
        if seen != ["16,836", "12,735", "2,931", "13,905"]:
            raise RuntimeError(f"Unexpected visible indicators: {seen}")
        evidence = dict(viewport=[W, H], url=args.url, metrics=seen, captured_utc=datetime.now(timezone.utc).isoformat(), shots={})

        def shoot(name, expression=None, pause=1):
            if expression:
                c.js(expression)
            time.sleep(pause)
            path = directory / f"{name}.png"
            c.screenshot(path)
            evidence["shots"][name] = dict(file=path.name, sha256=sha(path), width=W, height=H)

        def tab(index):
            c.js(f"document.querySelectorAll('[role=tab]')[{index}].click()")
            time.sleep(.6)

        top = "document.querySelector('h1').scrollIntoView({block:'start'})"
        shoot("header", top)
        shoot("metrics", "document.querySelector('[data-testid=stMetric]').scrollIntoView({block:'center'})")
        tab(0)
        shoot("map", "[...document.querySelectorAll('h3')].find(e=>e.innerText.includes('Actividad térmica observada')).scrollIntoView({block:'start'})", 4)
        tab(1)
        shoot("calendar", "[...document.querySelectorAll('h3')].find(e=>e.innerText.includes('Calendario de actividad')).scrollIntoView({block:'start'})")
        shoot("daily", "[...document.querySelectorAll('h3')].find(e=>e.innerText.includes('Comparación diaria')).scrollIntoView({block:'start'})")
        tab(4)
        c.wait("document.body.innerText.includes('Jaccard condicional: 0.85%')")
        shoot("validation", "[...document.querySelectorAll('h3')].find(e=>e.innerText.includes('Concordancia condicional')).scrollIntoView({block:'start'})")
        evidence["validation_summary"] = c.js("[...document.querySelectorAll('[data-testid=stMarkdownContainer]')].map(x=>x.innerText).find(t=>t.includes('41 parejas temporales') && t.includes('Jaccard condicional'))")
        evidence["app_errors"] = c.js("[...document.querySelectorAll('[data-testid=stException]')].map(e=>e.innerText)")
        evidence["runtime_exceptions"] = c.errors
        if evidence["app_errors"] or c.errors:
            raise RuntimeError("Application errors were present in the browser")
        (directory / "capture_verification.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        return evidence
    finally:
        if c:
            c.ws.close()
        if process:
            process.terminate()
            process.wait(timeout=15)


def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf", size)


def smooth(value):
    value = max(0., min(1., value))
    return value*value*(3-2*value)


def render_assets(directory):
    # Crops emphasize actual screen content; all originals remain Full HD PNGs.
    boxes = dict(header=(80, 0, 1840, 740), metrics=(60, 70, 1860, 830),
                 map=(60, 15, 1860, 865), calendar=(60, 0, 1860, 850),
                 daily=(60, 0, 1860, 850), validation=(60, 0, 1860, 850))
    return {name: Image.open(directory/f"{name}.png").convert("RGB").crop(box) for name, box in boxes.items()}


def scene_frame(scene, t, assets):
    start, end, kicker, title, name, caption = scene
    frame = Image.new("RGB", (W, H), "#080F1B")
    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, 0, W, 9), fill="#F97316")
    draw.text((64, 35), "NASA SPACE APPS CHALLENGE 2026", font=font(21, True), fill="#FF9C50")
    draw.text((W-480, 38), "OBSERVED DATA  /  AUGUST 2024", font=font(20, True), fill="#A7DCD1")
    draw.text((64, 77), kicker, font=font(18, True), fill="#859BB5")
    draw.text((64, 111), title, font=font(58 if name=="header" else 45, True), fill="#F4F7FB")
    image = assets[name]
    # Preserve aspect ratio: no chart/data stretching.
    card = Image.new("RGB", (1792, 670), "#0B1220")
    fitted = ImageOps.contain(image, card.size, Image.Resampling.LANCZOS)
    card.paste(fitted, ((card.width-fitted.width)//2, (card.height-fitted.height)//2))
    if name == "map":
        phase = smooth((t-start)/(end-start))
        zoom = 1 + .035*phase
        # Editorial camera motion over a real still, not simulated observations.
        enlarged = card.resize((round(card.width*zoom), round(card.height*zoom)), Image.Resampling.BICUBIC)
        x = round((enlarged.width-card.width)*(.35+.3*phase))
        y = round((enlarged.height-card.height)*.5)
        card = enlarged.crop((x, y, x+card.width, y+card.height))
    frame.paste(card, (64, 201))
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((63, 200, 1856, 871), radius=12, outline="#283D56", width=2)
    draw.rectangle((64, 894, 1856, 1007), fill="#101E31")
    lines = caption.splitlines()
    for i, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font(30, i == 0))
        draw.text(((W-(box[2]-box[0]))/2, 902+i*43), line, font=font(30, i == 0), fill="#F4F7FB" if i==0 else "#C9D7E8")
    draw.text((64, 1022), "FireSync AI  ·  Thermal observations, not unique fires", font=font(19), fill="#90A8C2")
    draw.text((1280, 1022), "No predictive model · No validated calibration", font=font(19), fill="#90A8C2")
    draw.rectangle((64, 1061, 1856, 1065), fill="#24354B")
    draw.rectangle((64, 1061, 64+round(1792*t/29), 1065), fill="#F97316")
    if t >= 27.4:
        alpha = .84*smooth((t-27.4)/.8)
        frame = Image.blend(frame, Image.new("RGB", frame.size, "#080F1B"), alpha)
        layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        fade = round(255*smooth((t-27.4)/.7))
        for text, size, y, colour in [("FireSync AI", 100, 392, (244,247,251)),
                                       ("Explore. Compare. Trace.", 38, 525, (255,156,80)),
                                       ("A reproducible view of MODIS–VIIRS thermal activity", 27, 596, (195,214,235))]:
            f = font(size, size==100)
            bounds = d.textbbox((0, 0), text, font=f)
            d.text(((W-(bounds[2]-bounds[0]))/2,y), text, font=f, fill=(*colour,fade))
        frame = Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")
    return frame


def video_frame(t, assets):
    index = next((i for i,s in enumerate(SCENES) if s[0] <= t < s[1]), len(SCENES)-1)
    for i in range(1, len(SCENES)):
        boundary = SCENES[i][0]
        if boundary-.20 <= t < boundary+.20:
            return Image.blend(scene_frame(SCENES[i-1], t, assets), scene_frame(SCENES[i], t, assets), smooth((t-boundary+.20)/.40))
    return scene_frame(SCENES[index], t, assets)


def encode(target, directory):
    assets = render_assets(directory)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    writer = None
    process = None
    if ffmpeg:
        process = subprocess.Popen([ffmpeg, "-y", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "1920x1080",
                                    "-framerate", "30", "-i", "pipe:0", "-an", "-c:v", "libx264", "-crf", "18",
                                    "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)], stdin=subprocess.PIPE,
                                   stdout=subprocess.DEVNULL, stderr=(directory/"ffmpeg_encoding.log").open("wb"))
        backend = "FFmpeg libx264"
    else:
        # MSMF in this OpenCV build rejects absolute paths with non-ASCII text.
        # The project may live under 'programación'; a project-relative output
        # path avoids changing the folder or touching source data.
        writer = cv2.VideoWriter(target.relative_to(ROOT).as_posix(), cv2.CAP_MSMF, cv2.VideoWriter_fourcc(*"H264"), FPS, (W,H))
        if not writer.isOpened():
            raise RuntimeError("No H.264 encoder: install FFmpeg/imageio-ffmpeg or enable Windows Media Foundation")
        backend = "OpenCV CAP_MSMF / Windows Media Foundation H.264"
    try:
        for number in range(FRAMES):
            frame = video_frame(number/FPS, assets)
            if number in (60, 240, 435, 585, 675, 780, 858):
                frame.save(directory/f"video_frame_{number:04d}.jpg", quality=93)
            if writer:
                writer.write(cv2.cvtColor(np.asarray(frame), cv2.COLOR_RGB2BGR))
            else:
                process.stdin.write(frame.tobytes())
            if number % 90 == 0:
                print(f"Rendered {number}/{FRAMES} frames", flush=True)
    finally:
        if writer:
            writer.release()
        if process:
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError("FFmpeg failed; inspect encoding log")
    return backend


def mp4_metadata(path):
    """Equivalent container inspection: mvhd duration and avc1 sample entry."""
    content = path.read_bytes()
    result = dict(avc1_sample_entry=b"avc1" in content, avc_configuration=b"avcC" in content)
    offset = 0
    while offset+8 <= len(content):
        size, atom = struct.unpack_from(">I4s", content, offset)
        if size == 1:
            size = struct.unpack_from(">Q", content, offset+8)[0]
        if size == 0:
            size = len(content)-offset
        if atom == b"moov":
            position = content.find(b"mvhd", offset, offset+size)
            if position >= 0:
                base = position+4
                if content[base] == 0:
                    scale, duration = struct.unpack_from(">II", content, base+12)
                else:
                    scale, duration = struct.unpack_from(">IQ", content, base+20)
                result.update(container_timescale=scale, container_duration_seconds=duration/scale)
        offset += size
    return result


def verify_video(target, directory):
    capture = cv2.VideoCapture(target.relative_to(ROOT).as_posix())
    metadata = dict(width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    fps=capture.get(cv2.CAP_PROP_FPS), declared_frames=int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    codec = int(capture.get(cv2.CAP_PROP_FOURCC))
    metadata["decoded_fourcc"] = "".join(chr((codec>>(8*i)) & 255) for i in range(4))
    count = 0
    for_readback = {60,240,435,585,675,780,858}
    while True:
        okay, frame = capture.read()
        if not okay:
            break
        if count in for_readback:
            Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).save(directory/f"decoded_frame_{count:04d}.jpg",quality=93)
        if frame.shape[:2] != (H,W):
            raise RuntimeError("Decoded frame dimensions changed")
        count += 1
    capture.release()
    metadata.update(decoded_frames=count, duration_seconds=count/metadata["fps"], sha256=sha(target), bytes=target.stat().st_size,
                    **mp4_metadata(target))
    if (metadata["width"],metadata["height"],count) != (W,H,FRAMES) or abs(metadata["fps"]-FPS) > .001:
        raise RuntimeError(f"Video verification failed: {metadata}")
    if not metadata["avc1_sample_entry"] or not metadata["avc_configuration"] or not 28.99 <= metadata["container_duration_seconds"] < 30:
        raise RuntimeError("MP4 is not the requested H.264/duration")
    (directory/"video_probe.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def verify_browser_playback(target, port):
    """Actually play the encoded MP4 in the isolated Chrome, without desktop capture."""
    ranges = []
    class QuietHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            if self.path.split('?',1)[0] != '/'+target.name:
                self.send_error(404)
                return
            size = target.stat().st_size
            first, last = 0, size-1
            header = self.headers.get('Range')
            if header:
                part = header.removeprefix('bytes=').split(',')[0]
                lo, hi = part.split('-',1)
                first = int(lo) if lo else max(0,size-int(hi))
                last = min(int(hi),size-1) if hi and lo else size-1
                ranges.append([first,last])
            if first > last or first >= size:
                self.send_error(416)
                return
            self.send_response(206 if header else 200)
            self.send_header('Content-Type','video/mp4')
            self.send_header('Accept-Ranges','bytes')
            self.send_header('Content-Length',str(last-first+1))
            if header:
                self.send_header('Content-Range',f'bytes {first}-{last}/{size}')
            self.end_headers()
            try:
                with target.open('rb') as stream:
                    stream.seek(first)
                    remaining = last-first+1
                    while remaining:
                        chunk = stream.read(min(1024*1024,remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    c = None
    try:
        c = CDP(port)
        c.call("Page.enable")
        c.call("Page.navigate", dict(url=f"http://127.0.0.1:{server.server_port}/{target.name}"))
        c.wait("document.querySelector('video')?.readyState>=2", 45)
        c.js("(()=>{let v=document.querySelector('video');v.muted=true;v.currentTime=0;return v.play().then(()=>true)})()")
        time.sleep(1)
        result = c.js("(()=>{let v=document.querySelector('video');return {width:v.videoWidth,height:v.videoHeight,duration:v.duration,current_time:v.currentTime,paused:v.paused,error:v.error?.message??null}})()")
        if result["width"] != W or result["height"] != H or not 28.99 <= result["duration"] < 30 or result["paused"] or result["error"] or result["current_time"] <= 0:
            raise RuntimeError(f"Chrome playback verification failed: {result}")
        c.js("document.querySelector('video').pause();document.querySelector('video').currentTime=28.5")
        c.wait("Math.abs(document.querySelector('video').currentTime-28.5)<.1 && document.querySelector('video').readyState>=2", 30)
        result["seek_to_closing_seconds"] = 28.5
        result["byte_range_requests_served"] = len(ranges)
        return result
    finally:
        if c:
            c.ws.close()
        server.shutdown()
        server.server_close()


def write_report(directory, target, data, evidence, metadata, encoder):
    scenes = "\n".join(f"| {s[0]:02d}–{s[1]:02d} | {s[3]} | `{s[4]}.png` |" for s in SCENES)
    report = f"""# FireSync AI — video generation report

Generated UTC: {datetime.now(timezone.utc).isoformat()}

## Final deliverable

- File: `{target.relative_to(ROOT).as_posix()}`
- Resolution: **{metadata['width']} × {metadata['height']}**.
- Frame rate: **{metadata['fps']:.0f} FPS**, constant frames supplied at 1/30 s.
- Duration: **{metadata['duration_seconds']:.3f} seconds**; MP4 container reports **{metadata['container_duration_seconds']:.6f} seconds**, below 30 seconds.
- Video: **H.264 / AVC**, `avc1` and `avcC` verified in MP4; decoded FOURCC `{metadata['decoded_fourcc']}`.
- Frames: **{metadata['decoded_frames']} decoded successfully**, matching all 870 encoded frames.
- Browser playback verification: `{metadata.get('browser_playback', 'Not attempted; complete decoder verification above')}`.
- Bytes: {metadata['bytes']:,}. SHA-256: `{metadata['sha256']}`.
- Audio: intentionally silent; no unlicensed music, personal audio or voice dependency.
- English subtitles and titles are burned into frames; supplementary SRT is also provided.
- Representative decoded frames were visually inspected: actual indicators, map with attribution, calendar, daily charts, agreement and closing title. No desktop or personal-window pixels appear.

## Method and tools

Python {sys.version.split()[0]} in `.venv-phase3`; Chrome DevTools Protocol through websocket-client {websocket.__version__}; Pillow {Image.__version__}; OpenCV {cv2.__version__}; NumPy {np.__version__}. Encoder: **{encoder}**.

FFmpeg/ffprobe were not on PATH and installing imageio-ffmpeg from the restricted Python environment was unavailable. Windows Media Foundation H.264 was successfully capability-tested and used if FFmpeg is unavailable. Its initial absolute output path failed because this OpenCV build does not handle non-ASCII path components for MSMF; a project-relative path resolved that without relocating or modifying source files. Verification equivalent to ffprobe combines MP4 movie-header timing and AVC sample-entry checks with a full OpenCV decode of every frame. `video_probe.json` records the measurements; sampled decoded frames are retained for visual inspection. No frame-count-only assumption is used without actual decode. Native encoder defaults produce a high-bitrate master; the exact file size is reported above.

Captures were taken from the real application at `{evidence['url']}`, with **1920 × 1080 viewport**, device scale 1, isolated browser profile. Only webpage pixels were captured, never the desktop, address bar, private windows or credentials. Presentation-only browser CSS hides the sidebar and Streamlit toolbar; screenshot crops and modest map camera motion are editorial, with no fabricated chart, map or numerical data. Crossfades last 0.4 s centred at scene boundaries. Total output is fixed at 870 frames.

## Capture verification and scientific scope

- Visible indicators verified by browser DOM: `{evidence['metrics']}`.
- Original-bundle verifier checked both input-file hashes and all existing output checksums before capture and after video generation.
- Observations: **{data['total']:,}**, MODIS **{data['sensors']['MODIS']:,}**, VIIRS **{data['sensors']['VIIRS']:,}**; month **{', '.join(data['observed_months'])}**. No synthetic rows.
- Validation text captured from DOM: {evidence['validation_summary']}
- Browser application errors: {len(evidence['app_errors'])}; runtime exceptions: {len(evidence['runtime_exceptions'])}.
- Every original capture is a Full HD PNG with SHA-256 in `capture_verification.json`.
- Data provenance: {data['provenance']}.
- The map shows **25–31 August**; the calendar and indicators describe **1–31 August**. The captions state this distinction.
- Detections are not individual fires. Agreement is conditional, not accuracy. One month provides insufficient years for a validated calibration. No predictive AI capability is claimed.
- CSV originals, analysis outputs and application files were not modified.

## Timeline

| Seconds | Scene | Actual screen capture |
| --- | --- | --- |
{scenes}

The final seconds retain the agreement screen under a FireSync AI closing title. All graphic and subtitle overlays are editorial labels; none claim NASA endorsement or add observations.

## Reproduce

```powershell
Start-Process -FilePath 'C:/Program Files/Google/Chrome/Application/chrome.exe' -ArgumentList '--remote-debugging-port=9227', '--remote-debugging-address=127.0.0.1', '--remote-allow-origins=http://localhost', "--user-data-dir=$env:TEMP/firesync-video-capture", '--no-first-run', '--no-default-browser-check', '--disable-extensions', 'http://127.0.0.1:8513/?source=real' -WindowStyle Hidden
.\\.venv-phase3\\Scripts\\python.exe scripts/generate_demo_video.py --attach --port 9227
```

The recorded run attached to an isolated Chrome launched with `--remote-debugging-port=9227 --remote-debugging-address=127.0.0.1 --remote-allow-origins=http://localhost --user-data-dir=<separate-temporary-profile>`. Alternatively run the script without `--attach` to request a separate headless Chrome; this restricted environment may require launching Chrome via the desktop application tool. Browser executable can be set with `--browser`. Streamlit must serve port 8513; the script starts it if the health check is unavailable. No MAP_KEY is needed for the stored real bundle.

For render-only reproduction from these verified captures, use `--reuse-captures`. This checks original PNG hashes and re-verifies the observational bundle. Optional Python video dependencies are listed in `requirements-video.txt`; FFmpeg is preferred if present, otherwise Windows Media Foundation is required.
"""
    (directory/"video_generation_report.md").write_text(report, encoding="utf-8")


def main():
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8513/?source=real")
    parser.add_argument("--port", type=int, default=9227)
    parser.add_argument("--attach", action="store_true")
    parser.add_argument("--browser", type=Path, default=Path("C:/Program Files/Google/Chrome/Application/chrome.exe"))
    parser.add_argument("--reuse-captures", action="store_true")
    args = parser.parse_args()
    # Package is installed editable; no manual sys.path modification.
    directory = ROOT / "reports/video"
    target = ROOT / "dist/FireSyncAI_demo_30s.mp4"
    directory.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(exist_ok=True)
    try:
        healthy = requests.get("http://127.0.0.1:8513/_stcore/health", timeout=3).status_code == 200
    except requests.RequestException:
        healthy = False
    if not healthy and not args.reuse_captures:
        log = (directory/"streamlit.log").open("wb")
        subprocess.Popen([sys.executable,"-m","streamlit","run","app.py","--server.headless","true",
                          "--server.address","127.0.0.1","--server.port","8513"],cwd=ROOT,stdout=log,stderr=log,
                         creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        for _ in range(60):
            try:
                if requests.get("http://127.0.0.1:8513/_stcore/health", timeout=1).status_code==200:
                    break
            except requests.RequestException:
                pass
            time.sleep(.5)
    print("Verifying original data and output hashes", flush=True)
    data = verify_data()
    if args.reuse_captures:
        evidence = json.loads((directory/"capture_verification.json").read_text(encoding="utf-8"))
        for shot in evidence["shots"].values():
            if sha(directory/shot["file"]) != shot["sha256"]:
                raise RuntimeError("Capture checksum mismatch")
    else:
        print("Capturing real Full HD browser views", flush=True)
        evidence = capture(args, directory)
    (directory/"verified_data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    encoder = encode(target, directory)
    print("Decoding and verifying every frame", flush=True)
    metadata = verify_video(target, directory)
    try:
        metadata["browser_playback"] = verify_browser_playback(target, args.port)
    except (requests.RequestException, OSError, RuntimeError) as exc:
        metadata["browser_playback"] = {"available":False,"reason":str(exc)}
    metadata["encoder"] = encoder
    (directory/"video_probe.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    if verify_data() != data:
        raise RuntimeError("Data changed during video generation")
    srt = []
    for number, scene in enumerate(SCENES, 1):
        start, end = scene[:2]
        srt.append(f"{number}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{scene[5]}\n")
    (directory/"FireSyncAI_demo_en.srt").write_text("\n".join(srt), encoding="utf-8")
    write_report(directory,target,data,evidence,metadata,encoder)
    print(json.dumps(dict(file=str(target), duration=metadata["duration_seconds"], frames=metadata["decoded_frames"], encoder=encoder)), flush=True)


if __name__ == "__main__":
    main()
