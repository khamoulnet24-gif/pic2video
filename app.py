import os, json, uuid, shutil, tempfile, subprocess, threading
from datetime import date
from pathlib import Path
from flask import Flask, request, render_template, send_file, jsonify, Response
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

from seo import BASE_URL, SITE_NAME, OG_IMAGE, LANDINGS, software_app_jsonld, faq_jsonld, article_jsonld

load_dotenv()
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024

PRESETS = {
    "16:9": {"720": (1280, 720),  "1080": (1920, 1080), "4K": (3840, 2160)},
    "9:16": {"720": (720, 1280),  "1080": (1080, 1920), "4K": (2160, 3840)},
    "1:1":  {"720": (720, 720),   "1080": (1080, 1080), "4K": (2160, 2160)},
    "4:5":  {"720": (864, 1080),  "1080": (1080, 1350), "4K": (2160, 2700)},
}
WATERMARK_ENABLED = os.getenv("WATERMARK_ENABLED", "true") == "true"
WATERMARK_TEXT    = os.getenv("WATERMARK_TEXT", "pics2video")
WATERMARK_OPACITY = float(os.getenv("WATERMARK_OPACITY", "0.5"))
OVERLAP = 0.4
FPS = 30

BLOG_FILE = Path(__file__).parent / "blog.json"
JOBS = {}
JOBS_LOCK = threading.Lock()

# Détection désactivée pour éviter le crash OpenCV
def detect_focus(path):
    return None

def audio_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path], capture_output=True, text=True)
    return float(json.loads(r.stdout)["format"]["duration"])

def compute_crop(path, W, H):
    iw, ih = Image.open(path).size
    tr = W / H
    ir = iw / ih
    focus = detect_focus(path)
    BW, BH = W * 2, H * 2
    if ir > tr:
        bh = BH; bw = int(iw * bh / ih)
    else:
        bw = BW; bh = int(ih * bw / iw)
    cx, cy = (focus[0] * bw / iw, focus[1] * bh / ih) if focus else (bw / 2, bh / 2)
    x = int(max(0, min(cx - BW / 2, bw - BW)))
    y = int(max(0, min(cy - BH / 2, bh - BH)))
    return bw, bh, x, y, BW, BH

def make_watermark_png(W, H, ratio, out_path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fs = max(20, int(W * 0.03))
    try: font = ImageFont.truetype("arial.ttf", fs)
    except: font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    m = int(W * 0.025)
    x, y = (W - tw - m, m) if ratio in ("9:16", "4:5") else (W - tw - m, H - th - m)
    alpha = int(255 * WATERMARK_OPACITY)
    for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1),(0,1),(0,-1),(1,0),(-1,0)]:
        draw.text((x+dx, y+dy), WATERMARK_TEXT, font=font, fill=(0, 0, 0, alpha))
    draw.text((x, y), WATERMARK_TEXT, font=font, fill=(255, 255, 255, alpha))
    img.save(out_path, "PNG")

def build_cmd(photo_paths, audio_path, W, H, ratio, quality, out_path, wm_path):
    n = len(photo_paths)
    dur_audio = audio_duration(audio_path)
    per_photo = (dur_audio + OVERLAP * (n - 1)) / n
    overlap = min(OVERLAP, per_photo / 2)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1"]
    filter_parts = []
    input_idx = 0

    for i, p in enumerate(photo_paths):
        cmd.extend(["-loop", "1", "-t", f"{per_photo:.3f}", "-i", p])
        bw, bh, cx, cy, cw, ch = compute_crop(p, W, H)
        filter_parts.append(f"[{i}:v]scale={bw}:{bh},crop={cw}:{ch}:{cx}:{cy},zoompan=z='min(zoom+0.0006,1.04)':d={int(per_photo*FPS)}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v{i}]")
        input_idx += 1

    audio_idx = input_idx
    cmd.extend(["-i", audio_path]); input_idx += 1

    if WATERMARK_ENABLED:
        wm_idx = input_idx
        cmd.extend(["-i", wm_path]); input_idx += 1

    if n == 1:
        last = "v0"
    else:
        current = "v0"
        for i in range(1, n):
            offset = i * (per_photo - overlap)
            nxt = f"vx{i}"
            filter_parts.append(f"[{current}][v{i}]xfade=transition=fade:duration={overlap:.3f}:offset={offset:.3f}[{nxt}]")
            current = nxt
        last = current

    if WATERMARK_ENABLED:
        filter_parts.append(f"[{last}][{wm_idx}:v]overlay=0:0[vout]")
        vmap = "[vout]"
    else:
        vmap = f"[{last}]"

    cmd.extend(["-filter_complex", ";".join(filter_parts)])
    cmd.extend(["-map", vmap, "-map", f"{audio_idx}:a"])
    
    crf = {"720": "24", "1080": "22", "4K": "20"}[quality]
    cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", crf])
    cmd.extend(["-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", out_path])
    return cmd, dur_audio

def run_job(job_id, cmd, dur_audio, tmpdir):
    def update(**kw):
        with JOBS_LOCK: JOBS[job_id].update(kw)
    update(status="running", progress=0)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        for line in proc.stdout:
            if line.strip().startswith("out_time_us="):
                try:
                    us = int(line.strip().split("=")[1])
                    pct = min(99, int((us / 1_000_000) / dur_audio * 100))
                    update(progress=pct)
                except: pass
        proc.wait()
        if proc.returncode == 0: update(status="done", progress=100)
        else: update(status="error", error="ffmpeg a échoué")
    except Exception as e:
        update(status="error", error=str(e))

