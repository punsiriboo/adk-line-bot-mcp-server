source ./init.sh
set -e

# ตั้งค่า variables
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"databeat-aiagent"}
SERVICE_NAME="line-bot-mcp-server"
REGION="asia-southeast1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# ตรวจสอบว่า PROJECT_ID ถูกตั้งค่าแล้ว
if [ "$PROJECT_ID" = "databeat-aiagent" ]; then
    echo "Error: Please set GOOGLE_CLOUD_PROJECT environment variable"
    echo "Example: export GOOGLE_CLOUD_PROJECT=your-actual-project-id"
    exit 1
fi

# ตั้งค่า gcloud project
gcloud config set project ${PROJECT_ID}

# เปิดใช้งาน APIs ที่จำเป็น
echo "Enabling required APIs..."
gcloud services enable containerregistry.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

echo "Building and deploying ${SERVICE_NAME} to Cloud Run..."

# Configure Docker เพื่อใช้ gcloud
echo "Configuring Docker for GCR..."
gcloud auth configure-docker

# Build Docker image for Cloud Run (Linux AMD64)
echo "Building Docker image for Cloud Run..."
docker build --platform linux/amd64 -t ${IMAGE_NAME} .

# Push to Google Container Registry
echo "Pushing image to GCR..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --env-vars-file=env.yaml

echo "Deployment completed!"
echo "Service URL: https://${SERVICE_NAME}-${REGION}-${PROJECT_ID}.a.run.app"