<#
.SYNOPSIS
    Export a fresh viewer bundle, build it, check it, and deploy it to Cloudflare Pages.

.DESCRIPTION
    A direct upload: no git integration, no CI, nothing scheduled. Four steps.

      1. Export a fresh bundle. `driftwatch propagate` writes the catalogue side of it
         (elements.bin, reference.bin, objects.json, manifest.json) at a reference time, and
         `driftwatch report` writes the conjunctions side (conjunctions.json,
         conjunction-tracks.bin) for a stored run's scenario. Neither rescreens.
      2. Build. `npm run build` in web/, which copies public/ into dist/ and bundles the app.
      3. Check what is about to be published, with `driftwatch check-bundle`, over dist/
         rather than over the source bundle -- the build is what actually ships. It refuses
         to go on if anything looks like a redistributed SpaceX file or a credential, or if
         any file is over the 25 MiB Cloudflare Pages limit. See driftwatch/export/audit.py.
      4. `wrangler pages deploy` with an explicit --branch, so a preview and a production
         deploy are separate: Pages treats the project's production branch name as production
         and every other branch name as a preview with its own URL.

    Authentication is wrangler's. Either run `npx wrangler login` once, or set
    CLOUDFLARE_API_TOKEN (and CLOUDFLARE_ACCOUNT_ID) in the environment. The token is never
    written anywhere by this script, and check-bundle refuses to publish a bundle that
    contains its value.

    Nothing here is scheduled. The daily automated pipeline is Phase 4.

.PARAMETER Branch
    The Pages branch to deploy to. Defaults to "preview". Use "main" (the project's
    production branch) for a production deploy.

.PARAMETER Run
    The stored run whose conjunctions are exported. Default "latest".

.PARAMETER Scenario
    Which scenario of that run to show. Default: the run's first stored scenario.

.PARAMETER At
    Reference time for the catalogue export, ISO 8601 UTC. Default: now, to the minute.

.PARAMETER ProjectName
    The Cloudflare Pages project. Default "driftwatch".

.PARAMETER SkipExport
    Deploy what is already in web/public/data instead of exporting a fresh bundle.

.PARAMETER DryRun
    Do everything except the upload. Use it to see the check and the sizes.

.EXAMPLE
    pwsh -File scripts/deploy-pages.ps1
    pwsh -File scripts/deploy-pages.ps1 -Branch main
    pwsh -File scripts/deploy-pages.ps1 -Branch main -Run demo_20260901T204800Z -Scenario quiet
    pwsh -File scripts/deploy-pages.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$Branch = "preview",
    [string]$Run = "latest",
    [string]$Scenario,
    [string]$At,
    [string]$ProjectName = "driftwatch",
    [switch]$SkipExport,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$web = Join-Path $repo "web"
$dist = Join-Path $web "dist"

function Invoke-Step {
    param([string]$Title, [scriptblock]$Body)
    Write-Host ""
    Write-Host "== $Title" -ForegroundColor Cyan
    & $Body
    if ($LASTEXITCODE -ne 0) { throw "$Title failed with exit code $LASTEXITCODE" }
}

if (-not $At) { $At = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:00Z") }

if (-not $SkipExport) {
    Invoke-Step "Exporting the catalogue bundle at $At" {
        uv run --project $repo driftwatch propagate --at $At
    }
    $reportArgs = @("report", $Run)
    if ($Scenario) { $reportArgs += @("--scenario", $Scenario) }
    Invoke-Step "Exporting the conjunctions bundle from run '$Run'" {
        uv run --project $repo driftwatch @reportArgs
    }
} else {
    Write-Host "Skipping the export; deploying whatever is in web/public/data." -ForegroundColor Yellow
}

Invoke-Step "Building the viewer" {
    npm --prefix $web run build
}

# The check runs over dist/, because that is what is uploaded: the built app plus the data
# the build copied out of public/. Running it over the source bundle would miss anything the
# build itself dragged in.
Invoke-Step "Checking the built bundle" {
    uv run --project $repo driftwatch check-bundle --dir $dist
}

if ($DryRun) {
    Write-Host ""
    Write-Host "Dry run: not uploading. The bundle in $dist is ready to deploy." -ForegroundColor Yellow
    exit 0
}

Invoke-Step "Deploying to Cloudflare Pages (project $ProjectName, branch $Branch)" {
    npx wrangler pages deploy $dist --project-name $ProjectName --branch $Branch --commit-dirty=true
}

Write-Host ""
Write-Host "Deployed $ProjectName from branch '$Branch'." -ForegroundColor Green
Write-Host "A branch that is not the project's production branch gets its own preview URL." -ForegroundColor Green
