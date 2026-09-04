"""VisualSpec -> a self-contained HTML slide with a word-timed animation track.

One renderer, two consumers: the browser stage plays it live, and Playwright
records it for the video artefact. Both read the same `cues` array, so what the
judge sees in the video is what the student sees in the app.

Elements start hidden and are revealed by `revealAt(ms)`, driven by word timings
from edge-tts. A graph draws its line progressively rather than appearing whole,
because the point of the V-I plot is watching proportionality emerge.
"""

from __future__ import annotations

import html
import json

from services.llm.schemas import Beat
from services.speech.tts import WordTiming

CDN_KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9"
CDN_MERMAID = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"


def element_ids(kind: str, payload: dict) -> list[str]:
    """DOM ids the renderer actually emits, in reveal order."""
    p = payload or {}
    if kind == "equation":
        return ["eq"] + [f"term-{t.get('id', i)}" for i, t in enumerate(p.get("terms") or [])]
    if kind == "graph":
        pts = (p.get("series") or [{}])[0].get("points") or []
        return ["line"] + [f"pt-{i}" for i in range(len(pts))]
    if kind == "diagram":
        return ["diagram"]
    if kind == "code":
        ids = [f"cl-{i}" for i in range(len(str(p.get("source", "")).splitlines() or [""]))]
        return ids + (["output"] if p.get("expected_output") else [])
    if kind == "bullets":
        head = ["heading"] if p.get("heading") else []
        return head + [f"b-{i}" for i in range(len(p.get("items") or []))]
    return []


def cues_for(beat: Beat, timings: list[WordTiming]) -> list[dict]:
    """Map each timeline cue onto a millisecond offset AND a real DOM id.

    The model invents element ids ("series[0]", "x_label") that the renderer
    does not emit. Rather than let those cues silently do nothing, resolve them:
    exact match first, then a `term-`/`b-` prefixed match, then by ordinal, so
    the Nth cue reveals the Nth revealable element.
    """
    real = element_ids(beat.visual.kind, beat.visual.payload)
    out = []
    for n, cue in enumerate(beat.visual.timeline):
        i = max(0, min(cue.word_index, len(timings) - 1)) if timings else 0
        raw = str(cue.element_id)
        if raw in real:
            el = raw
        elif f"term-{raw}" in real:
            el = f"term-{raw}"
        elif real:
            el = real[min(n, len(real) - 1)]
        else:
            el = raw
        out.append({
            "element": el,
            "requested": raw,
            "action": cue.action,
            "at_ms": timings[i].start_ms if timings else 0,
            "word_index": i,
        })
    return sorted(out, key=lambda c: c["at_ms"])


def _equation(p: dict) -> str:
    terms = p.get("terms") or []
    chips = "".join(
        f'<span class="term" id="term-{html.escape(str(t.get("id", i)))}">'
        f'<span class="tex">{html.escape(str(t.get("tex", "")))}</span>'
        f'<span class="lbl">{html.escape(str(t.get("label", "")))}</span></span>'
        for i, t in enumerate(terms)
    )
    return (
        f'<div class="eq" id="eq"></div>'
        f'<script>window.__latex={json.dumps(p.get("latex", ""))};</script>'
        f'<div class="terms">{chips}</div>'
    )


def _graph(p: dict) -> str:
    """Inline SVG. No plotting library, and the line draws progressively."""
    series = p.get("series") or [{}]
    pts = series[0].get("points") or [[0, 0]]
    schematic = bool(p.get("schematic"))
    xs = [float(x) for x, _ in pts] or [0.0]
    ys = [float(y) for _, y in pts] or [0.0]
    x_max, y_max = max(xs) or 1.0, max(ys) or 1.0
    W, H, PAD = 720, 420, 62

    def sx(x: float) -> float:
        return PAD + (x / x_max) * (W - 2 * PAD)

    def sy(y: float) -> float:
        return H - PAD - (y / y_max) * (H - 2 * PAD)

    path = " ".join(
        f"{'M' if i == 0 else 'L'}{sx(float(x)):.1f},{sy(float(y)):.1f}"
        for i, (x, y) in enumerate(pts)
    )
    dots = "".join(
        f'<circle class="pt" id="pt-{i}" cx="{sx(float(x)):.1f}" '
        f'cy="{sy(float(y)):.1f}" r="6"/>'
        for i, (x, y) in enumerate(pts)
    )
    # A schematic line asserts shape, not values, so it carries no numeric ticks.
    ticks = ""
    if not schematic:
        ticks = "".join(
            f'<text class="tick" x="{sx(float(x)):.1f}" y="{H - PAD + 22}">{x:g}</text>'
            f'<text class="tick" x="{PAD - 12}" y="{sy(float(y)):.1f}" '
            f'text-anchor="end">{y:g}</text>'
            for x, y in pts if float(x) or float(y)
        )
    badge = ('<text class="schematic" x="%d" y="28">schematic, not to scale</text>'
             % (W - PAD)) if schematic else ""
    return f"""<svg id="graph" viewBox="0 0 {W} {H}" role="img">
  <line class="axis" x1="{PAD}" y1="{H-PAD}" x2="{W-PAD}" y2="{H-PAD}"/>
  <line class="axis" x1="{PAD}" y1="{PAD}" x2="{PAD}" y2="{H-PAD}"/>
  <text class="axlbl" x="{W/2}" y="{H-14}">{html.escape(str(p.get('x_label','')))}</text>
  <text class="axlbl" transform="translate(18,{H/2}) rotate(-90)">{html.escape(str(p.get('y_label','')))}</text>
  {ticks}{badge}
  <path id="line" d="{path}" fill="none"/>
  {dots}
</svg>"""


