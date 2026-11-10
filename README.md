# FitnessTracker

A small Django app for logging workouts, tracking bodyweight over time and
keeping a short list of goals.

- **Workouts** are recorded against a split (push / pull / legs / arms) and can
  be rated 1-5 stars.
- **Lifts** belong to a workout; each lift holds any number of sets of
  reps x weight.
- **Bodyweight** entries are charted over time on the homepage.
- **Goals** are a simple checklist you can tick off.
- **Motivation** shows a random quote from `home/quotes.txt`.

The app is single-user: there is no per-user data scoping, so everyone who can
log in sees the same workouts and weights. Every view requires a login.

## Requirements

- Python 3.10+
- Django 4.2 (see `requirements.txt`)

## Setup

```bash
git clone https://github.com/K-D0T/FitnessTracker.git
cd FitnessTracker

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit it, see Configuration below

python manage.py migrate
python manage.py createsuperuser # the account you'll log in with
python manage.py runserver
```

Then open http://127.0.0.1:8000/ and sign in.

A fresh clone starts with an empty database. `db.sqlite3` is deliberately not
in version control, since it holds personal health data.

## Configuration

Settings that differ between machines are read from the environment;
`settings.py` has no secrets in it. Copy `.env.example` to `.env` (which is
git-ignored) and set what you need:

| Variable | Default | Notes |
| --- | --- | --- |
| `DJANGO_DEBUG` | `True` | Set to `False` for anything internet-facing. |
| `DJANGO_SECRET_KEY` | dev-only fallback | **Required** when `DJANGO_DEBUG` is off. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma-separated origins, if served over HTTPS behind a proxy. |
| `DJANGO_TIME_ZONE` | `UTC` | Set to your own zone, e.g. `America/Denver`. |
| `DJANGO_DB_PATH` | `db.sqlite3` | Alternate SQLite file. |

`DJANGO_TIME_ZONE` is worth setting: bodyweight and workout dates are recorded
with `timezone.localdate()`, so while it is left at UTC an evening weigh-in in
a western timezone is filed under the next day.

### Running with DEBUG off

With `DJANGO_DEBUG=False`, a real `DJANGO_SECRET_KEY` is required and secure
cookies, HSTS and SSL redirection are switched on, so the app expects to be
served over HTTPS. Static files are no longer served by Django:

```bash
python manage.py collectstatic   # writes to staticfiles/
python manage.py check --deploy
```

## Tests

```bash
python manage.py test
```

The suite covers the write endpoints (login required, POST required, CSRF
enforced, rating range), the chart and listing queries, and the model and form
behaviour around dates.

## Project layout

```
fitnesstracker/      project config, URLs, static CSS
home/                the single app: models, views, forms, templates
home/quotes.txt      motivational quotes, one per line
manage.py
```

## License

MIT. See [LICENSE](LICENSE).
