from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SET_PLANNER = Path('/Users/antonbiletskiy-volokh/Downloads/Projects/SET/scripts/plan_config_apply.py')


def _path(env_name: str, default: Path) -> Path:
    value = os.environ.get(env_name, '').strip()
    return Path(value) if value else default


def get_planner_path() -> Path:
    return _path('SET_PLANNER_SCRIPT', DEFAULT_SET_PLANNER)


def get_snapshot_path() -> Path:
    return _path('LAB_PLANNING_SNAPSHOT_PATH', LAB_ROOT / 'docs' / 'assets' / 'planning-snapshot.json')


def get_page_path() -> Path:
    return _path('LAB_PLANNING_PAGE_PATH', LAB_ROOT / 'docs' / 'planning' / 'index.html')


def run_planner() -> dict[str, object]:
    planner = get_planner_path()
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            ['python3', str(planner), '--all', '--export-dir', tmpdir, '--format', 'json'],
            check=True,
            capture_output=True,
            text=True,
        )
        batch_summary = json.loads((Path(tmpdir) / 'batch-summary.json').read_text())
        repos = []
        for repo_entry in batch_summary.get('repos', []):
            repo = repo_entry['repo']
            repo_dir = Path(tmpdir) / repo.replace('/', '-')
            plan = json.loads((repo_dir / 'plan.json').read_text())
            repos.append(
                {
                    **repo_entry,
                    'plan': plan,
                    'files': [path.name for path in sorted(repo_dir.iterdir())],
                }
            )
        return {
            'version': 1,
            'source': 'SET planning snapshot',
            'planner': str(planner),
            'repo_count': len(repos),
            'repos': repos,
        }


def sort_key(entry: dict[str, object]) -> tuple[int, int, str]:
    priority_order = {'high': 0, 'medium': 1, 'normal': 2}
    status_order = {'ready-for-review': 0, 'needs-wiring': 1}
    return (
        priority_order.get(str(entry.get('priority_hint')), 9),
        status_order.get(str(entry.get('status_hint')), 9),
        str(entry.get('repo')),
    )


def build_page(snapshot: dict[str, object]) -> str:
    cards = []
    repos = sorted(snapshot.get('repos', []), key=sort_key)
    for index, entry in enumerate(repos, start=1):
        plan = entry['plan']
        workflow = plan['proposed_changes'][0]['workflow']
        gh_pr = plan['review_payload']['gh_pr_create']
        apply_sim = plan['review_payload']['apply_simulation']
        first_step = apply_sim['manual_steps'][0] if apply_sim.get('manual_steps') else 'n/a'
        unmapped = plan.get('unmapped', [])
        unmapped_html = ''
        if unmapped:
            items = ''.join(f'<li>{item}</li>' for item in unmapped)
            unmapped_html = f'<div class="small-note">Unmapped fields:</div><ul class="bullet-list">{items}</ul>'
        cards.append(
            f'''<section class="page-panel">
            <h2>{index}. {entry['repo']}</h2>
            <p class="small-note">Status: {entry['status_hint']} | Priority: {entry['priority_hint']}</p>
            <ul class="bullet-list">
              <li>Workflow preset: {workflow['with'].get('workflow_preset', 'none')}</li>
              <li>Target workflow: {entry['target_workflow']}</li>
              <li>Suggested branch: {gh_pr['head']}</li>
              <li>Suggested title: {gh_pr['title']}</li>
              <li>Next manual step: {first_step}</li>
            </ul>
            {unmapped_html}
            <div class="link-grid"><a class="button" href="../repos/index.html">Repo cards</a><a class="button-secondary" href="../registry/index.html">Registry</a><a class="button-secondary" href="../status/index.html">Status</a><a class="button-secondary" href="../assets/planning-snapshot.json">JSON snapshot</a></div>
          </section>'''
        )
    cards_html = '\n'.join(cards)
    return f'''<!doctype html>
<html lang="en" data-style="ascii" data-ascii-mode="light">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Planning Snapshot | ABVX Lab</title>
    <meta name="description" content="Read-only planning queue for SET config-apply review across registered repos." />
    <link rel="canonical" href="https://lab.abvx.xyz/planning/" />
    <meta property="og:title" content="Planning Snapshot | ABVX Lab" />
    <meta property="og:description" content="Read-only planning queue for SET config-apply review across registered repos." />
    <meta property="og:url" content="https://lab.abvx.xyz/planning/" />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="https://lab.abvx.xyz/assets/og.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <link rel="stylesheet" href="../assets/asciitheme.css?v20260319d" />
    <link rel="stylesheet" href="../assets/styles.css?v20260320a" />
    <script type="application/ld+json">{{"@context":"https://schema.org","@type":"CollectionPage","name":"Planning Snapshot","url":"https://lab.abvx.xyz/planning/","description":"Read-only planning queue for SET config-apply review across registered repos."}}</script>
  </head>
  <body>
    <div class="site-shell">
      <div class="container page-layout">
        <header class="topbar">
          <div class="topbar-left"><a class="brand" href="../index.html"><img class="brand-logo" src="../assets/logo.png?v20260319d" alt="ABVX Lab logo" /><span class="brand-text">ABVX Lab</span></a></div>
          <nav class="topbar-nav" aria-label="Primary"><a href="../index.html">Home</a><a href="../index.html#tools">Tools</a><a href="https://github.com/markoblogo">GitHub profile</a></nav>
          <div class="topbar-right"><div class="header-controls"></div></div>
        </header>
        <main class="page-layout">
          <section class="hero-panel">
            <span class="kicker">ABVX control plane</span>
            <h1>What to review next</h1>
            <p class="lead">Read-only planning queue generated from SET config-apply plans across registered repos.</p>
            <p class="small-note">This is an operator view only: priority/status hints, suggested branches, and manual next steps. No repo mutation.</p>
            <div class="link-grid"><a class="button" href="../repos/index.html">Repo cards</a><a class="button-secondary" href="../registry/index.html">Registry</a><a class="button-secondary" href="../status/index.html">Status</a><a class="button-secondary" href="../assets/planning-snapshot.json">JSON snapshot</a></div>
          </section>
          {cards_html}
        </main>
        <footer class="footer footer--lab"><div class="footer-inner"><div class="footer-left"><div class="footer-title">ABVX Lab</div><div class="footer-note">Small, readable, static pages for ABVX developer tools.</div></div></div></footer>
      </div>
    </div>
    <script src="../assets/ascii-theme.js?v20260319d"></script>
    <script>
      AsciiTheme.initAsciiTheme({{ base: true, managedMode: true, addThemeToggle: true, addStyleToggle: false, mountSelector: '.header-controls' }});
    </script>
  </body>
</html>
'''


def main() -> int:
    snapshot = run_planner()
    output_json = get_snapshot_path()
    output_html = get_page_path()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(snapshot, indent=2) + '\n')
    output_html.write_text(build_page(snapshot))
    print(f'Wrote {output_json}')
    print(f'Wrote {output_html}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
