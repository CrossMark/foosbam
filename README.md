# Foosbam

[![Tests and coverage](https://github.com/CrossMark/foosbam/actions/workflows/tests.yml/badge.svg)](https://github.com/CrossMark/foosbam/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/CrossMark/foosbam/branch/main/graph/badge.svg)](https://codecov.io/gh/CrossMark/foosbam)

Foosbam is a Flask web application for keeping track of foosball matches. Players can record results, build an individual ELO rating, compare rankings, and review their match history and statistics.

This README is intended both for users who want to run their own instance and for developers who need to maintain the application.

## Features

- User registration, login, logout, and password reset.
- Player profiles and editable profile details.
- Recording and editing foosball match results.
- Individual ELO ratings and season-based rankings.
- Ranking, results, match, and player statistics pages.
- Database migrations managed with Flask-Migrate and Alembic.

## How the application is organized

The project uses Flask's application-factory pattern. The top-level `app.py` creates the application object used by Flask and by production WSGI servers.

```text
app.py                 Flask entry point and WSGI application
config.py              Environment-based application configuration
foosbam/
  __init__.py          Application factory and Flask extensions
  models.py            SQLAlchemy database models
  auth/                Authentication forms, routes, and blueprint
  core/                Match, ranking, season, profile, and statistics logic
  templates/           Jinja HTML templates
  static/              Browser assets
migrations/            Alembic/Flask-Migrate database migrations
requirements.txt       Python dependency versions
```

The normal user workflow is to register players, record the result of a match, and use the ranking and statistics pages to follow performance over time. Seasons allow rankings and ratings to be grouped by period.

## Getting started locally

### Prerequisites

- Python 3.11 or another version supported by the pinned dependencies.
- Git, if you are cloning the repository.
- A terminal or PowerShell.

### Installation

Clone the repository and enter its directory:

```bash
git clone <repository-url>
cd foosbam
```

Create and activate a virtual environment. On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Set a secret key before starting the application. Keep this value private and do not commit it to Git.

PowerShell:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-value"
```

macOS/Linux:

```bash
export SECRET_KEY="replace-with-a-long-random-value"
```

The application uses `app.sqlite` by default. Apply the existing database migrations:

```bash
flask --app app db upgrade
```

To populate a new local database with sample players, matches, results, and ratings, seed it once:

```bash
flask --app app --debug seed-demo-data
```

The command creates 120 demo matches across eight seasons. Running it again replaces the demo match, result, and rating history with a fresh sample set, while keeping the five demo accounts. It refuses to replace data if non-demo users are present. The sample matches use valid scores. In this local debug database, each demo account's password is its username (for example, `demo_alex` / `demo_alex`). This predictable password is only for local development; do not use demo accounts or debug mode in production. Newly submitted results must have a 2-point difference, with the winning score at least 10. The SQLite file is retained between application starts; do not delete it to restart the development server.

Start the development server:

```bash
flask --app app run --debug
```

Open <http://127.0.0.1:5000/> in a browser. The local SQLite database is intentionally excluded from Git by `.gitignore`.

## Deploying to PythonAnywhere EU

The same application can be hosted on PythonAnywhere's EU platform. The exact username, Python version, path, and hostname depend on the account, so replace the placeholders below with the values shown in the PythonAnywhere dashboard.

### 1. Upload the code

Upload the repository or clone it into a directory such as:

```text
/home/<username>/foosbam
```

### 2. Create a virtual environment

Open a Bash console on PythonAnywhere and create a virtual environment using the Python version that you will select for the web application:

```bash
mkvirtualenv --python=/usr/bin/python3.11 foosbam-env
workon foosbam-env
cd /home/<username>/foosbam
pip install -r requirements.txt
```

If PythonAnywhere provides a different supported Python version, use that version consistently for both the virtual environment and the web app.

### 3. Configure the application

Set the environment variables described in [Configuration](#configuration). At minimum, set a strong `SECRET_KEY`. The default SQLite database is suitable for a small personal or team instance:

```text
/home/<username>/foosbam/app.sqlite
```

Run the migrations from the project directory:

```bash
cd /home/<username>/foosbam
workon foosbam-env
flask --app app db upgrade
```

### 4. Create the PythonAnywhere web app

In the PythonAnywhere **Web** tab:

1. Add a new web app using **Manual configuration**.
2. Select the same Python version used by `foosbam-env`.
3. Set the virtualenv to the full path, for example `/home/<username>/.virtualenvs/foosbam-env`.
4. Use the EU hostname assigned to the account.
5. Open the generated WSGI configuration file and use the following application section:

```python
import sys

path = "/home/<username>/foosbam"
if path not in sys.path:
	 sys.path.insert(0, path)

from app import app as application
```

PythonAnywhere imports the WSGI application; it does not use `app.run()`. After deploying code or changing configuration, press **Reload** in the Web tab. The Web tab also contains the application and error logs.

For more detail, see the official [PythonAnywhere Flask deployment guide](https://help.pythonanywhere.com/pages/Flask/).

## Configuration

Configuration is read from environment variables in `config.py`.

| Variable | Required | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Signs sessions and password-reset tokens. Use a long, random, private value. |
| `DATABASE_URL` | No | SQLAlchemy database URL. If omitted, the application uses `app.sqlite`. |
| `MAIL_SERVER` | No | SMTP server used for password-reset email. |
| `MAIL_PORT` | No | SMTP port, commonly `587` for TLS. |
| `MAIL_USE_TLS` | No | Whether Flask-Mail should use TLS, commonly `True`. |
| `MAIL_USERNAME` | No | SMTP username. |
| `MAIL_PASSWORD` | No | SMTP password or provider-specific credential. |

The mail variables must be configured together if password-reset emails are needed. Do not commit secrets, SMTP credentials, or a production database URL to the repository.

## Development and maintenance

For a normal code change:

1. Update the relevant route, form, model, template, or static asset.
2. If a SQLAlchemy model or database schema changes, create a migration:

	```bash
	flask --app app db migrate -m "describe the schema change"
	```

3. Review the generated migration file.
4. Apply migrations:

	```bash
	flask --app app db upgrade
	```

5. Test the affected workflow locally.

Do not casually edit migration files that have already been applied to a shared or production database. Create a new migration instead. When SQLite is used, back up `app.sqlite` before applying significant schema changes. On PythonAnywhere, reload the web app after deploying code or configuration changes.

### Tests and coverage

Install the development requirements to run the test suite and measure application-code coverage:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m coverage run --branch --source=foosbam,config,app -m unittest discover -s tests
python -m coverage report -m
```

Coverage is measured for the `foosbam` application package and its root configuration and WSGI entry point; migration scripts, templates, and static assets are outside that application-code total.

## Troubleshooting

- **Sessions or login do not work:** verify that `SECRET_KEY` is set in the environment used to start the application.
- **Missing tables or database errors:** activate the correct virtual environment and run `flask --app app db upgrade` from the repository root.
- **PythonAnywhere shows an import error:** check that the WSGI `path` points to the directory containing `app.py`, and that the import is `from app import app as application`.
- **PythonAnywhere still serves old code:** reload the web app from the Web tab.
- **Password reset does not send email:** check all SMTP variables, their types and values, and the PythonAnywhere/application error logs.

## License

Foosbam is available under the [PolyForm Noncommercial License 1.0.0](LICENSE). You may use, study, modify, and share Foosbam for non-commercial purposes, including personal, hobby, educational, and public-research projects. Commercial use is not permitted under this license, so you may not use Foosbam or derivative works to make money or support a commercial service without separate permission from the copyright holder.

When you share Foosbam or substantial parts of it, keep the license and copyright notice with the work and give credit to Foosbam and this repository. See [LICENSE](LICENSE) for the full terms.

## Contributions

Bug reports, ideas, and improvements are welcome. Use [GitHub Issues](../../issues) to report problems or suggest changes. If you want to pick up an issue, comment on it first and ask for it to be formally assigned to you. Formal assignment makes issue ownership clear and helps avoid duplicated work.

For code or documentation changes, see [CONTRIBUTING.md](CONTRIBUTING.md). Please make a good-faith effort to keep changes focused, explain what you changed, and test the affected workflow. Contributions are distributed under the same PolyForm Noncommercial License.
