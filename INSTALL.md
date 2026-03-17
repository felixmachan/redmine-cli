# Install

This repository contains two runnable versions:

- the original GUI app in `gui\main.py`
- the new CLI/TUI available globally as `redmine`

## Requirements

- Windows
- Node.js 18+ recommended
- Python 3.11+ recommended
- Microsoft Excel desktop app installed

Excel is required because the timetable export still uses Excel automation to generate the PDF.

## 1. Clone the repository

```powershell
git clone <YOUR_GITHUB_URL>
cd redmine-timetable
```

## 2. Create the local `.env`

Create a `.env` file based on `.env.example`.

Required values:

- `REDMINE_BASE_URL`
- `REDMINE_API_KEY`
- `REDMINE_USER_ID`
- `NOTION_API_TOKEN`
- `NOTION_TASKS_DATABASE_ID`
- `NOTION_PROJECTS_DATABASE_ID`

Optional but useful values:

- `DEFAULT_REDMINE_ACTIVITY_ID`
- `NOTION_PROJECT_NAMES`
- `NOTION_WORK_PRIVATE_SCOPE`

## 3. Install the CLI command

From the repository root:

```powershell
npm install
npm link
```

After that, `redmine` will be available from any folder in the terminal.

The first time you run `redmine`, the wrapper bootstraps a local Python runtime into `.runtime` and installs the CLI Python dependencies automatically.

Recommended first check:

```powershell
redmine config doctor
```

Available commands:

```powershell
redmine
redmine timetable
redmine upload
redmine config doctor
```

## 4. Run the original GUI version

If you also want to use the original GUI app:

```powershell
python -m venv gui\venv
.\gui\venv\Scripts\python -m pip install -r gui\requirements.txt
.\gui\venv\Scripts\python gui\main.py
```

## 5. Build the original GUI into an exe

If you want the packaged GUI version:

```powershell
python -m venv gui\venv
.\gui\venv\Scripts\python -m pip install -r gui\requirements.txt
.\gui\venv\Scripts\python -m pip install pyinstaller
.\gui\build.bat
```

The output will be generated under `gui\dist\redmine-timetable`.

## Notes

- Do not commit your real `.env`.
- `gui\unfilled.xlsx` must stay in the repository because the original GUI timetable generation depends on it.
- If `redmine upload` fails with Notion access errors, make sure your Notion integration is shared with the `Tasks` and `Projects` databases in Notion.
- If you move to another machine, run `npm link` again on that machine after cloning the repository.
