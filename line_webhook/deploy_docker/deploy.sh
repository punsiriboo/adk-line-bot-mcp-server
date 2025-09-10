source ./init.sh

echo "Deploying to Cloud Run..."
gcloud run deploy line-bot-mcp-server \
  --image gcr.io/databeat-aiagent/line-bot-mcp-server \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --env-vars-file=env.yaml
  
echo "Deployment completed!"
echo "Service URL: https://line-bot-mcp-server-1014335186278.asia-southeast1.run.app"