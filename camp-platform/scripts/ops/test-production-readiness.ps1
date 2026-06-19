param(
  [string]$TaskPrefix = "CampPlatformCrawl",
  [int]$MaxSnapshotAgeHours = 24,
  [switch]$RequireScheduler,
  [switch]$RequireSupabase,
  [switch]$RequireKakao,
  [switch]$CheckSupabaseConnection
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$checks = New-Object System.Collections.Generic.List[object]

function Add-Check {
  param(
    [string]$Name,
    [string]$Status,
    [string]$Detail
  )

  $checks.Add([pscustomobject]@{
    Check = $Name
    Status = $Status
    Detail = $Detail
  })
}

function Get-EnvMap {
  param([string]$Path)

  $map = @{}
  if (-not (Test-Path -LiteralPath $Path)) {
    return $map
  }

  Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
      return
    }
    if ($line.StartsWith("export ")) {
      $line = $line.Substring(7).Trim()
    }
    $equalsAt = $line.IndexOf("=")
    if ($equalsAt -le 0) {
      return
    }
    $key = $line.Substring(0, $equalsAt).Trim()
    $value = $line.Substring($equalsAt + 1).Trim().Trim('"').Trim("'")
    if ($key) {
      $map[$key] = $value
    }
  }

  return $map
}

function Has-EnvValue {
  param(
    [hashtable]$Map,
    [string[]]$Names
  )

  foreach ($name in $Names) {
    if ($Map.ContainsKey($name) -and -not [string]::IsNullOrWhiteSpace([string]$Map[$name])) {
      return $true
    }
    $processValue = [Environment]::GetEnvironmentVariable($name)
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
      return $true
    }
  }

  return $false
}

function Get-EnvValue {
  param(
    [hashtable]$Map,
    [string[]]$Names
  )

  foreach ($name in $Names) {
    if ($Map.ContainsKey($name) -and -not [string]::IsNullOrWhiteSpace([string]$Map[$name])) {
      return [string]$Map[$name]
    }
    $processValue = [Environment]::GetEnvironmentVariable($name)
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
      return $processValue
    }
  }

  return ""
}

function Add-EnvCheck {
  param(
    [hashtable]$Map,
    [string]$Name,
    [string[]]$Keys,
    [switch]$Required
  )

  $hasValue = Has-EnvValue -Map $Map -Names $Keys
  if ($hasValue) {
    Add-Check $Name "OK" ("configured: " + ($Keys -join " or "))
    return
  }

  if ($Required) {
    Add-Check $Name "FAIL" ("missing: " + ($Keys -join " or "))
  } else {
    Add-Check $Name "WARN" ("missing: " + ($Keys -join " or "))
  }
}

Push-Location $projectRoot

