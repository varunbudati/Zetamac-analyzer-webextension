#🧠 Zetamac → Obsidian Chrome Extension & Analyzer

Automatically export your [Zetamac](https://arithmetic.zetamac.com/) mental math practice sessions directly into your **Obsidian Vault** as detailed markdown notes, and visualize your progression with an interactive local dashboard.

---

## ✨ Features

- 📂 **Direct Obsidian Vault Export:** Automatically writes game logs directly to your Obsidian vault (using standard Chrome Native Messaging powered by a Python helper script). No manual downloads or copy-pasting required.
- 📋 **Granular Markdown Session Logs:** Each game session generates an Obsidian-ready note containing:
  - YAML frontmatter with metadata (`tags`, `score`, `duration`, `avg_time_ms`, etc.).
  - A summary table showing counts and solve speeds for each operator (➕, ➖, ✖️, ➗).
  - A **Slowest Problems** table showing where you spent the most time.
  - A full chronological logs table.
  - Actionable recommendations based on the carry-over patterns of that specific run.
- 📊 **Interactive local Progression Dashboard:** Analyze your performance over time with a dark-themed visual dashboard.
  - Generates line charts for **Score Trend** and **Average Speed Progression** using Chart.js.
  - Visualizes your **Operation Distribution** (stacked bar charts) and solve speed trends by operator.
  - Includes a searchable, sortable run history log table.
- 💡 **Actionable Practice Targets:** The analyzer parses your individual solved questions across all games to compute number-specific speeds. It highlights the top 3 specific factors (e.g., multiplying by 17) and divisors (e.g., dividing by 12) you struggle with most.

---

## 🛠️ Installation & Setup

### 1. Load the Extension in Chrome
1. Clone this repository to your machine.
2. Open Google Chrome and navigate to `chrome://extensions/`.
3. Enable **Developer mode** in the top right.
4. Click **Load unpacked** in the top left and select the `extension/` directory of this repository.
5. Copy the **Extension ID** displayed on the extension's card (e.g., `faacnaopdjapflcalnnlgheodnggkcci`).

### 2. Register the Native Messaging Host
To allow Chrome to securely write files directly to your vault, register the helper host:
1. Open PowerShell in the `native-host/` folder.
2. Run the installer script with your extension ID:
   ```powershell
   .\install.ps1 -ExtensionId "YOUR_EXTENSION_ID"
   ```
3. Restart Chrome (`chrome://restart`) so the browser picks up the new registry key permissions.

### 3. Configure settings
1. Click the **Zetamac → Obsidian** extension icon in your Chrome toolbar.
2. In the **Obsidian Vault Folder** field, enter the absolute path to your target folder (e.g. `C:\Users\you\Obsidian\Zetamac`).
3. Click **Save Settings**.
4. Click **Test Connection**. It should display **`✅ Direct Write Success!`** to confirm the setup is working.

---

## 📈 Running the Progression Analyzer

You can launch the progression analysis and view your dashboard in two ways:

1. **Directly from the Extension:**
   Open the extension popup and click the **📊 View Progression Dashboard** button.
2. **Via Command Line:**
   Run the analysis script in your terminal:
   ```bash
   python analyze.py
   ```
   *(Optionally pass a custom vault path as an argument: `python analyze.py "C:\path\to\vault"`)*

Both methods compile your statistics, generate the local dashboard, and save it cleanly under the `analysis/zetamac_progression.html` folder inside your vault for easy access, automatically launching it in your browser.
