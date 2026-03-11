# Run from project root: .\scripts\generate_mock_data.ps1

Write-Host "Generating mock data for mall-e-app..." -ForegroundColor Green

# Get project root (where the script is being run from)
$projectRoot = Get-Location
Write-Host "Project root: $projectRoot" -ForegroundColor Cyan

# Set PYTHONPATH
$env:PYTHONPATH = "scripts"

# Activate virtual environment if it exists, create if not
$venvPath = Join-Path $projectRoot "scripts\get_store_url_and_tags\venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (-Not (Test-Path $venvPath)) {
    Write-Host "Virtual environment not found. Creating it now..." -ForegroundColor Yellow
    $scraperPath = Join-Path $projectRoot "scripts\get_store_url_and_tags"
    Set-Location $scraperPath
    python -m venv venv
    & "$scraperPath\venv\Scripts\Activate.ps1"
    pip install -r requirements.txt
    playwright install chromium
    Set-Location $projectRoot
} else {
    Write-Host "Activating existing virtual environment..." -ForegroundColor Yellow
    & $activateScript
}

# Create mall-e-app/src/data directory if it doesn't exist
$dataPath = Join-Path $projectRoot "mall-e-app\src\data"
if (-Not (Test-Path $dataPath)) {
    Write-Host "Creating data directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
}

# Run scraper with limited stores and URLs for quick mock data
Write-Host "Running scraper (this may take a few minutes)..." -ForegroundColor Yellow
Write-Host "Scraping AmericanEagle and Abercrombie with max 3 URLs per store..." -ForegroundColor Cyan

try {
    $jsonOutput = python -m get_store_url_and_tags --stores "AmericanEagle,Abercrombie" --max-urls-per-shop 3 --json 2>&1 | Where-Object { $_ -match '^\s*[\[\{]' -or $_ -match '^\s*[\]\}]' -or $_ -match '^\s*"' }

    $outputFile = Join-Path $projectRoot "mall-e-app\src\data\mock-data.json"
    $jsonOutput | Out-File -FilePath $outputFile -Encoding UTF8

    Write-Host "Mock data generated successfully!" -ForegroundColor Green
    Write-Host "Location: $outputFile" -ForegroundColor Cyan

    # Check if file has content
    $fileContent = Get-Content $outputFile -Raw
    if ($fileContent -and $fileContent.Length -gt 10) {
        $productCount = (Select-String -Path $outputFile -Pattern '"item_name"' -AllMatches).Matches.Count
        Write-Host "Found $productCount products in the mock data." -ForegroundColor Green
    } else {
        Write-Host "WARNING: Mock data file appears to be empty or invalid." -ForegroundColor Red
        Write-Host "Check the scraper logs above for errors." -ForegroundColor Yellow
    }
} catch {
    Write-Host "ERROR: Failed to run scraper." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}