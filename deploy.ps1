# deploy.ps1 - Native PowerShell deployment script for Windows

$ImageName = "hoax-detection-app"
$ContainerName = "hoax-detection-container"
$Port = 8501

Write-Host "==================================================" -ForegroundColor Green
Write-Host "🛡️ Starting Indonesian Hoax Classifier Deployment (Windows)" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# 1. Build the Docker image
Write-Host "Step 1: Building Docker image '$ImageName:latest'..." -ForegroundColor Cyan
docker build -t "$ImageName:latest" .

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed. Exiting deployment."
    exit $LASTEXITCODE
}

# 2. Stop and remove existing container if it exists
$ExistingContainer = docker ps -aq -f "name=$ContainerName"
if ($ExistingContainer) {
    Write-Host "Step 2: Stopping and removing existing container '$ContainerName'..." -ForegroundColor Cyan
    docker stop $ContainerName | Out-Null
    docker rm $ContainerName | Out-Null
} else {
    Write-Host "Step 2: No existing container named '$ContainerName' found. Skipping removal." -ForegroundColor Cyan
}

# 3. Run the container
Write-Host "Step 3: Running container '$ContainerName' on port $Port..." -ForegroundColor Cyan
docker run -d `
  --name $ContainerName `
  -p "${Port}:${Port}" `
  --restart unless-stopped `
  "$ImageName:latest"

# 4. Print status
Write-Host "==================================================" -ForegroundColor Green
Write-Host "🎉 Deployment Successful!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host "Container Status:" -ForegroundColor Yellow
docker ps -f "name=$ContainerName"
Write-Host ""
Write-Host "You can access the dashboard at:" -ForegroundColor Yellow
Write-Host "👉 Local: http://localhost:$Port" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
