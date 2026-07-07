# Deployment

For Kaggle judging, a public GitHub repository is enough if live deployment is
not practical. A live Cloud Run URL is a nice extra signal for deployability.

## Local Product Demo

```bash
cd bookweaver-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn bookweaver_app:app --host 127.0.0.1 --port 7860
```

Open `http://127.0.0.1:7860` and record the product workflow: submit book,
analyze, translate, export.

## Option A: Deploy The Product UI To Cloud Run

This deploys the visible BookWeaver Studio web app.

### Prerequisites

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

Create the Gemini key secret:

```bash
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
```

Grant your Cloud Run service account access to the secret. Replace the project
number and service account if your setup differs:

```bash
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Deploy

```bash
gcloud run deploy bookweaver-studio \
  --source . \
  --region us-central1 \
  --set-secrets GOOGLE_API_KEY=GOOGLE_API_KEY:latest \
  --set-env-vars TRANSLATIONTRAIL_MODEL=gemini-3.5-flash,TRANSLATIONTRAIL_WORKSPACE=sample_workspace \
  --allow-unauthenticated
```

Cloud Run will build from the included `Dockerfile` and print a service URL.
Use that as the optional live demo URL in Kaggle.

## Option B: Deploy The ADK Agent UI To Cloud Run

This deploys the ADK dev-style agent app, useful as supporting evidence for the
multi-agent layer. The product UI above is better for the main demo video.

Official ADK Cloud Run docs expect:

- `agent.py` in the agent directory
- a `root_agent` variable
- `__init__.py` importing the agent module
- `requirements.txt`

This project follows that structure in `translationtrail/`.

```bash
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="us-central1"
export SERVICE_NAME="bookweaver-adk"
export APP_NAME="translationtrail"

adk deploy cloud_run \
  --project="$GOOGLE_CLOUD_PROJECT" \
  --region="$GOOGLE_CLOUD_LOCATION" \
  --service_name="$SERVICE_NAME" \
  --app_name="$APP_NAME" \
  --with_ui \
  translationtrail
```

If deployment succeeds, ADK prints a service URL. Use that as the public demo
link only if you want to show the agent graph/dev UI.

## Important Production Note

This sample uses `sample_workspace/` inside the container. For a real user-facing
translation service, use authenticated access and persistent storage. Do not
deploy copyrighted or private documents to an unauthenticated public service.

## Official References

- ADK Cloud Run deployment: https://adk.dev/deploy/cloud-run/