def _diagram(p: dict) -> str:
    return f'<pre class="mermaid" id="diagram">{html.escape(str(p.get("mermaid", "")))}</pre>'


def _code(p: dict) -> str:
    src = html.escape(str(p.get("source", "")))
    lines = "".join(
        f'<div class="cl" id="cl-{i}">{l or "&nbsp;"}</div>'
        for i, l in enumerate(src.split("\n"))
    )
    out = p.get("expected_output")
    tail = (f'<div class="out" id="output"><span class="olbl">output</span>'
            f'<pre>{html.escape(str(out))}</pre></div>') if out else ""
    return f'<div class="code"><div class="lang">{html.escape(str(p.get("language","")))}</div>{lines}</div>{tail}'


def _bullets(p: dict) -> str:
    items = "".join(
        f'<li class="bullet" id="b-{i}">{html.escape(str(it))}</li>'
        for i, it in enumerate(p.get("items") or [])
    )
    head = p.get("heading")
    h = f'<h2 id="heading">{html.escape(str(head))}</h2>' if head else ""
    return f'{h}<ul class="bullets">{items}</ul>'


_RENDERERS = {
    "equation": _equation, "graph": _graph, "diagram": _diagram,
    "code": _code, "bullets": _bullets,
}

_CSS = """
:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--line:#30363d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.6 "Segoe UI",system-ui,"Nirmala UI","Noto Sans Devanagari",sans-serif}
.slide{width:1280px;height:720px;padding:44px 64px 24px;display:flex;flex-direction:column;
  gap:14px;position:relative;overflow:hidden}
.kicker{color:var(--accent);font-size:14px;letter-spacing:.14em;text-transform:uppercase}
h2{margin:0;font-size:38px;font-weight:650;line-height:1.25}
.stage{flex:1;display:flex;align-items:center;justify-content:center;min-height:0}
.reveal{opacity:0;transform:translateY(10px);transition:opacity .45s ease,transform .45s ease}
.reveal.on{opacity:1;transform:none}
.reveal.hl{color:var(--accent)}
.eq{font-size:46px;text-align:center}
.terms{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-top:8px}
.term{border:1px solid var(--line);border-radius:10px;padding:8px 14px;text-align:center}
.term .tex{display:block;font-size:22px;color:var(--accent)}
.term .lbl{display:block;font-size:13px;color:var(--muted)}
svg{width:100%;height:100%;max-height:460px}
.axis{stroke:var(--line);stroke-width:2}
.axlbl{fill:var(--muted);font-size:15px;text-anchor:middle}
.tick{fill:var(--muted);font-size:12px;text-anchor:middle}
.schematic{fill:var(--muted);font-size:13px;text-anchor:end;font-style:italic}
#line{stroke:var(--accent);stroke-width:3.5;stroke-linecap:round}
.pt{fill:var(--accent)}
.bullets{list-style:none;padding:0;margin:0;font-size:26px;display:flex;
  flex-direction:column;gap:16px;max-width:900px}
.bullet{padding-left:26px;position:relative}
.bullet:before{content:"";position:absolute;left:0;top:.62em;width:9px;height:9px;
  border-radius:2px;background:var(--accent)}
.code{background:#010409;border:1px solid var(--line);border-radius:12px;padding:20px 24px;
  font-family:"Cascadia Code",Consolas,monospace;font-size:19px;position:relative}
.lang{position:absolute;top:8px;right:14px;font-size:12px;color:var(--muted)}
.cl{white-space:pre}
.out{margin-top:14px;border-left:3px solid var(--accent);padding-left:14px;color:var(--muted)}
.olbl{font-size:12px;text-transform:uppercase;letter-spacing:.1em}
.mermaid{background:transparent;display:flex;justify-content:center}
.why{flex:0 0 auto;font-size:13px;color:var(--muted);
  border-top:1px solid var(--line);padding-top:8px}
/* Two lines, scrolled to follow the spoken word. A full transcript would cover
   the visual it is meant to support. */
.caption{flex:0 0 auto;height:76px;overflow:hidden;font-size:23px;line-height:38px;
  position:relative}
.caption .w{opacity:.35;transition:opacity .2s}
.caption .w.spoken{opacity:1}
.caption .w.current{color:var(--accent);opacity:1}
"""