def load_blog():
    if not BLOG_FILE.exists(): return {}
    with open(BLOG_FILE, encoding="utf-8") as f: all_articles = json.load(f)
    today = date.today()
    return {s: a for s, a in all_articles.items() if a.get("status") != "draft" and date.fromisoformat(a.get("published", "2000-01-01")) <= today}

def render_page(template, **ctx):
    ctx.setdefault("site_name", SITE_NAME); ctx.setdefault("og_image", OG_IMAGE)
    ctx.setdefault("jsonld", json.dumps(ctx.pop("jsonld_data", software_app_jsonld()), ensure_ascii=False))
    return render_template(template, **ctx)

@app.route("/")
def index():
    return render_page("index.html", title=f"{SITE_NAME} - Créer une vidéo", meta_description="Transformez vos photos et musique en vidéo.", canonical=BASE_URL + "/")

@app.route("/generate", methods=["POST"])
def generate():
    audio = request.files.get("audio"); photos = request.files.getlist("photos")
    if len(photos) > 20: return jsonify(error="Maximum 20 photos autorisées"), 400
    ratio = request.form.get("ratio", "16:9"); quality = request.form.get("quality", "1080")
    if not audio or not photos: return jsonify(error="Fichiers manquants"), 400

    W, H = PRESETS.get(ratio, PRESETS["16:9"]).get(quality, PRESETS["16:9"]["1080"])
    tmpdir = tempfile.mkdtemp()
    audio_path = os.path.join(tmpdir, "audio"); audio.save(audio_path)
    photo_paths = []
    for i, p in enumerate(photos):
        ext = os.path.splitext(p.filename or "p.jpg")[1] or ".jpg"
        fp = os.path.join(tmpdir, f"p{i}{ext}"); p.save(fp); photo_paths.append(fp)

    wm_path = os.path.join(tmpdir, "wm.png")
    if WATERMARK_ENABLED: make_watermark_png(W, H, ratio, wm_path)
    out_path = os.path.join(tmpdir, "out.mp4")
    cmd, dur = build_cmd(photo_paths, audio_path, W, H, ratio, quality, out_path, wm_path)

    job_id = uuid.uuid4().hex
    with JOBS_LOCK: JOBS[job_id] = {"status": "queued", "progress": 0, "output": out_path, "tmpdir": tmpdir, "error": None}
    threading.Thread(target=run_job, args=(job_id, cmd, dur, tmpdir), daemon=True).start()
    return jsonify(job_id=job_id)

@app.route("/status/<job_id>")
def status(job_id):
    with JOBS_LOCK: j = JOBS.get(job_id)
    if not j: return jsonify(error="introuvable"), 404
    return jsonify(status=j["status"], progress=j["progress"], error=j["error"])

@app.route("/download/<job_id>")
def download(job_id):
    with JOBS_LOCK: j = JOBS.get(job_id)
    if not j or j["status"] != "done": return jsonify(error="pas prêt"), 404
    resp = send_file(j["output"], as_attachment=True, download_name="video.mp4")
    @resp.call_on_close
    def cleanup():
        shutil.rmtree(j["tmpdir"], ignore_errors=True)
        with JOBS_LOCK: JOBS.pop(job_id, None)
    return resp

@app.route("/<slug>")
def landing(slug):
    if slug not in LANDINGS: return render_page("404.html", title="404", meta_description="Page introuvable", canonical=BASE_URL), 404
    cfg = LANDINGS[slug]
    jsonld = faq_jsonld(cfg["faq"]) if cfg.get("faq") else software_app_jsonld()
    return render_page("landing.html", title=cfg["title"], meta_description=cfg["meta_description"], canonical=f"{BASE_URL}/{slug}", h1=cfg["h1"], intro=cfg["intro"], sections=cfg.get("sections", []), related=cfg.get("related", []), ratio=cfg["ratio"], quality=cfg["quality"], faq=cfg.get("faq", []), jsonld_data=jsonld)

@app.route("/blog")
def blog_index():
    articles = load_blog()
    return render_page("blog_index.html", title="Blog", meta_description="Guides vidéo", canonical=f"{BASE_URL}/blog", articles=[{"slug": s, **a} for s, a in articles.items()])

@app.route("/blog/<slug>")
def article(slug):
    articles = load_blog()
    if slug not in articles: return render_page("404.html", title="404", meta_description="Page introuvable", canonical=BASE_URL), 404
    a = articles[slug]
    return render_page("article.html", title=a["title"], meta_description=a["meta_description"], canonical=f"{BASE_URL}/blog/{slug}", h1=a["h1"], intro=a["intro"], sections=a["sections"], published=a["published"], reading_time=a["reading_time"], cta=a["cta"], cta_url=a["cta_url"], related_landings=a["related_landings"], jsonld_data=article_jsonld(a, f"{BASE_URL}/blog/{slug}"))

@app.route("/sitemap.xml")
def sitemap():
    blog = load_blog()
    urls = [f"{BASE_URL}/", f"{BASE_URL}/blog"] + [f"{BASE_URL}/{s}" for s in LANDINGS] + [f"{BASE_URL}/blog/{s}" for s in blog]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls: xml.append(f"<url><loc>{u}</loc><changefreq>weekly</changefreq></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n", mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True, port=5000)

