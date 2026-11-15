"""Optional headless Chromium visual review (requires websocket-client).

Uses a separate browser profile, localhost only; saves evidence under reports/.
Does not interact with the presenter's open browser or personal profile.
"""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import time

import requests
import websocket


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8513/?source=real")
    parser.add_argument("--output", type=Path, default=Path("reports/final_visual"))
    parser.add_argument("--port", type=int, default=9224)
    parser.add_argument("--browser", type=Path, default=Path("C:/Program Files/Google/Chrome/Application/chrome.exe"))
    parser.add_argument("--attach", action="store_true", help="Usar un navegador de revisión ya iniciado en localhost")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    browser = args.browser
    process = None if args.attach else subprocess.Popen([str(browser), "--headless=new", f"--remote-debugging-port={args.port}",
                                "--remote-debugging-address=127.0.0.1", "--remote-allow-origins=http://localhost",
                                f"--user-data-dir={args.output.resolve() / 'profile'}", "--no-first-run",
                                "--no-default-browser-check", "--disable-extensions", "--window-size=1600,1100", "about:blank"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    connection = None
    events, results = [], []
    try:
        for _ in range(100):
            try:
                tabs = requests.get(f"http://127.0.0.1:{args.port}/json", timeout=1).json()
                page = next(tab for tab in tabs if tab.get("type") == "page")
                break
            except (requests.RequestException, StopIteration):
                time.sleep(.2)
        else:
            raise RuntimeError("No se pudo iniciar Edge headless")
        connection = websocket.create_connection(page["webSocketDebuggerUrl"], origin="http://localhost", timeout=60)
        counter = 0

        def call(method, params=None):
            nonlocal counter
            counter += 1
            connection.send(json.dumps(dict(id=counter, method=method, params=params or {})))
            while True:
                reply = json.loads(connection.recv())
                if reply.get("id") == counter:
                    if "error" in reply:
                        raise RuntimeError(reply["error"])
                    return reply.get("result", {})
                if reply.get("method") in ("Runtime.exceptionThrown", "Log.entryAdded"):
                    events.append(reply)

        def js(expression):
            result = call("Runtime.evaluate", dict(expression=expression, returnByValue=True, awaitPromise=True))
            if "exceptionDetails" in result:
                raise RuntimeError(result["exceptionDetails"])
            return result.get("result", {}).get("value")

        call("Page.enable")
        call("Runtime.enable")
        call("Log.clear")
        call("Log.enable")
        call("Emulation.setDeviceMetricsOverride", dict(width=1600, height=1100, deviceScaleFactor=1, mobile=False))
        call("Page.navigate", dict(url=args.url))
        for _ in range(120):
            if js("document.body.innerText.includes('16,836') && document.querySelectorAll('[role=tab]').length===5"):
                break
            time.sleep(.5)
        else:
            raise RuntimeError("La vista real no cargó los indicadores esperados")
        time.sleep(3)
        for index in range(5):
            label = js(f"document.querySelectorAll('[role=tab]')[{index}].innerText")
            js(f"document.querySelectorAll('[role=tab]')[{index}].click()")
            time.sleep(1)
            js(f"document.querySelectorAll('[role=tab]')[{index}].scrollIntoView({{block:'start'}})")
            time.sleep(.5)
            shot = call("Page.captureScreenshot", dict(format="png", captureBeyondViewport=False))
            name = f"tab_{index+1}.png"
            (args.output / name).write_bytes(base64.b64decode(shot["data"]))
            panel = js("(()=>{const p=[...document.querySelectorAll('[role=tabpanel]')].find(p=>p.getAttribute('aria-hidden')!=='true' && p.offsetHeight>0); return p ? p.innerText : ''})()")
            results.append(dict(tab=index+1, label=label, screenshot=name, visible_text=panel))
        js("document.querySelectorAll('[role=tab]')[1].click()")
        js("[...document.querySelectorAll('h3')].find(x=>x.innerText.includes('Comparación diaria'))?.scrollIntoView({block:'start'})")
        time.sleep(1)
        shot = call("Page.captureScreenshot", dict(format="png", captureBeyondViewport=False))
        (args.output / "daily.png").write_bytes(base64.b64decode(shot["data"]))
        result = dict(url=args.url, tabs=results, browser_events=events,
                      visible_app_errors=js("[...document.querySelectorAll('[data-testid=stException]')].map(e=>e.innerText)"))
        (args.output / "review.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(dict(tabs=len(results), errors=result["visible_app_errors"], events=len(events), output=str(args.output))))
    finally:
        if connection:
            connection.close()
        if process:
            process.terminate()
            process.wait(timeout=15)


if __name__ == "__main__":
    main()