_JS = """
const CUES = window.__cues || [];
const KIND = window.__kind;
function els(id){return document.querySelectorAll('[id="'+id+'"]');}
function apply(c){
  const t = c.element==='*' ? document.querySelectorAll('.reveal') : els(c.element);
  t.forEach(e=>{
    if(c.action==='hide') e.classList.remove('on');
    else if(c.action==='highlight'){e.classList.add('on');e.classList.add('hl');}
    else e.classList.add('on');
  });
}
// A graph's line draws in rather than popping, so proportionality is watched
// emerging rather than presented finished.
function drawLine(pct){
  const p=document.getElementById('line'); if(!p) return;
  const L=p.getTotalLength();
  p.style.strokeDasharray=L; p.style.strokeDashoffset=L*(1-pct);
}
window.seek = function(ms){
  document.querySelectorAll('.reveal').forEach(e=>{e.classList.remove('on','hl');});
  CUES.filter(c=>c.at_ms<=ms).forEach(apply);
  if(KIND==='graph'){
    const cs=CUES.length?CUES:[{at_ms:0}];
    const span=Math.max(1,(cs[cs.length-1].at_ms||1)-(cs[0].at_ms||0));
    drawLine(Math.max(0,Math.min(1,(ms-(cs[0].at_ms||0))/span)));
  }
  const ws=document.querySelectorAll('.caption .w');
  let cur=null;
  ws.forEach(w=>{
    const on = Number(w.dataset.at)<=ms;
    w.classList.toggle('spoken', on);
    w.classList.remove('current');
    if(on) cur=w;
  });
  if(cur){
    cur.classList.add('current');
    const box=document.querySelector('.caption');
    const want=cur.offsetTop-box.offsetTop-38;   // keep the spoken line centred
    if(Math.abs(box.scrollTop-want)>4) box.scrollTop=Math.max(0,want);
  }
  window.__seeked = ms;
};
window.play = function(){
  const t0=performance.now();
  (function tick(){
    const ms=performance.now()-t0;
    window.seek(ms);
    if(ms < (window.__duration||0)) requestAnimationFrame(tick);
  })();
};
if(KIND==='equation' && window.katex && window.__latex){
  katex.render(window.__latex, document.getElementById('eq'),
               {throwOnError:false, displayMode:true});
}
if(KIND==='diagram' && window.mermaid){
  mermaid.initialize({startOnLoad:true, theme:'dark',
                      themeVariables:{background:'#0d1117',primaryColor:'#161b22',
                      primaryTextColor:'#e6edf3',lineColor:'#58a6ff'}});
}
window.seek(0);
window.__ready = true;
"""


def render_slide(
    beat: Beat,
    timings: list[WordTiming] | None = None,
    *,
    title: str = "",
    with_caption: bool = True,
) -> str:
    timings = timings or []
    cues = cues_for(beat, timings)
    body = _RENDERERS[beat.visual.kind](beat.visual.payload or {})

    caption = ""
    if with_caption and timings:
        words = "".join(
            f'<span class="w" data-at="{t.start_ms}">{html.escape(t.word)} </span>'
            for t in timings
        )
        caption = f'<div class="caption">{words}</div>'

    duration = (timings[-1].end_ms if timings else 0)
    head = f'<div class="kicker">{html.escape(title or beat.intent)}</div>' if title or beat.intent else ""
    reveal_class = "reveal"

    # Every animatable element carries .reveal so a cue can act on it.
    for marker in ('class="term"', 'class="bullet"', 'class="pt"', 'class="cl"',
                   'class="mermaid"', 'class="out"'):
        body = body.replace(marker, marker[:-1] + f' {reveal_class}"')
    if beat.visual.kind in {"equation", "diagram"}:
        body = body.replace('id="eq"', f'id="eq" class="{reveal_class}"')
        body = body.replace('id="diagram"', f'id="diagram" class="{reveal_class}"')

    return f"""<!doctype html>
<html lang="{html.escape(beat.language)}"><head><meta charset="utf-8">
<title>{html.escape(beat.id)}</title>
<link rel="stylesheet" href="{CDN_KATEX}/katex.min.css">
<style>{_CSS}</style></head>
<body><div class="slide" id="slide">
  {head}
  <div class="stage">{body}</div>
  <div class="why">{html.escape(beat.visual.reason)}</div>
  {caption}
</div>
<script src="{CDN_KATEX}/katex.min.js"></script>
<script src="{CDN_MERMAID}"></script>
<script>
window.__cues={json.dumps(cues)};
window.__kind={json.dumps(beat.visual.kind)};
window.__duration={duration};
</script>
<script>{_JS}</script>
</body></html>"""
