# Start the Vitrin background worker (Celery) on Windows.
#
# The worker runs sync/reconciliation jobs off the request path. It needs the
# same PG/Redis settings as the API; pass overrides via environment variables
# or a .env file at the repo root (loaded by acip_core.config).
#
# Usage (from the repository root, in PowerShell):
#   .\scripts\start-worker.ps1                 # worker only
#   .\scripts\start-worker.ps1 -WithBeat       # worker + beat (scheduled reconciliation)
#   .\scripts\start-worker.ps1 -Concurrency 4  # more concurrent tasks
#
# Note: Celery's default "prefork" pool does not work on Windows — this script
# uses the "solo" pool, which is the supported single-process mode for Windows
# development. For production-grade parallelism run the worker on Linux/WSL2.

param(
    [switch] $WithBeat,
    [int] $Concurrency = 1,
    [string] $LogLevel = "info"
)

$ErrorActionPreference = "Stop"

# Run from the repository root so package imports resolve.
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$env:PYTHONPATH = "packages;services"

$celeryArgs = @(
    "-m", "celery",
    "-A", "worker.celery_app:celery_app",
    "worker",
    "--pool", "solo",
    "--concurrency", "$Concurrency",
    "--loglevel", $LogLevel
)
if ($WithBeat) {
    # Embedded beat: one process runs both the worker and the schedule.
    $celeryArgs += "--beat"
}

Write-Host "Starting Vitrin worker (pool=solo, beat=$WithBeat) ..." -ForegroundColor Cyan
python @celeryArgs
