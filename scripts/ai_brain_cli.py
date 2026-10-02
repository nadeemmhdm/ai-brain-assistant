#!/usr/bin/env python3
"""Cross-platform AI Brain CLI.

Uses the same local backend API as the Web UI, so CLI and UI operate on the
same Brain, learning sessions, models and persisted data.
"""
from __future__ import annotations
import argparse, json, sys, time, urllib.request, urllib.error

DEFAULT = "http://127.0.0.1:8000"

def request(base, path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}

def main():
    p=argparse.ArgumentParser(prog="ai-brain", description="AI Brain Assistant CLI")
    p.add_argument("--api", default=DEFAULT)
    sub=p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    learn=sub.add_parser("learn"); learn.add_argument("topic"); learn.add_argument("--wait", action="store_true")
    search=sub.add_parser("brain-search"); search.add_argument("query"); search.add_argument("--topic")
    sub.add_parser("topics")
    sources=sub.add_parser("sources"); sources.add_argument("--limit", type=int, default=20)
    ctl=sub.add_parser("learn-control"); ctl.add_argument("session_id"); ctl.add_argument("action", choices=["pause","resume","cancel"])
    args=p.parse_args()
    try:
        if args.cmd=="status": out=request(args.api,"/api/model/status")
        elif args.cmd=="topics": out=request(args.api,"/api/brain/topics")
        elif args.cmd=="sources": out=request(args.api,f"/api/brain/sources?limit={args.limit}")
        elif args.cmd=="brain-search":
            from urllib.parse import quote
            path=f"/api/brain/knowledge?query={quote(args.query)}"
            if args.topic: path += f"&topic={quote(args.topic)}"
            out=request(args.api,path)
        elif args.cmd=="learn-control": out=request(args.api,f"/api/learn/{args.action}?session_id={args.session_id}","POST")
        elif args.cmd=="learn":
            out=request(args.api,"/api/learn","POST",{"topic":args.topic})
            if args.wait:
                sid=out["session_id"]
                while True:
                    state=request(args.api,f"/api/learn/status?session_id={sid}")
                    print(f"\r{state.get('progress_pct',0):3}%  {state.get('current_task','')[:80]:80}",end="",flush=True)
                    if state.get("status") in {"completed","cancelled","error"}:
                        print(); out=state; break
                    time.sleep(1)
        print(json.dumps(out,ensure_ascii=False,indent=2))
    except urllib.error.HTTPError as e:
        print(f"API error {e.code}: {e.read().decode(errors='replace')}",file=sys.stderr); return 1
    except urllib.error.URLError:
        print("AI Brain backend is not reachable. Start run.bat/run.sh first.",file=sys.stderr); return 2
    return 0

if __name__=="__main__": raise SystemExit(main())
