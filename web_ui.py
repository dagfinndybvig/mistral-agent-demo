import json
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ub_loop import AGENT_ID, AGENT_VERSION, LOG_FILE, QUERY, client, render

HOST = "127.0.0.1"
PORT = 8000

SECTION_RE = re.compile(r"^===== Update (.+?) =====$", re.MULTILINE)


def read_history():
    """Parse weather_update.log into [{stamp, text}], newest first."""
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return []
    parts = SECTION_RE.split(content)
    updates = [
        {"stamp": stamp.strip(), "text": body.strip()}
        for stamp, body in zip(parts[1::2], parts[2::2])
    ]
    updates.reverse()
    return updates


def run_update():
    """One agent query; appends to the log like ub_loop.one_cycle()."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = client.beta.conversations.start(
        agent_id=AGENT_ID,
        agent_version=AGENT_VERSION,
        inputs=[{"role": "user", "content": QUERY}],
    )
    text = render(response)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n===== Update {stamp} =====\n{text}\n")
    return {"stamp": stamp, "text": text}


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UB Weather Updates</title>
<style>
  body { font-family: system-ui, sans-serif; background: #14161a; color: #e6e6e6;
         max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
  h1 { font-size: 1.4rem; }
  button { background: #ff7000; color: #fff; border: none; padding: 0.6rem 1.2rem;
           border-radius: 6px; font-size: 1rem; cursor: pointer; }
  button:disabled { opacity: 0.5; cursor: wait; }
  .update { background: #1d2026; border: 1px solid #2c313a; border-radius: 8px;
            padding: 1rem; margin: 1rem 0; white-space: pre-wrap; }
  .stamp { color: #9aa3af; font-size: 0.85rem; margin-bottom: 0.5rem; }
  .status { color: #9aa3af; font-size: 0.9rem; min-height: 1.2em; }
  .empty { color: #9aa3af; }
</style>
</head>
<body>
<h1>UB &mdash; weather at NTNU Gloshaugen</h1>
<p><button id="update">Update now</button> <span id="status"></span></p>
<div id="updates"><p class="empty">Loading...</p></div>
<script>
async function refresh() {
  const res = await fetch('/api/updates');
  const updates = await res.json();
  const box = document.getElementById('updates');
  box.innerHTML = '';
  if (updates.length === 0) {
    box.innerHTML = '<p class="empty">No updates yet. Click "Update now".</p>';
    return;
  }
  for (const u of updates) {
    const div = document.createElement('div');
    div.className = 'update';
    const stamp = document.createElement('div');
    stamp.className = 'stamp';
    stamp.textContent = u.stamp;
    const text = document.createElement('div');
    text.textContent = u.text;
    div.appendChild(stamp);
    div.appendChild(text);
    box.appendChild(div);
  }
}
document.getElementById('update').addEventListener('click', async () => {
  const btn = document.getElementById('update');
  const status = document.getElementById('status');
  btn.disabled = true;
  status.textContent = 'Asking the agent...';
  try {
    const res = await fetch('/update', { method: 'POST' });
    if (!res.ok) {
      status.textContent = 'Error: ' + await res.text();
    } else {
      status.textContent = 'Done.';
      await refresh();
    }
  } catch (e) {
    status.textContent = 'Error: ' + e;
  } finally {
    btn.disabled = false;
  }
});
refresh();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/updates":
            self._send(200, json.dumps(read_history()), "application/json")
        elif self.path == "/":
            self._send(200, PAGE, "text/html")
        else:
            self._send(404, "Not found", "text/plain")

    def do_POST(self):
        if self.path == "/update":
            try:
                run_update()
                self._send(200, "ok", "text/plain")
            except Exception as e:
                self._send(500, f"{type(e).__name__}: {e}", "text/plain")
        else:
            self._send(404, "Not found", "text/plain")


def main():
    print(f"Serving on http://{HOST}:{PORT} (Ctrl+C to stop)")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