try {
  $envPath = Join-Path $projectRoot ".env"
  $envMap = Get-EnvMap -Path $envPath

  if (Test-Path -LiteralPath $envPath) {
    Add-Check ".env" "OK" ".env exists"
  } else {
    Add-Check ".env" "FAIL" ".env is required for crawler secrets"
  }

  $nodeCommand = Get-Command "node.exe" -ErrorAction SilentlyContinue
  if ($nodeCommand) {
    $nodeVersion = (& $nodeCommand.Source "--version") -join " "
    Add-Check "Node.js" "OK" $nodeVersion
  } else {
    Add-Check "Node.js" "FAIL" "node.exe not found in PATH"
  }

  $npmCommand = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
  if ($npmCommand) {
    $npmVersion = (& $npmCommand.Source "--version") -join " "
    Add-Check "npm" "OK" $npmVersion
  } else {
    Add-Check "npm" "FAIL" "npm.cmd not found in PATH"
  }

  if (Test-Path -LiteralPath (Join-Path $projectRoot "node_modules")) {
    Add-Check "Dependencies" "OK" "node_modules exists"
  } else {
    Add-Check "Dependencies" "WARN" "run npm install before production crawl/build"
  }

  Add-EnvCheck -Map $envMap -Name "Supabase URL" -Keys @("VITE_SUPABASE_URL", "SUPABASE_URL") -Required:$RequireSupabase
  Add-EnvCheck -Map $envMap -Name "Supabase anon key" -Keys @("VITE_SUPABASE_ANON_KEY") -Required:$RequireSupabase
  Add-EnvCheck -Map $envMap -Name "Supabase service role" -Keys @("SUPABASE_SERVICE_ROLE_KEY") -Required:$RequireSupabase
  Add-EnvCheck -Map $envMap -Name "Kakao map app key" -Keys @("VITE_KAKAO_MAP_APP_KEY") -Required:$RequireKakao
  Add-EnvCheck -Map $envMap -Name "Kakao REST key" -Keys @("KAKAO_REST_API_KEY") -Required:$RequireKakao
  Add-EnvCheck -Map $envMap -Name "Reviewplace cookie" -Keys @("REVIEWPLACE_COOKIE")
  Add-EnvCheck -Map $envMap -Name "Gangnam cookie" -Keys @("GANGNAM_COOKIE")
  Add-EnvCheck -Map $envMap -Name "Mrblog auth" -Keys @("MRBLOG_COOKIE", "MRBLOG_LOGIN_ID", "MRBLOG_EMAIL", "MRBLOG_USERNAME")
  Add-EnvCheck -Map $envMap -Name "Revu auth" -Keys @("REVU_AUTHORIZATION", "REVU_COOKIE", "REVU_LOGIN_ID", "REVU_EMAIL")

  if ($CheckSupabaseConnection) {
    $supabaseUrl = Get-EnvValue -Map $envMap -Names @("VITE_SUPABASE_URL", "SUPABASE_URL")
    $supabaseKey = Get-EnvValue -Map $envMap -Names @("SUPABASE_SERVICE_ROLE_KEY", "VITE_SUPABASE_ANON_KEY")

    if ([string]::IsNullOrWhiteSpace($supabaseUrl) -or [string]::IsNullOrWhiteSpace($supabaseKey)) {
      Add-Check "Supabase REST" "FAIL" "missing Supabase URL or key"
    } else {
      $nodeCommand = Get-Command "node.exe" -ErrorAction SilentlyContinue
      $supabaseCheckPath = Join-Path $projectRoot "scripts\ops\check-supabase.cjs"
      if (-not $nodeCommand) {
        Add-Check "Supabase connection" "FAIL" "node.exe not found in PATH"
      } elseif (-not (Test-Path -LiteralPath $supabaseCheckPath)) {
        Add-Check "Supabase connection" "FAIL" "scripts\ops\check-supabase.cjs not found"
      } else {
        $checkOutput = & $nodeCommand.Source $supabaseCheckPath 2>&1
        if ($LASTEXITCODE -eq 0) {
          Add-Check "Supabase connection" "OK" "platforms/campaigns are reachable"
        } else {
          Add-Check "Supabase connection" "FAIL" (($checkOutput | Select-Object -Last 1) -join " ")
        }
      }
    }
  }

  $schemaPath = Join-Path $projectRoot "database\supabase\schema.sql"
  if (Test-Path -LiteralPath $schemaPath) {
    $schemaText = Get-Content -LiteralPath $schemaPath -Encoding UTF8 -Raw
    $requiredSchemaTokens = @("create table if not exists public.platforms", "create table if not exists public.campaigns", "close_expired_campaigns")
    $missingTokens = @($requiredSchemaTokens | Where-Object { $schemaText -notlike "*$_*" })
    if ($missingTokens.Count -eq 0) {
      Add-Check "Supabase schema" "OK" "platforms/campaigns/functions are present"
    } else {
      Add-Check "Supabase schema" "FAIL" ("missing schema tokens: " + ($missingTokens -join ", "))
    }
  } else {
    Add-Check "Supabase schema" "FAIL" "database\supabase\schema.sql not found"
  }

  $runnerPath = Join-Path $projectRoot "scripts\ops\run-crawl.ps1"
  if (Test-Path -LiteralPath $runnerPath) {
    Add-Check "Crawler runner" "OK" "scripts\ops\run-crawl.ps1 exists"
  } else {
    Add-Check "Crawler runner" "FAIL" "scripts\ops\run-crawl.ps1 not found"
  }

  $snapshotPath = Join-Path $projectRoot "public\campaigns.json"
  if (Test-Path -LiteralPath $snapshotPath) {
    try {
      $snapshot = Get-Content -LiteralPath $snapshotPath -Encoding UTF8 -Raw | ConvertFrom-Json
      $campaignCount = @($snapshot.campaigns).Count
      $updatedAt = $null
      if ($snapshot.updatedAt) {
        $updatedAt = [datetime]::Parse([string]$snapshot.updatedAt).ToUniversalTime()
      }

      if ($updatedAt) {
        $ageHours = [math]::Round(((Get-Date).ToUniversalTime() - $updatedAt).TotalHours, 1)
        if ($ageHours -le $MaxSnapshotAgeHours) {
          Add-Check "Snapshot" "OK" "$campaignCount campaigns, updated $ageHours hours ago"
        } else {
          Add-Check "Snapshot" "WARN" "$campaignCount campaigns, updated $ageHours hours ago"
        }
      } else {
        Add-Check "Snapshot" "WARN" "$campaignCount campaigns, updatedAt missing"
      }
    } catch {
      Add-Check "Snapshot" "FAIL" "public\campaigns.json is not valid JSON"
    }
  } else {
    Add-Check "Snapshot" "WARN" "public\campaigns.json not found"
  }

  $logDir = Join-Path $projectRoot "logs"
  if (Test-Path -LiteralPath $logDir) {
    $latestLog = Get-ChildItem -LiteralPath $logDir -Filter "crawl-*.log" -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    if ($latestLog) {
      $logAgeHours = [math]::Round(((Get-Date) - $latestLog.LastWriteTime).TotalHours, 1)
      Add-Check "Crawl logs" "OK" ("latest: " + $latestLog.Name + ", " + $logAgeHours + " hours ago")
    } else {
      Add-Check "Crawl logs" "WARN" "logs directory exists, no crawl-*.log files"
    }
  } else {
    Add-Check "Crawl logs" "WARN" "logs directory not found"
  }

  $taskNames = @("${TaskPrefix}_Morning", "${TaskPrefix}_Afternoon")
  foreach ($taskName in $taskNames) {
    $scheduledTask = Get-ScheduledTask -TaskPath "\" -TaskName $taskName -ErrorAction SilentlyContinue
    if ($scheduledTask) {
      $taskInfo = Get-ScheduledTaskInfo -TaskPath "\" -TaskName $taskName -ErrorAction SilentlyContinue
      $detail = "registered"
      if ($taskInfo -and $taskInfo.NextRunTime) {
        $detail = "next run: " + $taskInfo.NextRunTime
      }
      Add-Check "Scheduled task $taskName" "OK" $detail
    } else {
      if ($RequireScheduler) {
        Add-Check "Scheduled task $taskName" "FAIL" "not registered"
      } else {
        Add-Check "Scheduled task $taskName" "WARN" "not registered"
      }
    }
  }

  Write-Host ""
  Write-Host "Camp Platform Production Readiness"
  Write-Host "Project: $projectRoot"
  Write-Host ""
  $checks | Format-Table -AutoSize

  $failed = @($checks | Where-Object { $_.Status -eq "FAIL" })
  $warned = @($checks | Where-Object { $_.Status -eq "WARN" })

  Write-Host ""
  Write-Host ("Summary: {0} failed, {1} warnings, {2} checks" -f $failed.Count, $warned.Count, $checks.Count)

  if ($failed.Count -gt 0) {
    exit 1
  }

  exit 0
}
finally {
  Pop-Location
}
