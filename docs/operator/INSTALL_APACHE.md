# Installing Apache 2.4 for RASTATIME

The RASTATIME PHP frontend (Zend Framework 1) runs on Apache 2.4 with
`mod_fcgid` and PHP CGI. This page covers the **one-time host setup**.
Service registration is handled separately by `infra/nssm/install-apache.ps1`.

> **Important — read before installing:**
>
> Do **not** register Apache as a Windows service via the usual
> `httpd.exe -k install` command.  RASTATIME wraps Apache in NSSM (like
> every other RASTATIME service) so service stop / restart is bounded
> by the NSSM `AppStopMethodWindow` / `AppKillProcessTree` settings.
> The native Apache service has no equivalent knob and routinely takes
> 15+ seconds to stop because it waits on graceful-shutdown of idle
> mod_fcgid children.

## 1. Install the binaries

1. Download Apache 2.4 (Win64, with `mod_fcgid`) — the [Apache Lounge
   distribution](https://www.apachelounge.com/download/) is the
   standard choice.
2. Extract to `C:\Tools\Apache24\` (the install scripts assume this
   path; pass `-ApacheRoot` to `install-apache.ps1` if you put it
   elsewhere).
3. Install PHP 8.3 (Non-Thread-Safe / x64) to `C:\Tools\PHP\`.

After extracting, the layout should be:

    C:\Tools\Apache24\
        bin\httpd.exe
        bin\httpd.conf
        conf\httpd.conf
        modules\mod_fcgid.so
        logs\

    C:\Tools\PHP\
        php-cgi.exe
        php.ini
        ext\

## 2. Configure httpd.conf

Edit `C:\Tools\Apache24\conf\httpd.conf`. Key sections:

### Root directives

```apache
ServerRoot "C:/Tools/Apache24"
Listen 80
ServerName localhost:80
```

### DocumentRoot pointed at the RASTATIME frontend

```apache
DocumentRoot "C:/RASTATIME/frontend/legacy/public"
<Directory "C:/RASTATIME/frontend/legacy/public">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
```

### mod_fcgid + PHP

```apache
LoadModule fcgid_module modules/mod_fcgid.so

<IfModule fcgid_module>
    FcgidInitialEnv PHPRC "C:/Tools/PHP"
    FcgidWrapper "C:/Tools/PHP/php-cgi.exe" .php
    AddHandler fcgid-script .php
    FcgidMaxRequestLen 134217728
    FcgidConnectTimeout 20
    FcgidIOTimeout 120
    # RASTATIME: keep the fcgid pool small and short-lived so PHP
    # workers get recycled regularly.  Defaults are 300 / 3600 s.
    FcgidIdleTimeout 60
    FcgidProcessLifeTime 600
</IfModule>
```

### .htaccess support (the legacy frontend uses it)

```apache
<Directory />
    AllowOverride All
</Directory>
```

## 3. Adjust PHP upload limits

Edit `C:\Tools\PHP\php.ini`:

```ini
upload_max_filesize = 512M
post_max_size       = 512M
memory_limit        = 256M
max_execution_time  = 300
max_input_time      = 300
```

These match the file-upload limits used by RASTATIME's legacy uploader
and the analyzer's expected input size.

## 4. Verify Apache starts cleanly (without registering a service)

Open an **elevated** PowerShell:

```powershell
cd C:\Tools\Apache24\bin
.\httpd.exe -t       # config syntax check
.\httpd.exe          # run in foreground (Ctrl+C to stop)
```

Browse to `http://localhost/` — you should see the RASTATIME login
page. If something is wrong, the error scrolls in the foreground
console window. Stop with **Ctrl+C** before continuing.

> If Apache fails with "AH00558: Could not reliably determine the
> server's fully qualified domain name", set `ServerName localhost:80`
> in `httpd.conf` and retry.

## 5. Wrap Apache in NSSM

From the RASTATIME repo root, in an **elevated** PowerShell:

```powershell
powershell -ExecutionPolicy Bypass `
    -File C:\RASTATIME\infra\nssm\install-apache.ps1 -StartService
```

The script:

* Detects whether `RASTATIME-APACHE` is already registered (NSSM or
  native) and offers to clean up before reinstalling.
* Configures bounded stop methods (`AppStopMethodConsole / Window /
  Threads = 5000 ms`, `AppKillProcessTree = 1`) so service restarts
  finish in 2-3 s instead of 15+ s.
* Captures NSSM-side stdout / stderr to
  `C:\rastatime\logs\apache-nssm-stdout.log` /
  `apache-nssm-stderr.log`.
  Apache's own `access_log` and `error_log` continue to live under
  `C:\Tools\Apache24\logs\` as configured by `httpd.conf`.

## 6. Verify

```powershell
Get-Service RASTATIME-APACHE              # Status: Running
Measure-Command { Restart-Service RASTATIME-APACHE }   # ~3-5 s typically
```

Browse to `http://localhost/` — same login page as in step 4, served
by the NSSM-managed instance.

## Removal

```powershell
powershell -ExecutionPolicy Bypass `
    -File C:\RASTATIME\infra\nssm\remove-apache.ps1
```

This removes the NSSM service entry only; binaries under
`C:\Tools\Apache24\` and `C:\Tools\PHP\` are untouched, as are the
Apache log files. Pass `-PurgeLogs` to also delete the NSSM-side
capture logs.
