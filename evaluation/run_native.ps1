<#
Runs the existing module in the local Odoo test database against the 20
synthetic regression emails; exports native records and scores actual lines.
Run from the repo, e.g. evaluation/run_native.ps1 -Mode small -Round qwen01.
The same round ID resumes completed items. Use a new ID for different settings.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('small','strong','confidence','kev')][string]$Mode,
    [Parameter(Mandatory)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Round,
    [Parameter(Mandatory)][string]$Python,
    [Parameter(Mandatory)][string]$OutputDir,
    [switch]$AllowApi
)
$ErrorActionPreference='Stop'
if ($Mode -ne 'small' -and !$AllowApi) {throw 'This mode can invoke the OpenAI API; pass -AllowApi for this run.'}
$output=[IO.Path]::GetFullPath($OutputDir)
[void][IO.Directory]::CreateDirectory($output)
Push-Location (Join-Path $PSScriptRoot '..')
try {
    $prefix="/tmp/group55-$Mode-$Round"
    # Copy contents, not a nested emails/ directory, on resumed runs.
    docker compose exec -T web mkdir -p "$prefix-emls"
    if ($LASTEXITCODE) {throw 'web container unavailable'}
    docker compose cp test_kit/emails/. "web:$prefix-emls/"
    if ($LASTEXITCODE) {throw 'fixture copy failed'}
    $shell='exec odoo shell -d odoo_test --no-http --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD" --log-level=warn'
    Get-Content -Raw -Encoding utf8 evaluation/run_fixture_round.py |
        docker compose exec -T -e "ROUND_MODE=$Mode" -e "ROUND_MANIFEST=$prefix-ids.json" -e "EML_DIR=$prefix-emls" web sh -c $shell
    if ($LASTEXITCODE) {throw 'round failed; resume with same round ID after fixing the runtime'}
    Get-Content -Raw -Encoding utf8 test_kit/export_round.py |
        docker compose exec -T -e "ROUND_MANIFEST=$prefix-ids.json" -e "ROUND_OUTPUT=$prefix-native.json" web sh -c $shell
    if ($LASTEXITCODE) {throw 'native export failed'}
    $native=Join-Path $output "$Mode-$Round-native.json"
    docker compose cp "web:$prefix-native.json" $native
    if ($LASTEXITCODE) {throw 'result copy failed'}
    $scores=& $Python test_kit/score_regression.py $native
    if ($LASTEXITCODE) {throw 'regression scoring failed'}
    $scores | Set-Content -Encoding utf8 (Join-Path $output "$Mode-$Round-scores.json")
    ($scores -join [Environment]::NewLine | ConvertFrom-Json) |
        Select-Object total,drafts,right_drafts,wrong_drafts,missed_drafts,correct_actions
} finally { Pop-Location }
