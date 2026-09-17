# Daftra Scraper — Setup & Usage

This script connects to your **already logged-in Edge browser** and crawls
every page of your Daftra account, saving all pages, menus, inputs, buttons,
table columns, dropdowns, and features to `daftra_analysis.md`.

---

## Step 1 — Install dependencies

Open PowerShell inside the `scraper` folder and run:

```powershell
pip install -r requirements.txt
```

You also need **msedgedriver** matching your Edge version:
- Check your Edge version: open Edge → `edge://version`
- Download matching EdgeDriver: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
- Place `msedgedriver.exe` anywhere on your PATH (e.g. `C:\Windows\`)

---

## Step 2 — Launch Edge with remote debugging

**Close all Edge windows first**, then run this in PowerShell:

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\edge-debug"
```

> If Edge is installed elsewhere, adjust the path accordingly.

---

## Step 3 — Log in to Daftra

In the Edge window that just opened, go to:
```
https://moustafazen90.daftra.com/
```
Log in with your credentials and make sure you can see the dashboard.

---

## Step 4 — Run the scraper

In PowerShell (from the `scraper` folder):

```powershell
python daftra_scraper.py
```

The script will:
1. Connect to your logged-in Edge session
2. Visit every page it can find (up to 300 pages)
3. Extract headings, nav menus, buttons, form fields, table columns, dropdowns, tabs, badges, and cards
4. Save everything to `daftra_analysis.md`

---

## Output

`daftra_analysis.md` will contain a section for every page with:

| Section | What it captures |
|---|---|
| Headings | H1–H4 titles on the page |
| Navigation / Menu Items | Sidebar and top-nav links |
| Tabs | Tab bar labels |
| Buttons / Actions | All clickable buttons |
| Table Columns | Column headers in data tables |
| Form Fields | Every input, textarea, select with its label |
| Dropdowns | All `<select>` elements and their options |
| Status Labels | Badges and status chips |
| Cards / Widgets | Dashboard card/widget titles |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SessionNotCreatedException` | msedgedriver version doesn't match Edge. Download the correct one. |
| `ConnectionRefusedError` | Edge wasn't started with `--remote-debugging-port=9222`. Redo Step 2. |
| Script visits login page only | You weren't logged in. Log in first, then run the script. |
| Some pages are empty | The page uses heavy JavaScript. Increase `PAGE_WAIT` in the script (default: 2.5s). |
