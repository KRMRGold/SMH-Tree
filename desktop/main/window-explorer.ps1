Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$WarningPreference = 'SilentlyContinue'

class ExplorerToolError : System.Exception {
    ExplorerToolError([string]$message) : base($message) {}
}

function Test-ExplorerEntryName([object]$Name) {
    if ($Name -isnot [string] -or $Name.Length -lt 1 -or $Name.Length -gt 255) {
        return $false
    }
    if ($Name.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0 -or
        $Name.EndsWith('.') -or $Name.EndsWith(' ') -or
        $Name -match '^(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9\u00b9\u00b2\u00b3])(?: *\.|$)') {
        return $false
    }
    try {
        [void][Text.UTF8Encoding]::new($false, $true).GetByteCount($Name)
        return $true
    } catch {
        return $false
    }
}

function Resolve-ExplorerLocalFolder([object]$Folder) {
    if ($Folder -isnot [string] -or $Folder.Length -gt 2048 -or $Folder -notmatch '^[A-Za-z]:\\') {
        return $null
    }

    $root = $Folder.Substring(0, 3).ToUpperInvariant()
    $tail = $Folder.Substring(3)
    if ($tail.EndsWith('\')) {
        $tail = $tail.Substring(0, $tail.Length - 1)
        if (-not $tail) { return $null }
    }

    $segments = @()
    if ($tail) { $segments = $tail.Split([char]92) }
    foreach ($segment in $segments) {
        if (-not (Test-ExplorerEntryName $segment)) { return $null }
    }

    try {
        if ([IO.DriveInfo]::new($root).DriveType -ne [IO.DriveType]::Fixed) { return $null }
        $folderPath = $root
        # Check each component before traversing it to avoid following junctions or symlinks.
        $attributes = [IO.File]::GetAttributes($root)
        if ($attributes -band [IO.FileAttributes]::ReparsePoint) { return $null }
        foreach ($segment in $segments) {
            $folderPath = [IO.Path]::Combine($folderPath, $segment)
            $attributes = [IO.File]::GetAttributes($folderPath)
            if (($attributes -band [IO.FileAttributes]::ReparsePoint) -or
                -not ($attributes -band [IO.FileAttributes]::Directory)) {
                return $null
            }
        }
        return $folderPath
    } catch {
        return $null
    }
}

function Get-ExplorerWindowInfo([object]$Browser, [string]$ExplorerPath) {
    try {
        if ($null -eq $Browser -or
            -not [string]::Equals([string]$Browser.FullName, $ExplorerPath, [StringComparison]::OrdinalIgnoreCase)) {
            return $null
        }
        $handle = [long]$Browser.HWND
        if ($handle -le 0) { return $null }

        $self = $Browser.Document.Folder.Self
        if (-not $self.IsFileSystem -or -not $self.IsFolder) { return $null }
        $folder = Resolve-ExplorerLocalFolder $self.Path
        if (-not $folder) { return $null }

        $title = ([string]$Browser.LocationName -replace '[\x00-\x1f\x7f]', ' ').Trim()
        if (-not $title) { $title = $folder }
        if ($title.Length -gt 240) { $title = $title.Substring(0, 240) }
        return @{
            window_id = $handle.ToString([Globalization.CultureInfo]::InvariantCulture)
            folder = $folder
            title = $title
        }
    } catch {
        # Explorer windows can close or navigate while COM is enumerating them.
        return $null
    }
}

function Get-ExplorerWindows([object]$Shell, [string]$ExplorerPath) {
    $windows = $Shell.Windows()
    if ($null -eq $windows) { return }
    $count = [int]$windows.Count
    if ($count -gt 256) {
        throw [ExplorerToolError]::new('Too many shell windows are open. Close some and try again.')
    }
    for ($index = 0; $index -lt $count; $index++) {
        try { $browser = $windows.Item($index) } catch { continue }
        $info = Get-ExplorerWindowInfo $browser $ExplorerPath
        if ($null -ne $info) {
            @{ browser = $browser; info = $info }
        }
    }
}

function Find-ExplorerWindow([object]$Shell, [string]$ExplorerPath, [string]$WindowId, [string]$Folder) {
    $matches = @(Get-ExplorerWindows $Shell $ExplorerPath | Where-Object {
        $_.info.window_id -ceq $WindowId -and $_.info.folder -ceq $Folder
    })
    if ($matches.Count -gt 1) {
        throw [ExplorerToolError]::new('Multiple Explorer tabs match this folder. Choose a different tab or close the duplicate.')
    }
    if ($matches.Count -ne 1) {
        throw [ExplorerToolError]::new('The Explorer window or folder changed. Refresh the window list.')
    }
    return $matches[0]
}

function Read-ExplorerFolder([object]$Browser, [string]$ExplorerPath, [hashtable]$Expected) {
    $entries = [Collections.Generic.List[object]]::new()
    $visited = 0
    $truncated = $false
    try {
        foreach ($path in [IO.Directory]::EnumerateFileSystemEntries($Expected.folder)) {
            if ($visited -eq 100) {
                $truncated = $true
                break
            }
            $visited++
            $name = [IO.Path]::GetFileName($path)
            if (-not (Test-ExplorerEntryName $name)) { continue }
            try { $attributes = [IO.File]::GetAttributes($path) } catch { continue }
            if ($attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
            $entries.Add(@{
                name = $name
                is_folder = [bool]($attributes -band [IO.FileAttributes]::Directory)
            })
        }
    } catch {
        throw [ExplorerToolError]::new('Unable to read this Explorer folder.')
    }

    $current = Get-ExplorerWindowInfo $Browser $ExplorerPath
    if ($null -eq $current -or $current.window_id -cne $Expected.window_id -or $current.folder -cne $Expected.folder) {
        throw [ExplorerToolError]::new('The Explorer window or folder changed. Refresh the window list.')
    }
    return @{ window = $current; entries = $entries.ToArray(); truncated = $truncated }
}

function Invoke-ExplorerRequest([object]$Request) {
    if ($Request -isnot [pscustomobject] -or $null -eq $Request.PSObject.Properties['action'] -or
        $Request.action -isnot [string]) {
        throw [ExplorerToolError]::new('Invalid Explorer request.')
    }
    $fields = switch -CaseSensitive -Exact ($Request.action) {
        'list' { 'action' }
        'inspect' { 'action'; 'window_id'; 'folder' }
        'open_child' { 'action'; 'window_id'; 'folder'; 'child' }
        default { throw [ExplorerToolError]::new('Unsupported Explorer action.') }
    }
    $properties = @($Request.PSObject.Properties.Name)
    if ($properties.Count -ne @($fields).Count -or @($properties | Where-Object { $_ -cnotin $fields }).Count) {
        throw [ExplorerToolError]::new('Invalid Explorer request fields.')
    }
    if ($Request.action -cne 'list') {
        if ($Request.window_id -isnot [string] -or $Request.window_id -notmatch '^[1-9][0-9]{0,18}$' -or
            $Request.folder -isnot [string] -or $Request.folder.Length -gt 2048) {
            throw [ExplorerToolError]::new('Invalid Explorer window or folder.')
        }
        if ($Request.action -ceq 'open_child' -and -not (Test-ExplorerEntryName $Request.child)) {
            throw [ExplorerToolError]::new('Choose an immediate child folder by name.')
        }
    }

    $windowsDirectory = [Environment]::GetFolderPath([Environment+SpecialFolder]::Windows)
    $explorerPath = [IO.Path]::Combine($windowsDirectory, 'explorer.exe')
    $shell = New-Object -ComObject 'Shell.Application'
    if ($Request.action -ceq 'list') {
        $windows = @(Get-ExplorerWindows $shell $explorerPath | ForEach-Object { $_.info })
        return @{ windows = $windows }
    }

    $entry = Find-ExplorerWindow $shell $explorerPath $Request.window_id $Request.folder
    if ($Request.action -ceq 'inspect') {
        return Read-ExplorerFolder $entry.browser $explorerPath $entry.info
    }

    $childPath = [IO.Path]::Combine($entry.info.folder, $Request.child)
    $childFolder = Resolve-ExplorerLocalFolder $childPath
    if (-not $childFolder) {
        throw [ExplorerToolError]::new('The child must be an existing local folder without a junction or symlink.')
    }
    $entry = Find-ExplorerWindow $shell $explorerPath $Request.window_id $Request.folder
    [void]$entry.browser.Navigate2($childFolder)
    $wait = [Diagnostics.Stopwatch]::StartNew()
    do {
        $changed = Get-ExplorerWindowInfo $entry.browser $explorerPath
        if ($null -ne $changed -and $changed.window_id -ceq $Request.window_id) {
            if ($changed.folder -ceq $childFolder) {
                return Read-ExplorerFolder $entry.browser $explorerPath $changed
            }
            if ($changed.folder -cne $Request.folder) {
                throw [ExplorerToolError]::new('Explorer navigated to a different folder. Refresh the window list.')
            }
        }
        Start-Sleep -Milliseconds 100
    } while ($wait.ElapsedMilliseconds -lt 3000)
    throw [ExplorerToolError]::new('Explorer did not confirm the requested folder. Refresh the window list.')
}

function Invoke-ExplorerToolMain {
    [Console]::InputEncoding = [Text.UTF8Encoding]::new($false, $true)
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    try {
        $raw = [Console]::In.ReadToEnd()
        $trimmed = $raw.Trim()
        if ($raw.Length -gt 8192 -or -not $trimmed.StartsWith('{') -or -not $trimmed.EndsWith('}')) {
            throw [ExplorerToolError]::new('Expected one bounded Explorer request object.')
        }
        try { $request = ConvertFrom-Json -InputObject $trimmed } catch {
            throw [ExplorerToolError]::new('Invalid Explorer request JSON.')
        }
        $result = Invoke-ExplorerRequest $request
    } catch [ExplorerToolError] {
        $result = @{ error = $_.Exception.Message }
    } catch [System.UnauthorizedAccessException] {
        $result = @{ error = 'This Windows session denied access to File Explorer.' }
    } catch {
        $result = @{ error = 'File Explorer could not complete this request.' }
    }
    [Console]::WriteLine((ConvertTo-Json -InputObject $result -Depth 5 -Compress))
}

Invoke-ExplorerToolMain
