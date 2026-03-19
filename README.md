# redmine-cli

`redmine-cli` is a Windows-focused Redmine utility with two modes:

- a classic GUI exporter under `gui/`
- a newer CLI/TUI available globally as `redmine`

It can:

- export monthly Redmine time entries into Excel and PDF
- guide you through a keyboard-driven TUI workflow
- pull `Done` tasks from Notion
- create Redmine issues from those tasks
- log spent time onto the created issues

## Project structure

```text
.
|- bin/                 # global redmine command wrapper
|- cli/                 # CLI / TUI implementation
|- gui/                 # original GUI implementation
|- .env.example         # example local configuration
|- package.json         # npm wrapper package
`- README.md
```

## Requirements

- Windows
- Node.js 18+ recommended
- Python 3.11+ recommended
- Microsoft Excel desktop app installed

Excel is required because the timetable export still uses Excel automation to generate the PDF.

## Configuration

Create a local `.env` file in the repository root based on `.env.example`.

Required values:

- `REDMINE_BASE_URL`
- `REDMINE_API_KEY`
- `REDMINE_USER_ID`
- `NOTION_API_TOKEN`
- `NOTION_TASKS_DATABASE_ID`
- `NOTION_PROJECTS_DATABASE_ID`

Useful optional values:

- `DEFAULT_REDMINE_ACTIVITY_ID`
- `NOTION_PROJECT_NAMES`
- `NOTION_WORK_PRIVATE_SCOPE`
- `NOTION_DONE_STATUS_NAME`

Do not commit your real `.env`.

## CLI / TUI setup

Install the global `redmine` command from the repository root:

```powershell
npm install
npm link
```

After that, `redmine` will be available from any folder.

The first time you run it, the wrapper bootstraps a local Python runtime into `.runtime` and installs the CLI dependencies automatically.

### CLI commands

```powershell
redmine
redmine timetable
redmine upload
redmine config doctor
```

Recommended first check:

```powershell
redmine config doctor
```

## Original GUI setup

If you want to use the original GUI app:

```powershell
python -m venv gui\venv
.\gui\venv\Scripts\python -m pip install -r gui\requirements.txt
.\gui\venv\Scripts\python gui\main.py
```

The GUI source and assets live under `gui/`.

## Build the original GUI

To build the GUI into an executable:

```powershell
python -m venv gui\venv
.\gui\venv\Scripts\python -m pip install -r gui\requirements.txt
.\gui\venv\Scripts\python -m pip install pyinstaller
.\gui\build.bat
```

The output will be generated under `gui\dist\redmine-cli`.

## Features

### Timetable export

- month selection
- Redmine time-entry download
- Excel timesheet generation
- PDF export through Excel automation

### Upload flow

- TUI home screen with keyboard navigation
- Notion `Done` task filtering
- Work / Private scope filtering
- Notion project filtering
- Redmine project selection
- create issues directly under a project or under an existing parent issue
- choose tracker, `% done`, hours, minutes, activity, comment, spent date
- summary screen before upload
- archive uploaded Notion tasks and set `Done at`

## Notes

- `gui\unfilled.xlsx` must stay in the repository because the original GUI timetable generation depends on it.
- If `redmine upload` fails with Notion access errors, make sure your Notion integration is shared with the `Tasks` and `Projects` databases.
- If you move to another machine, run `npm link` again after cloning the repository.
