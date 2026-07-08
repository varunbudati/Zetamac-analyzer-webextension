#!/usr/bin/env python3
"""
Zetamac Progression Analyzer
Parses Zetamac Obsidian session markdown files and compiles progress statistics.
Outputs a console summary and generates an interactive HTML dashboard.
"""

import os
import sys
import json
import re
import webbrowser

DEFAULT_VAULT_PATH = r"C:\Users\varun\OneDrive\Documents\Obsidian\Me\DailyLogs\Zetamac"
OUTPUT_HTML_NAME = "zetamac_progression.html"

# Reconfigure standard streams to use UTF-8 on Windows to avoid UnicodeEncodeErrors with emojis and math symbols
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def parse_markdown_file(filepath):
    """Parses the YAML frontmatter of a Zetamac markdown file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        parts = content.split('---')
        if len(parts) < 3:
            return None
        
        yaml_text = parts[1]
        data = {}
        for line in yaml_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or ':' not in line:
                continue
            
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip().strip('"\'[]')
            
            try:
                if '.' in val:
                    data[key] = float(val)
                else:
                    data[key] = int(val)
            except ValueError:
                data[key] = val
        
        if 'score' not in data or 'date' not in data:
            return None
            
        return data
    except Exception as e:
        sys.stderr.write(f"Error parsing {filepath}: {str(e)}\n")
        return None

def parse_session_problems(filepath):
    """Parses the 'Full Log' table in a markdown session file to extract individual problems."""
    problems = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if "## 📋 Full Log" not in content:
            return problems
            
        lines = content.split("## 📋 Full Log")[1].split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("##"):
                break
            
            # Match markdown table row like: | 1 | 14 × 7 | 98 | 3.5s |
            match = re.match(r'^\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([\d\.]+)s\s*\|', line)
            if match:
                problem_str = match.group(2).strip()
                time_sec = float(match.group(4).strip())
                
                op = None
                val1, val2 = None, None
                
                if '+' in problem_str:
                    parts = problem_str.split('+')
                    op = 'addition'
                elif '−' in problem_str or '-' in problem_str:
                    parts = problem_str.split('−') if '−' in problem_str else problem_str.split('-')
                    op = 'subtraction'
                elif '×' in problem_str or 'x' in problem_str or '*' in problem_str:
                    parts = problem_str.split('×') if '×' in problem_str else (problem_str.split('x') if 'x' in problem_str else problem_str.split('*'))
                    op = 'multiplication'
                elif '÷' in problem_str or '/' in problem_str:
                    parts = problem_str.split('÷') if '÷' in problem_str else problem_str.split('/')
                    op = 'division'
                    
                if op and len(parts) == 2:
                    try:
                        val1 = int(parts[0].strip())
                        val2 = int(parts[1].strip())
                        problems.append({
                            'op': op,
                            'val1': val1,
                            'val2': val2,
                            'time': time_sec
                        })
                    except ValueError:
                        pass
    except Exception as e:
        sys.stderr.write(f"Error parsing problems from {filepath}: {str(e)}\n")
    return problems

def scan_vault(vault_path):
    """Scans the vault folder for session files and returns a sorted list of data."""
    sessions = []
    if not os.path.exists(vault_path):
        print(f"[-] Error: Vault path does not exist: {vault_path}")
        return sessions
        
    print(f"[+] Scanning vault path: {vault_path}")
    for filename in os.listdir(vault_path):
        if filename.endswith('.md') and filename.startswith('Zetamac') and filename != 'Template.md':
            filepath = os.path.join(vault_path, filename)
            data = parse_markdown_file(filepath)
            if data:
                data['_filename'] = filename
                data['_filepath'] = filepath
                date_str = str(data.get('date', '')).replace('"', '').strip()
                time_str = str(data.get('time', '00:00')).replace('"', '').replace('-', ':').strip()
                data['datetime_display'] = f"{date_str} {time_str}"
                sessions.append(data)
                
    def get_timestamp(s):
        return s.get('datetime_display', '')
        
    sessions.sort(key=get_timestamp)
    return sessions

def compile_recommendations(sessions):
    """Compiles specific numbers to practice for multiplication and division."""
    all_problems = []
    for s in sessions:
        filepath = s.get('_filepath')
        if filepath and os.path.exists(filepath):
            all_problems.extend(parse_session_problems(filepath))
            
    if not all_problems:
        return {'multiplication': [], 'division': []}
        
    mult_stats = {}
    div_stats = {}
    
    for p in all_problems:
        op = p['op']
        val1 = p['val1']
        val2 = p['val2']
        time_sec = p['time']
        
        if op == 'multiplication':
            for factor in [val1, val2]:
                if factor not in mult_stats:
                    mult_stats[factor] = []
                mult_stats[factor].append(time_sec)
        elif op == 'division':
            if val2 not in div_stats:
                div_stats[val2] = []
            div_stats[val2].append(time_sec)
            
    def get_averages(stats_dict):
        averages = []
        for num, times in stats_dict.items():
            averages.append({
                'number': num,
                'avg_time': sum(times) / len(times),
                'count': len(times)
            })
        return averages
        
    mult_all = get_averages(mult_stats)
    div_all = get_averages(div_stats)
    
    mult_filtered = [x for x in mult_all if x['count'] >= 2]
    div_filtered = [x for x in div_all if x['count'] >= 2]
    
    if not mult_filtered:
        mult_filtered = mult_all
    if not div_filtered:
        div_filtered = div_all
        
    mult_filtered.sort(key=lambda x: x['avg_time'], reverse=True)
    div_filtered.sort(key=lambda x: x['avg_time'], reverse=True)
    
    return {
        'multiplication': mult_filtered[:3],
        'division': div_filtered[:3]
    }

def print_terminal_summary(sessions, recommendations):
    """Prints a beautiful summary of progress to the console."""
    if not sessions:
        print("[-] No sessions found to summarize.")
        return
        
    total_games = len(sessions)
    scores = [s['score'] for s in sessions]
    avg_speeds = [s['avg_time_ms'] for s in sessions if 'avg_time_ms' in s]
    
    max_score = max(scores)
    max_score_idx = scores.index(max_score)
    pb_date = sessions[max_score_idx]['datetime_display']
    
    avg_score = sum(scores) / total_games
    avg_speed = (sum(avg_speeds) / len(avg_speeds)) / 1000 if avg_speeds else 0
    
    op_counts = {'addition': 0, 'subtraction': 0, 'multiplication': 0, 'division': 0}
    op_total_ms = {'addition': 0.0, 'subtraction': 0.0, 'multiplication': 0.0, 'division': 0.0}
    op_total_games = {'addition': 0, 'subtraction': 0, 'multiplication': 0, 'division': 0}
    
    for s in sessions:
        for op in op_counts.keys():
            count_key = f"{op}_count"
            avg_key = f"{op}_avg_ms"
            if count_key in s:
                op_counts[op] += s[count_key]
                if avg_key in s and s[count_key] > 0:
                    op_total_ms[op] += s[avg_key] * s[count_key]
                    op_total_games[op] += s[count_key]
                    
    op_speeds = {}
    for op in op_counts.keys():
        if op_total_games[op] > 0:
            op_speeds[op] = (op_total_ms[op] / op_total_games[op]) / 1000
        else:
            op_speeds[op] = 0.0

    print("\n" + "="*50)
    print("      🧠 ZETAMAC PROGRESSION SUMMARY 🧠")
    print("="*50)
    print(f"📊 Total Sessions Played:  {total_games}")
    print(f"🏆 Personal Best Score:   {max_score}  (Achieved {pb_date})")
    print(f"📈 Average Score:         {avg_score:.1f}")
    print(f"⚡ Average Speed:         {avg_speed:.2f} seconds / problem")
    print("-"*50)
    print("🎯 OPERATION BREAKDOWN (ALL TIME)")
    print("-"*50)
    for op in ['addition', 'subtraction', 'multiplication', 'division']:
        symbol = {'addition': '➕', 'subtraction': '➖', 'multiplication': '✖️', 'division': '➗'}[op]
        name = op.capitalize().ljust(15)
        count = op_counts[op]
        speed = op_speeds[op]
        speed_str = f"{speed:.2f}s/prob" if speed > 0 else "N/A"
        print(f"{symbol} {name} | Solved: {str(count).ljust(5)} | Avg Speed: {speed_str}")
        
    # Print Actionable Recommendations in console
    mult_recs = recommendations.get('multiplication', [])
    div_recs = recommendations.get('division', [])
    
    if mult_recs or div_recs:
        print("-"*50)
        print("💡 RECOMMENDED NUMBERS TO PRACTICE (SLOWEST)")
        print("-"*50)
        if mult_recs:
            recs_str = ", ".join([f"{item['number']} ({item['avg_time']:.1f}s)" for item in mult_recs])
            print(f"✖️ Multiplication factors: {recs_str}")
        if div_recs:
            recs_str = ", ".join([f"{item['number']} ({item['avg_time']:.1f}s)" for item in div_recs])
            print(f"➗ Division divisors:      {recs_str}")
            
    print("-"*50)
    
    if total_games >= 2:
        half = min(5, total_games // 2)
        first_half_avg = sum(scores[:half]) / half
        last_half_avg = sum(scores[-half:]) / half
        diff = last_half_avg - first_half_avg
        direction = "📈 Improved by" if diff >= 0 else "📉 Decreased by"
        print(f"🔥 Recent Trend (Last {half} vs First {half} games):")
        print(f"   {direction} {abs(diff):.1f} points on average")
        
    print("="*50 + "\n")

def generate_html_dashboard(sessions, recommendations, output_path):
    """Generates a premium dark-themed HTML dashboard with interactive charts."""
    sessions_json = json.dumps(sessions)
    recommendations_json = json.dumps(recommendations)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Zetamac Mental Math Progression</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg-dark: #09090e;
      --bg-card: #12121e;
      --bg-card-hover: #171727;
      --border-color: #232338;
      --text-main: #f1f1f7;
      --text-muted: #8b8ba8;
      
      --color-primary: #8b5cf6;
      --color-secondary: #06b6d4;
      --color-success: #10b981;
      
      --color-addition: #a78bfa;
      --color-subtraction: #f43f5e;
      --color-multiplication: #3b82f6;
      --color-division: #fbbf24;
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: 'Inter', sans-serif;
      padding: 30px;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}

    /* ── Header ── */
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 30px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 20px;
    }}

    .title-area h1 {{
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(135deg, #a78bfa, #8b5cf6, #06b6d4);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 6px;
    }}

    .title-area p {{
      color: var(--text-muted);
      font-size: 14px;
    }}

    .filter-btn-group {{
      display: flex;
      gap: 10px;
      background: #181829;
      padding: 4px;
      border-radius: 10px;
      border: 1px solid var(--border-color);
    }}

    .filter-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 8px 16px;
      border-radius: 7px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .filter-btn.active, .filter-btn:hover {{
      background: var(--bg-card);
      color: var(--text-main);
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}

    /* ── KPI Grid ── */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }}

    .kpi-card {{
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 24px;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }}

    .kpi-card:hover {{
      transform: translateY(-2px);
      border-color: #3b3b5c;
    }}

    .kpi-title {{
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-muted);
      margin-bottom: 8px;
    }}

    .kpi-value {{
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 6px;
    }}

    .kpi-desc {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    /* ── Charts Grid ── */
    .charts-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 25px;
      margin-bottom: 35px;
    }}

    @media (max-width: 900px) {{
      .charts-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .chart-card {{
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 18px;
      padding: 24px;
      height: 380px;
      position: relative;
    }}

    .chart-card-title {{
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 20px;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .chart-container {{
      position: absolute;
      left: 20px;
      right: 20px;
      top: 60px;
      bottom: 20px;
    }}

    /* ── Table Card ── */
    .table-card {{
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 18px;
      padding: 24px;
      overflow: hidden;
    }}

    .table-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }}

    .table-title {{
      font-size: 16px;
      font-weight: 600;
    }}

    .search-input {{
      background: #181829;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 8px 14px;
      color: var(--text-main);
      font-size: 13px;
      outline: none;
      width: 240px;
      transition: border-color 0.2s;
    }}

    .search-input:focus {{
      border-color: var(--color-primary);
    }}

    .table-scroll {{
      overflow-x: auto;
      max-height: 400px;
      overflow-y: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 14px;
    }}

    th {{
      color: var(--text-muted);
      font-weight: 600;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      background: var(--bg-card);
      z-index: 10;
    }}

    td {{
      padding: 14px 16px;
      border-bottom: 1px solid rgba(35, 35, 56, 0.4);
      color: #d4d4e2;
    }}

    tr:hover td {{
      background-color: var(--bg-card-hover);
    }}

    .tag {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
    }}

    .tag-add {{ background: rgba(167, 139, 250, 0.15); color: var(--color-addition); }}
    .tag-sub {{ background: rgba(244, 63, 94, 0.15); color: var(--color-subtraction); }}
    .tag-mul {{ background: rgba(59, 130, 246, 0.15); color: var(--color-multiplication); }}
    .tag-div {{ background: rgba(251, 191, 36, 0.15); color: var(--color-division); }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="title-area">
        <h1>🧠 Zetamac Analyzer</h1>
        <p>Interactive dashboard tracking mental math capability and speed progression</p>
      </div>
      <div class="filter-btn-group">
        <button class="filter-btn active" onclick="setFilter('all')">All Time</button>
        <button class="filter-btn" onclick="setFilter('30')">Last 30 Games</button>
        <button class="filter-btn" onclick="setFilter('10')">Last 10 Games</button>
      </div>
    </header>

    <!-- Actionable Recommendations Card -->
    <div class="kpi-grid" id="recommendations-container" style="display: none; grid-template-columns: 1fr; margin-bottom: 25px;">
      <div class="kpi-card" style="border-color: rgba(251, 191, 36, 0.3); background: linear-gradient(135deg, rgba(251, 191, 36, 0.04), rgba(244, 63, 94, 0.04)); padding: 20px 24px;">
        <div class="kpi-title" style="color: #fbbf24; font-size: 13px; display: flex; align-items: center; gap: 8px; margin-bottom: 0;">
          💡 Areas to Improve (Specific Numbers to Practice)
        </div>
        <div class="recommendations-list" id="recommendations-list" style="margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px;">
          <!-- Populated dynamically -->
        </div>
      </div>
    </div>

    <!-- KPI Summary Card Row -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Total Games</div>
        <div class="kpi-value" id="kpi-total">0</div>
        <div class="kpi-desc">Total completed runs logged</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Personal Best</div>
        <div class="kpi-value" style="color: var(--color-success);" id="kpi-pb">0</div>
        <div class="kpi-desc" id="kpi-pb-date">--</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Avg Score</div>
        <div class="kpi-value" id="kpi-avg-score">0</div>
        <div class="kpi-desc">Average questions per session</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Avg Solve Speed</div>
        <div class="kpi-value" id="kpi-avg-speed">0.00s</div>
        <div class="kpi-desc">Mean solve time per question</div>
      </div>
    </div>

    <!-- Charts Layout Grid -->
    <div class="charts-grid">
      <div class="chart-card">
        <div class="chart-card-title">📈 Score Progression Trend</div>
        <div class="chart-container">
          <canvas id="scoreChart"></canvas>
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-card-title">⚡ Average Speed Trend (Seconds per Answer)</div>
        <div class="chart-container">
          <canvas id="speedChart"></canvas>
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-card-title">📊 Operation Composition (Total Questions Solved)</div>
        <div class="chart-container">
          <canvas id="compositionChart"></canvas>
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-card-title">⏱️ Average Speed by Operation</div>
        <div class="chart-container">
          <canvas id="opSpeedChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Table Logs -->
    <div class="table-card">
      <div class="table-header">
        <div class="table-title">📋 Run History Log</div>
        <input type="text" class="search-input" id="tableSearch" placeholder="Search by date or score..." oninput="filterTable()">
      </div>
      <div class="table-scroll">
        <table id="historyTable">
          <thead>
            <tr>
              <th>Date/Time</th>
              <th>Score</th>
              <th>Avg Speed</th>
              <th>➕ Addition</th>
              <th>➖ Subtraction</th>
              <th>✖️ Multiplication</th>
              <th>➗ Division</th>
            </tr>
          </thead>
          <tbody id="tableBody">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const allSessions = {sessions_json};
    let activeSessions = [...allSessions];

    let scoreChart, speedChart, compositionChart, opSpeedChart;

    function msToSec(ms) {{
      return (ms / 1000).toFixed(2);
    }}

    function calculateKPIs() {{
      if (activeSessions.length === 0) return;
      
      document.getElementById('kpi-total').textContent = activeSessions.length;
      
      const scores = activeSessions.map(s => s.score);
      const maxScore = Math.max(...scores);
      document.getElementById('kpi-pb').textContent = maxScore;
      
      const pbSession = activeSessions[scores.indexOf(maxScore)];
      document.getElementById('kpi-pb-date').textContent = "Set on " + pbSession.datetime_display;
      
      const avgScore = scores.reduce((a, b) => a + b, 0) / activeSessions.length;
      document.getElementById('kpi-avg-score').textContent = avgScore.toFixed(1);
      
      const speeds = activeSessions.map(s => s.avg_time_ms).filter(Boolean);
      const avgSpeed = speeds.length > 0 ? (speeds.reduce((a, b) => a + b, 0) / speeds.length) / 1000 : 0;
      document.getElementById('kpi-avg-speed').textContent = avgSpeed.toFixed(2) + 's';
    }}

    function renderRecommendations() {{
      const recs = {recommendations_json};
      const recList = document.getElementById('recommendations-list');
      const recContainer = document.getElementById('recommendations-container');
      
      recList.innerHTML = '';
      let hasRecs = false;
      
      if (recs.multiplication && recs.multiplication.length > 0) {{
        hasRecs = true;
        recs.multiplication.forEach(item => {{
          const div = document.createElement('div');
          div.style.cssText = "display: flex; align-items: center; justify-content: space-between; font-size: 13.5px; padding: 12px 16px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.04);";
          div.innerHTML = `
            <span>✖️ Slow at multiplying by <strong style="color: var(--color-addition); font-size: 15px;">${{item.number}}</strong></span>
            <span style="color: var(--text-muted);">Avg speed: <strong style="color: var(--color-subtraction); font-weight:600;">${{item.avg_time.toFixed(1)}}s</strong> over ${{item.count}} questions</span>
          `;
          recList.appendChild(div);
        }});
      }}
      
      if (recs.division && recs.division.length > 0) {{
        hasRecs = true;
        recs.division.forEach(item => {{
          const div = document.createElement('div');
          div.style.cssText = "display: flex; align-items: center; justify-content: space-between; font-size: 13.5px; padding: 12px 16px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.04);";
          div.innerHTML = `
            <span>➗ Slow at dividing by <strong style="color: var(--color-division); font-size: 15px;">${{item.number}}</strong></span>
            <span style="color: var(--text-muted);">Avg speed: <strong style="color: var(--color-subtraction); font-weight:600;">${{item.avg_time.toFixed(1)}}s</strong> over ${{item.count}} questions</span>
          `;
          recList.appendChild(div);
        }});
      }}
      
      if (hasRecs) {{
        recContainer.style.display = 'grid';
      }} else {{
        recContainer.style.display = 'none';
      }}
    }}

    function renderTable() {{
      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = '';
      
      const sortedTableSessions = [...activeSessions].reverse();
      
      sortedTableSessions.forEach(s => {{
        const row = document.createElement('tr');
        
        const addCount = s.addition_count || 0;
        const addSpeed = s.addition_avg_ms ? msToSec(s.addition_avg_ms) + 's' : '-';
        const subCount = s.subtraction_count || 0;
        const subSpeed = s.subtraction_avg_ms ? msToSec(s.subtraction_avg_ms) + 's' : '-';
        const mulCount = s.multiplication_count || 0;
        const mulSpeed = s.multiplication_avg_ms ? msToSec(s.multiplication_avg_ms) + 's' : '-';
        const divCount = s.division_count || 0;
        const divSpeed = s.division_avg_ms ? msToSec(s.division_avg_ms) + 's' : '-';
        
        row.innerHTML = `
          <td>${{s.datetime_display}}</td>
          <td style="font-weight: 700; color: #a78bfa;">${{s.score}}</td>
          <td>${{s.avg_time_ms ? msToSec(s.avg_time_ms) + 's' : '-'}}</td>
          <td>${{addCount}} <span class="tag tag-add">${{addSpeed}}</span></td>
          <td>${{subCount}} <span class="tag tag-sub">${{subSpeed}}</span></td>
          <td>${{mulCount}} <span class="tag tag-mul">${{mulSpeed}}</span></td>
          <td>${{divCount}} <span class="tag tag-div">${{divSpeed}}</span></td>
        `;
        tbody.appendChild(row);
      }});
    }}

    function filterTable() {{
      const query = document.getElementById('tableSearch').value.toLowerCase();
      const rows = document.getElementById('tableBody').getElementsByTagName('tr');
      
      for (let i = 0; i < rows.length; i++) {{
        const cells = rows[i].getElementsByTagName('td');
        let match = false;
        for (let j = 0; j < cells.length; j++) {{
          if (cells[j].textContent.toLowerCase().includes(query)) {{
            match = true;
            break;
          }}
        }}
        rows[i].style.display = match ? '' : 'none';
      }}
    }}

    function renderCharts() {{
      const labels = activeSessions.map((s, idx) => `G${{idx + 1}} (${{s.datetime_display.split(' ')[0]}})`);
      
      const scores = activeSessions.map(s => s.score);
      const scoreCtx = document.getElementById('scoreChart').getContext('2d');
      if (scoreChart) scoreChart.destroy();
      scoreChart = new Chart(scoreCtx, {{
        type: 'line',
        data: {{
          labels: labels,
          datasets: [{{
            label: 'Score',
            data: scores,
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: '#8b5cf6',
            pointRadius: 4,
            pointHoverRadius: 6
          }}]
        }},
        options: getChartOptions()
      }});

      const speeds = activeSessions.map(s => s.avg_time_ms ? s.avg_time_ms / 1000 : 0);
      const speedCtx = document.getElementById('speedChart').getContext('2d');
      if (speedChart) speedChart.destroy();
      speedChart = new Chart(speedCtx, {{
        type: 'line',
        data: {{
          labels: labels,
          datasets: [{{
            label: 'Average Speed (s)',
            data: speeds,
            borderColor: '#06b6d4',
            backgroundColor: 'rgba(6, 182, 212, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: '#06b6d4',
            pointRadius: 4,
            pointHoverRadius: 6
          }}]
        }},
        options: getChartOptions()
      }});

      const compositionCtx = document.getElementById('compositionChart').getContext('2d');
      if (compositionChart) compositionChart.destroy();
      compositionChart = new Chart(compositionCtx, {{
        type: 'bar',
        data: {{
          labels: labels,
          datasets: [
            {{
              label: '➕ Addition',
              data: activeSessions.map(s => s.addition_count || 0),
              backgroundColor: '#a78bfa'
            }},
            {{
              label: '➖ Subtraction',
              data: activeSessions.map(s => s.subtraction_count || 0),
              backgroundColor: '#f43f5e'
            }},
            {{
              label: '✖️ Multiplication',
              data: activeSessions.map(s => s.multiplication_count || 0),
              backgroundColor: '#3b82f6'
            }},
            {{
              label: '➗ Division',
              data: activeSessions.map(s => s.division_count || 0),
              backgroundColor: '#fbbf24'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{
              stacked: true,
              grid: {{ color: 'rgba(255,255,255,0.05)' }},
              ticks: {{ color: '#8b8ba8', font: {{ family: 'Inter', size: 10 }} }}
            }},
            y: {{
              stacked: true,
              grid: {{ color: 'rgba(255,255,255,0.05)' }},
              ticks: {{ color: '#8b8ba8' }}
            }}
          }},
          plugins: {{
            legend: {{
              position: 'top',
              labels: {{ color: '#f1f1f7', font: {{ family: 'Inter', weight: 500 }} }}
            }}
          }}
        }}
      }});

      const opSpeedCtx = document.getElementById('opSpeedChart').getContext('2d');
      if (opSpeedChart) opSpeedChart.destroy();
      opSpeedChart = new Chart(opSpeedCtx, {{
        type: 'line',
        data: {{
          labels: labels,
          datasets: [
            {{
              label: '➕ Add Speed',
              data: activeSessions.map(s => s.addition_avg_ms ? s.addition_avg_ms / 1000 : null),
              borderColor: '#a78bfa',
              borderWidth: 2,
              pointRadius: 2,
              tension: 0.2,
              fill: false
            }},
            {{
              label: '➖ Sub Speed',
              data: activeSessions.map(s => s.subtraction_avg_ms ? s.subtraction_avg_ms / 1000 : null),
              borderColor: '#f43f5e',
              borderWidth: 2,
              pointRadius: 2,
              tension: 0.2,
              fill: false
            }},
            {{
              label: '✖️ Mul Speed',
              data: activeSessions.map(s => s.multiplication_avg_ms ? s.multiplication_avg_ms / 1000 : null),
              borderColor: '#3b82f6',
              borderWidth: 2,
              pointRadius: 2,
              tension: 0.2,
              fill: false
            }},
            {{
              label: '➗ Div Speed',
              data: activeSessions.map(s => s.division_avg_ms ? s.division_avg_ms / 1000 : null),
              borderColor: '#fbbf24',
              borderWidth: 2,
              pointRadius: 2,
              tension: 0.2,
              fill: false
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{
              grid: {{ color: 'rgba(255,255,255,0.05)' }},
              ticks: {{ color: '#8b8ba8', font: {{ family: 'Inter', size: 10 }} }}
            }},
            y: {{
              title: {{ display: true, text: 'Seconds', color: '#8b8ba8' }},
              grid: {{ color: 'rgba(255,255,255,0.05)' }},
              ticks: {{ color: '#8b8ba8' }}
            }}
          }},
          plugins: {{
            legend: {{
              position: 'top',
              labels: {{ color: '#f1f1f7', font: {{ family: 'Inter', weight: 500 }} }}
            }}
          }}
        }}
      }});
    }}

    function getChartOptions() {{
      return {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{
            grid: {{ color: 'rgba(255,255,255,0.05)' }},
            ticks: {{ color: '#8b8ba8', font: {{ family: 'Inter', size: 10 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(255,255,255,0.05)' }},
            ticks: {{ color: '#8b8ba8' }}
          }}
        }},
        plugins: {{
          legend: {{ display: false }}
        }}
      }};
    }}

    function setFilter(limit) {{
      const buttons = document.querySelectorAll('.filter-btn');
      buttons.forEach(btn => btn.classList.remove('active'));
      
      event.target.classList.add('active');
      
      if (limit === 'all') {{
        activeSessions = [...allSessions];
      }} else {{
        const count = parseInt(limit, 10);
        activeSessions = allSessions.slice(-count);
      }}
      
      calculateKPIs();
      renderCharts();
      renderTable();
    }}

    window.onload = function() {{
      calculateKPIs();
      renderRecommendations();
      renderCharts();
      renderTable();
    }};
  </script>
</body>
</html>
"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        print(f"[+] Interactive dashboard generated: {output_path}")
        return True
    except Exception as e:
        sys.stderr.write(f"[-] Error generating dashboard file: {str(e)}\n")
        return False

def main():
    # Allow passing target folder as argument, default to default config path
    vault_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VAULT_PATH
    
    if not os.path.exists(vault_path):
        print(f"[-] Error: Specified directory does not exist: {vault_path}")
        print("Usage: python analyze.py [vault_path]")
        sys.exit(1)
        
    sessions = scan_vault(vault_path)
    
    if not sessions:
        print("[-] No Zetamac session log files found.")
        print(f"Make sure you have daily logs in: {vault_path}")
        sys.exit(0)
        
    # Compile recommendations
    recommendations = compile_recommendations(sessions)
        
    # Render terminal report
    print_terminal_summary(sessions, recommendations)
    
    # Generate dashboard in 'analysis' subfolder inside vault_path
    analysis_dir = os.path.join(vault_path, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    dashboard_path = os.path.join(analysis_dir, OUTPUT_HTML_NAME)
    
    if generate_html_dashboard(sessions, recommendations, dashboard_path):
        try:
            print("[+] Opening dashboard in browser...")
            webbrowser.open(f"file:///{os.path.abspath(dashboard_path)}")
        except Exception:
            print(f"[*] Double-click '{OUTPUT_HTML_NAME}' to view the charts in your browser.")

if __name__ == '__main__':
    main()
