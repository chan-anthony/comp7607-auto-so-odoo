<# Run one real model stage; recover completed rows from the host or container.
Use an absolute Python or a command on PATH for policy freezing and scoring.
The input directory comes from build_cases.py and build_extended.py.
Do not run competing jobs for the same stage and panel. #>
[CmdletBinding()]
param(
 [Parameter(Mandatory)][ValidateSet('calibration','test','stress')][string]$Split,
 [Parameter(Mandatory)][ValidateSet('small','strong','kev')][string]$Tier,
 [Parameter(Mandatory)][string]$DataDir,
 [switch]$Authority, [switch]$V2, [switch]$AllowApi
)
$ErrorActionPreference='Stop'
if($Tier -eq 'strong' -and !$AllowApi){throw 'Add -AllowApi to authorize the strong model for this split'}
$data=(Resolve-Path -LiteralPath $DataDir).Path
$rid=if($Authority){'/tmp/group55-panel-authority'}elseif($V2){'/tmp/group55-panel-v2'}else{'/tmp/group55-panel-v1'}
$sh='exec odoo shell -d odoo_test --no-http --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD" --log-level=warn'
Push-Location (Join-Path $PSScriptRoot '..')
$oldKey=$env:OPENAI_API_KEY
try {
    $keyArgs=@()
    if($Tier -eq 'strong'){
        if(!$oldKey){
            $entry=[IO.File]::ReadAllLines((Resolve-Path .env).Path) | Where-Object {$_ -match '^OPENAI_API_KEY='} | Select-Object -Last 1
            if(!$entry){throw 'Project API key is not configured'}
            $env:OPENAI_API_KEY=$entry.Substring('OPENAI_API_KEY='.Length).Trim().Trim('"')
        }
        $keyArgs=@('-e','OPENAI_API_KEY')
    }
    docker compose exec -T web mkdir -p $rid
    if($LASTEXITCODE){throw 'Odoo test container unavailable'}
    $required=@('manifest.json')
    if($Split -ne 'calibration'){$required+='frozen-policies.json'}
    if($Split -eq 'stress'){$required+='stress-manifest.json'}
    if($Tier -eq 'kev'){$required+="$Split-small.jsonl"}
    foreach($file in $required){
        $path=Join-Path $data $file
        if(!(Test-Path -LiteralPath $path)){throw "Missing $file"}
        docker compose cp $path "web:$rid/$file"
        if($LASTEXITCODE){throw "Could not upload $file"}
    }
    $name="$Split-$Tier.jsonl"; $local=Join-Path $data $name
    docker compose exec -T web test -f "$rid/$name"
    if($LASTEXITCODE -ne 0 -and (Test-Path -LiteralPath $local)){
        docker compose cp $local "web:$rid/$name"
        if($LASTEXITCODE){throw 'Could not restore stage output'}
    }
    Get-Content -Encoding utf8 -Raw evaluation/collect_candidates.py |
        docker compose exec -T @keyArgs -e "EVAL_TIER=$Tier" -e "EVAL_SPLIT=$Split" -e "EVAL_DIR=$rid" web sh -c $sh
    $stageExit=$LASTEXITCODE
    docker compose exec -T web test -f "$rid/$name"
    if(!$LASTEXITCODE){
        docker compose cp "web:$rid/$name" $local
        if($LASTEXITCODE){throw 'Could not save stage results on host'}
    }
    if($stageExit){throw "Stage $Tier/$Split failed; existing rows remain resumable"}
    $manifest=if($Split -eq 'stress'){'stress-manifest.json'}else{'manifest.json'}
    $want=@(Get-Content (Join-Path $data $manifest) -Raw | ConvertFrom-Json | ForEach-Object {$_} | Where-Object split -eq $Split | ForEach-Object id | Sort-Object)
    $got=@(Get-Content -LiteralPath $local | ForEach-Object {($_|ConvertFrom-Json).id} | Sort-Object)
    if($want.Count -ne $got.Count -or (Compare-Object $want $got)){throw 'Stage ID mismatch'}
    "Verified $Tier/$Split : $($got.Count) saved items"
} finally {$env:OPENAI_API_KEY=$oldKey;Pop-Location}
