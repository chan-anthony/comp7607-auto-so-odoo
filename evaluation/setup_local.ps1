<# Install the Group55 module and fixture catalogue in odoo_test. Existing
secrets stay untouched. No OpenAI inference, model download, or mail import
is performed here. Odoo and Ollama are reachable only via localhost ports. #>
[CmdletBinding()]
param([switch]$RunModuleTests)
$ErrorActionPreference='Stop'
Push-Location (Join-Path $PSScriptRoot '..')
try {
    $file=Join-Path (Get-Location) '.env'
    $names=if(Test-Path $file){[IO.File]::ReadAllLines($file) | ForEach-Object {($_ -split '=',2)[0].Trim()}}
    $bytes=[byte[]]::new(32)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $defaults=[ordered]@{POSTGRES_USER='odoo';POSTGRES_PASSWORD=[Convert]::ToHexString($bytes);ODOO_DB='odoo_test';ODOO_PORT='18069';OLLAMA_PORT='11435'}
    $extra=@($defaults.Keys|Where-Object {$_ -notin $names}|ForEach-Object {"$_=$($defaults[$_])"})
    if($extra.Count){[IO.File]::AppendAllText($file,[Environment]::NewLine+($extra -join [Environment]::NewLine)+[Environment]::NewLine)}
    docker compose config --quiet
    if($LASTEXITCODE){throw 'Compose configuration invalid'}
    docker compose up -d
    if($LASTEXITCODE){throw 'Compose startup failed'}
    $ready=$false
    for($i=0;$i -lt 30;$i++){
        docker compose exec -T mydb sh -c 'pg_isready -q -U "$POSTGRES_USER" -d postgres'
        if(!$LASTEXITCODE){$ready=$true;break}
        Start-Sleep -Seconds 2
    }
    if(!$ready){throw 'Postgres not ready'}
    $install='exec odoo -d odoo_test -i sale_email_order -u sale_email_order --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD" --without-demo=True --stop-after-init'
    $install+=if($RunModuleTests){' --http-port=8079 --test-tags /sale_email_order'}else{' --no-http'}
    docker compose exec -T web sh -c $install
    if($LASTEXITCODE){throw 'Module initialization failed'}
    $shell='exec odoo shell -d odoo_test --no-http --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD" --log-level=warn'
    Get-Content -Raw -Encoding utf8 test_kit/setup_test_data.py | docker compose exec -T web sh -c $shell
    if($LASTEXITCODE){throw 'Fixture catalogue setup failed'}
    $port=([IO.File]::ReadAllLines($file)|Where-Object {$_ -match '^OLLAMA_PORT=([0-9]+)$'}|Select-Object -Last 1) -replace '^OLLAMA_PORT=',''
    if(!$port){throw 'Expected numeric OLLAMA_PORT in project .env'}
    "env['ir.config_parameter'].sudo().set_param('sale_email_order.ollama_url','http://ollama:$port'); env.cr.commit()" | docker compose exec -T web sh -c $shell
    if($LASTEXITCODE){throw 'Ollama connection setting failed'}
} finally {Pop-Location}
