# PowerShell smoke test for Mini Chat
param(
    [int]$Port = 8000,
    [string]$Host = "localhost",
    [int]$MaxWait = 30,
    [int]$WaitInterval = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Starting smoke test for Mini Chat..." -ForegroundColor Green

Write-Host "Testing against http://$Host`:$Port" -ForegroundColor Cyan

# Function to check if port is listening
function Wait-ForPort {
    Write-Host "Waiting for app to start on port $Port..." -ForegroundColor Yellow
    $waited = 0
    
    while ($waited -lt $MaxWait) {
        try {
            $response = Invoke-RestMethod -Uri "http://$Host`:$Port/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
            Write-Host "App is responding on port $Port" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Host "   Still waiting... ($waited/$MaxWait seconds)" -ForegroundColor Gray
            Start-Sleep -Seconds $WaitInterval
            $waited += $WaitInterval
        }
    }
    
    Write-Host "Timeout waiting for app to start" -ForegroundColor Red
    return $false
}

# Function to run health check
function Test-Health {
    Write-Host "Testing health endpoint..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "http://$Host`:$Port/health" -Method Get
        if ($response.status -eq "healthy") {
            Write-Host "Health check passed" -ForegroundColor Green
            Write-Host "Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
            return $true
        } else {
            Write-Host "Health check failed" -ForegroundColor Red
            Write-Host "Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
            return $false
        }
    }
    catch {
        Write-Host "Health check failed with error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to test happy path
function Test-HappyPath {
    Write-Host "Testing happy path..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://$Host`:$Port/" -Method Get -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "Root endpoint returns 200" -ForegroundColor Green
            return $true
        } else {
            Write-Host "Root endpoint returned $($response.StatusCode)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "Happy path test failed with error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main test execution
function Main {
    Write-Host "Starting smoke test..." -ForegroundColor Cyan
    
    # Wait for app to be ready
    if (-not (Wait-ForPort)) {
        Write-Host "Smoke test failed: App did not start" -ForegroundColor Red
        exit 1
    }
    
    # Test health endpoint
    if (-not (Test-Health)) {
        Write-Host "Smoke test failed: Health check failed" -ForegroundColor Red
        exit 1
    }
    
    # Test happy path
    if (-not (Test-HappyPath)) {
        Write-Host "Smoke test failed: Happy path test failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "SMOKE TEST PASSED!" -ForegroundColor Green
    Write-Host "App is running and responding correctly" -ForegroundColor Green
}

# Run the test
Main
