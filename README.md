# Learnant

<p align="center">
  <img src="core/static/core/learnant-ant.svg" width="88" alt="Learnant ant emblem on a white square">
</p>

Learnant is a secure learning workspace where each institute manages its own courses, lessons, and learners.

**Deployed site:** [learnant.3o14.com](https://learnant.3o14.com)

***

# AI-Powered Course Creation Design

```
For example, a Tenant Admin provides:
- Learner: Backend Developer
- Current Level: Beginner
- Goal: Learn Python
- Available Time: 5 hours/week
- Duration: 6 weeks
```

## Prompt Setup:

Firstly I will craft a proper prompt that properly explains the AI on what is to be made. Which will be the default prompt that the AI receives each time a course creation request is made. This shall ensure the AI will not derail from the actual task of creating content.

Then I will attach/cat the information that the Tenant admin provides to build the course. (The information here is the above example.)

The AI will be instructed to output the course structure in a fixed schema structured output format in JSON.

## Temporary Storage

I will instruct the AI to write the output to a File in the container (not to the attached volume) it is running on. This file is the only file that AI could actually edit.

## Deployment to DB

It is never a good thing to allow AI to write directly to the DB. And in our usecase, we only care about writing into a particular table in DB. The only variables to a single database query will be:

- Tenant Organization
- Course Content

This will be handled by a custom python script that will only have one job; parsing the JSON output from AI and pushing it to the correct tables in the DB accessible to the prompting organization/tenant. 

After the DB is successfully updated the file is then removed. (Even if the file isn't removed, upon updates to the deployment; the temporary files automatically vanish, since it will be replaced by a new container image.)

## Questions

**What information would be sent to the AI?**
- Prompt generated according to the choices of the tenant admin.
- Tenant Admin ID (Not to AI but for use in DB Update Script)

**How you would structure and validate the AI response?**
- Fixed Output Schema for AI
- A script to check if the schema is corrrectly designed and filled.

**How you would personalize courses for different users?**
- Personalization is dependent on the selections of the prompter. But, the general fixed structure is preferred for the course. As per the user feedback new teacher personas/tones (Default Prompt Falvors) can be added on the options.

## Problems

### Hallucinations
- A default prompt guiding the AI on how exactly the answers should be structured and formatted. 
- A structured input flow only allowing tenant's to select from a given list of options where applicable (like with level, goal, time, duration, etc.). 

### Inconsistent Outputs
- Define a fixed schema for output in json, which is validated with a script before executing the database queries script.

### Token Cost Limits
- A token quota system that limits usage as per their subscribed plan.

### Privacy
- Uses the same queries that a manual course imput would use, as per individual tenant hence it only makes it editable by the tenant admin and the superior roles (superadmin, admin).

### Prompt Injection
- Only allow for a limited number of character for titles.
- AI runs on a seperate script that is configured with it's own user/group which do not have read write or execute permissions beyond what it explicitely has to run and write to. (i.e. execute[DB Entry Script] + read/write[JSON structured Output])

***

## Deploy

### Railway with GHCR

1. Create a Railway PostgreSQL service and a Django app service.
2. In Railway, configure the app service to pull `ghcr.io/<github-owner>/<repository>:master`. If the GHCR package is private, configure registry credentials in Railway.
3. Add the app's `DATABASE_URL` variable as a Railway reference to the PostgreSQL service, for example `${{Postgres.DATABASE_URL}}` (use your actual service name).
4. Set `SECRET_KEY` to a unique secret, set `DEBUG=false`, and set `ALLOWED_HOSTS` if you use hosts other than the Railway-provided domain or `learnant.3o14.com`. `RAILWAY_PUBLIC_DOMAIN` is automatically added to host and CSRF validation.
5. Attach a Railway volume to the app service at **`/app/uploads`** and set `MEDIA_ROOT=/app/uploads`. This preserves uploaded lesson media, avatars, and organization logos across app redeploys. Keep the volume; deleting it deletes uploaded files. Set this up before relying on media persistence.
6. Push to `master`. GitHub Actions builds and publishes the `:master` GHCR image and signs its digest. After the workflow succeeds, manually redeploy the Railway app to pull the updated image.
7. Set `LEARNANT_SUPERADMIN_USERNAME`, `LEARNANT_SUPERADMIN_EMAIL`, and `LEARNANT_SUPERADMIN_PASSWORD` as Railway app variables. Redeploy/restart the app service to apply them, then open its shell and run:

   ```bash
   python manage.py bootstrap_superadmin
   ```

   This command creates the initial platform Super Admin; setting the variables alone does not. The account must change its password on first login. If the command reports that the account already exists, it does not reset its password.

### Docker Compose

1. Copy `.env.example` to `.env` and set unique `SECRET_KEY` and `POSTGRES_PASSWORD` values.
2. Build and start the Django and PostgreSQL services:

   ```bash
   docker compose up --build -d
   ```

3. Open `http://localhost:8000/`. Migrations and static collection run at startup. PostgreSQL data and uploaded media use persistent Compose volumes.
4. To provision the first platform Super Admin, set the three `LEARNANT_SUPERADMIN_*` variables in `.env`, recreate the web service with `docker compose up -d web`, then run:

   ```bash
   docker compose exec web python manage.py bootstrap_superadmin
   ```

## Local development

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Apply migrations and, optionally, seed local-only demo data:

   ```bash
   python manage.py migrate
   python manage.py seed_demo  # Optional; do not use for production data
   ```

3. Start Django and open `http://127.0.0.1:8000/`:

   ```bash
   python manage.py runserver
   ```

## Tests and checks

Run the automated test suite and Django checks from the repository root:

```bash
.venv/bin/python manage.py test
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```
