# PowerShell Reference Scripts

Replace `YOUR_TOKEN`, site URL, and credentials before use.

## Phase 0 — Auth test
```powershell
$base = "https://your-site.com/wp-json/wp/v2"
$t    = "YOUR_TOKEN"
$me   = Invoke-RestMethod -Uri "$base/users/me?t=$t" -Method Get
Write-Host "✓ Auth: $($me.name) (id=$($me.id))"
```

## Phase 1 — Link replacement
```powershell
$base  = "https://your-site.com/wp-json/wp/v2"
$t     = "YOUR_TOKEN"
$rows  = Import-Csv "phase1-dryrun-YYYYMMDD.csv"

foreach ($row in $rows) {
    $id = $row.post_id
    if ($id -match "NOT_FOUND|MANUAL|^$") { continue }

    # ALWAYS fetch individually — batch fetch concatenates content.raw
    $post   = Invoke-RestMethod -Uri "$base/posts/$id`?context=edit&t=$t"
    $newRaw = $post.content.raw -replace [regex]::Escape($row.old_link), $row.new_link

    if ($newRaw -ne $post.content.raw) {
        $body    = @{ content = $newRaw } | ConvertTo-Json -Depth 2 -Compress
        $headers = @{ "Content-Type" = "application/json" }
        Invoke-RestMethod -Uri "$base/posts/$id`?t=$t" -Method Post -Body $body -Headers $headers
        Write-Host "✓ $($row.slug)"
    }
    Start-Sleep -Seconds 25
}
```

## Phase 3 — Background draft (50+ posts)
```powershell
# Write script to file, launch hidden
$script = @'
$base = "https://your-site.com/wp-json/wp/v2"; $t = "YOUR_TOKEN"
$log  = "$env:TEMP\phase3-log.csv"; $results = @()
Import-Csv "execution-actions.csv" | Where-Object { $_.action -eq "DRAFT" } | ForEach-Object {
    $id   = $_.wp_id
    if ($id -match "NOT_FOUND|MANUAL|^$") { $results += [pscustomobject]@{slug=$_.url_slug;result="SKIP"}; return }
    $type = if ($_.post_type -eq "page") { "pages" } else { "posts" }
    try {
        Invoke-RestMethod -Uri "$base/$type/$id`?t=$t" -Method Post `
            -Body '{"status":"draft"}' -Headers @{"Content-Type"="application/json"}
        $results += [pscustomobject]@{slug=$_.url_slug;result="DRAFTED"}
    } catch { $results += [pscustomobject]@{slug=$_.url_slug;result="ERROR:$_"} }
    Start-Sleep -Seconds 25
}
$results | Export-Csv $log -NoTypeInformation
'@
$path = "$env:TEMP\wp-draft.ps1"
Set-Content -Path $path -Value $script -Encoding UTF8
Start-Process powershell.exe -ArgumentList "-NonInteractive -File `"$path`"" -WindowStyle Hidden
Write-Host "Background process started. Monitor: $env:TEMP\phase3-log.csv"
```

## Phase 4 — 410 redirects
```powershell
$wpUrl = "https://your-site.com"; $t = "YOUR_TOKEN"
Import-Csv "execution-actions.csv" | Where-Object { $_.action -eq "DRAFT" } | ForEach-Object {
    $slug = $_.url_slug.Trim()
    if ($slug -notmatch "^/") { $slug = "/$slug" }
    if ($slug -notmatch "/$")  { $slug = "$slug/" }
    $body = @{ url=$slug; action_type="url"; action_code=410
               action_data=@{url=""}; match_type="url"; regex=$false
             } | ConvertTo-Json -Depth 3 -Compress
    Invoke-RestMethod -Uri "$wpUrl/wp-json/redirection/v1/redirect?t=$t" `
        -Method Post -Body $body -Headers @{"Content-Type"="application/json"}
    Write-Host "✓ 410: $slug"
    Start-Sleep -Seconds 25
}
```

## Common gotchas
| Problem | Fix |
|---------|-----|
| `&` in URL string | Use backtick: `` ?t=tok`&other=val `` |
| Batch fetch concatenates content.raw | Always `GET /posts/{id}?context=edit` individually |
| MCP times out on long loop | `Start-Process -WindowStyle Hidden` |
| 400 Bad Request | Add `-Depth 2 -Compress` to `ConvertTo-Json` |
| `date` variable conflict | Use fixed string `"20260601"` |
| `nslookup` not found | Use `Resolve-DnsName` |
