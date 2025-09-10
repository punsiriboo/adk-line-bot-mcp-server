source ./init.sh

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
  --set-env-vars GEMINI_API_KEY=${GEMINI_API_KEY} \
  --set-env-vars LINE_CHANNEL_ACCESS_TOKEN=${LINE_CHANNEL_ACCESS_TOKEN} \
  --set-env-vars LINE_CHANNEL_SECRET=${LINE_CHANNEL_SECRET} \
  --set-env-vars LINE_DESTINATION_USER_ID=${LINE_DESTINATION_USER_ID} \
  --set-env-vars NPX_PATH=/usr/bin/npx

echo "Deployment completed!"
echo "Service URL: https://${SERVICE_NAME}-${REGION}-${PROJECT_ID}.a.run.app"