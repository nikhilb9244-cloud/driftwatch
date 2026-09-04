<#
.SYNOPSIS
    Export a fresh viewer bundle, build it with the Vercel CLI, check it, and deploy the prebuilt output.

.DESCRIPTION
    The hand-run counterpart of the pipeline's deploy steps, and the same four moves in the same
    order, so that what a person deploys and what the runner deploys are built and checked the
    same way.

      1. Export a fresh bundle. `driftwatch propagate` writes the catalogue side of it
         (elements.bin, reference.bin, objects.json, manifest.json) at a reference time, and
         `driftwatch report` writes the conjunctions side (conjunctions.json, scenarios.json,
         conjunction-tracks.bin) for a stored run's scenario. Neither rescreens.
      2. Build with Vercel's own CLI: `vercel pull` fetches the project settings (root directory
         `web`, framework Vite) and `vercel build` runs the Vite build into `.vercel/output/`.
         Building locally and deploying `--prebuilt` is what lets step 3 check exactly the files
         that will be served: nothing is rebuilt on Vercel's side.
      3. Check what is about to be published, with `driftwatch check-bundle`, over
         `.vercel/output` -- the whole prebuilt output, not the source bundle. It refuses to go
         on if anything looks like a redistributed SpaceX file or a credential (including the
         literal value of VERCEL_TOKEN when it is set), or if any file is over the project's
         25 MiB per-file ceiling. See driftwatch/export/audit.py.
      4. `vercel deploy --prebuilt`, to a preview URL by default; `-Production` adds `--prod` to
         both the build and the deploy, which Vercel requires to agree.

    Authentication is the Vercel CLI's: either `npx vercel login` once on this machine, or set
    VERCEL_TOKEN in the environment (with VERCEL_ORG_ID and VERCEL_PROJECT_ID, which is how the
    pipeline runs it without a `.vercel/` link). The token is never written anywhere by this
    script. The project lives in the `nikolodeon-s-projects` team; Git builds are not
    connected, so this script and the pipeline are the only two things that ever deploy.

    The daily automated deploy is `.github/workflows/pipeline.yml`; this script is for a
    hand-run preview or a production deploy from a chosen stored run.

.PARAMETER Production
    Deploy to production (`--prod` on the build and the deploy). Without it, a preview.

.PARAMETER Run
    The stored run whose conjunctions are exported. Default "latest" -- which resolves at the
    top level of data/conjunctions/ only, so pass a run under a subdirectory explicitly.

.PARAMETER Scenario
    Which scenario of that run to show. Default: the run's first stored scenario.

.PARAMETER At
    Reference time for the catalogue export, ISO 8601 UTC. Default: now, to the minute.

.PARAMETER SkipExport
    Deploy what is already in web/public/data instead of exporting a fresh bundle.

.PARAMETER DryRun
    Do everything except the upload. Use it to see the check and the sizes.

.EXAMPLE
    pwsh -File scripts/deploy-vercel.ps1 -DryRun
    pwsh -File scripts/deploy-vercel.ps1 -Run data/conjunctions/step2-attached/demo_20260903T160600Z -Scenario quiet
    pwsh -File scripts/deploy-vercel.ps1 -Production -Run <run> -Scenario quiet
#>
[CmdletBinding()]
param(
    [switch]$Production,
    [string]$Run = "latest",
    [string]$Scenario,
    [string]$At,
    [switch]$SkipExport,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$web = Join-Path $repo "web"
$output = Join-Path $repo ".vercel\output"
$vercel = "vercel@59"

function Invoke-Step {
    param([string]$Title, [scriptblock]$Body)
    Write-Host ""
    Write-Host "== $Title" -ForegroundColor Cyan
    & $Body
    if ($LASTEXITCODE -ne 0) { throw "$Title failed with exit code $LASTEXITCODE" }
}

if (-not $At) { $At = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:00Z") }
$target = if ($Production) { "production" } else { "preview" }

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

# The token is passed on the command line only when the environment has one, so a machine that
# logged in with `vercel login` keeps working and the pipeline's token-only runner does too.
$auth = @()
if ($env:VERCEL_TOKEN) { $auth = @("--token", $env:VERCEL_TOKEN) }

Invoke-Step "Pulling the Vercel project settings ($target)" {
    Push-Location $repo
    try { npx --yes $vercel pull --yes --environment=$target @auth } finally { Pop-Location }
}

Invoke-Step "Building the viewer with the Vercel CLI into .vercel/output ($target)" {
    Push-Location $repo
    try {
        if ($Production) { npx --yes $vercel build --prod @auth } else { npx --yes $vercel build @auth }
    } finally { Pop-Location }
}

# Over the prebuilt output, because that is exactly what `vercel deploy --prebuilt` uploads: the
# built app plus the data the build copied out of web/public/. Running it over the source bundle
# would miss anything the build itself dragged in.
Invoke-Step "Checking the prebuilt output" {
    uv run --project $repo driftwatch check-bundle --dir $output
}

if ($DryRun) {
    Write-Host ""
    Write-Host "Dry run: not uploading. The prebuilt output in $output is ready to deploy." -ForegroundColor Yellow
    exit 0
}

Invoke-Step "Deploying the prebuilt output to Vercel ($target)" {
    Push-Location $repo
    try {
        if ($Production) { npx --yes $vercel deploy --prebuilt --prod @auth } else { npx --yes $vercel deploy --prebuilt @auth }
    } finally { Pop-Location }
}

Write-Host ""
Write-Host "Deployed to Vercel ($target). The URL is the last line the CLI printed above." -ForegroundColor Green
