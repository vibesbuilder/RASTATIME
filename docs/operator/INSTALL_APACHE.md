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

1. Install the latest **Microsoft Visual C++ Redistributable (x64)**
   first.  The Apache Lounge builds (currently the VS18 build) and
   PHP 8.5 NTS x64 (VS17 build) are linked against it — without it `httpd.exe`
   and `php-cgi.exe` exit **silently**, with no error message and
   nothing in the logs.
2. Download Apache 2.4 (Win64) — the [Apache Lounge
   distribution](https://www.apachelounge.com/download/) is the
   standard choice.  `mod_fcgid` is a **separate** module zip on the
   same download page — fetch it too and drop `mod_fcgid.so` into
   `modules\`.
3. Extract to `C:\Tools\Apache24\` (the install scripts assume this
   path; pass `-ApacheRoot` to `install-apache.ps1` if you put it
   elsewhere).
4. Install PHP 8.5 (Non-Thread-Safe / x64) to `C:\Tools\PHP\`.

After extracting, the layout should be:

    C:\Tools\Apache24\
        bin\httpd.exe
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

### Required modules

```apache
LoadModule rewrite_module    modules/mod_rewrite.so
LoadModule proxy_module      modules/mod_proxy.so
LoadModule proxy_http_module modules/mod_proxy_http.so
```

`mod_rewrite` drives the ZF1 front-controller rules below;
`mod_proxy` / `mod_proxy_http` serve the `/api/v2/` reverse proxy to
the Django API.  (`mod_fcgid` is loaded in its own section further
down.)

### DocumentRoot pointed at the RASTATIME frontend

```apache
DocumentRoot "C:/RASTATIME/frontend/legacy/public"
<Directory "C:/RASTATIME/frontend/legacy/public">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted

    # ZF1 front controller: send every request that is not an
    # existing file, symlink, or directory to index.php.
    RewriteEngine On
    # Re-export the Authorization header into the FastCGI env.
    # mod_fcgid strips it otherwise, which breaks Basic-auth
    # endpoints (e.g. the Icecast stream_auth listener-allow hook).
    RewriteRule ^ - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
    RewriteCond %{REQUEST_FILENAME} -s [OR]
    RewriteCond %{REQUEST_FILENAME} -l [OR]
    RewriteCond %{REQUEST_FILENAME} -d
    RewriteRule ^.*$ - [NC,L]
    RewriteRule ^.*$ index.php [NC,L]
</Directory>
```

The `HTTP_AUTHORIZATION` line is not optional: without it the
frontend appears to work, but every endpoint relying on HTTP Basic
auth silently receives no credentials.

### mod_fcgid + PHP

```apache
LoadModule fcgid_module modules/mod_fcgid.so

<IfModule fcgid_module>
    FcgidInitialEnv PHPRC "C:/Tools/PHP"
    FcgidWrapper "C:/Tools/PHP/php-cgi.exe" .php
    AddHandler fcgid-script .php
    FcgidMaxRequestLen 536870912  # 512 MiB = PHP post_max_size; the UI shows that limit
    FcgidConnectTimeout 20
    FcgidIOTimeout 120
    # RASTATIME: keep the fcgid pool small and short-lived so PHP
    # workers get recycled regularly.  Defaults are 300 / 3600 s.
    FcgidIdleTimeout 60
    FcgidProcessLifeTime 600
</IfModule>
```

### .htaccess

The frontend ships **no** `.htaccess` files — the front-controller
rewrite lives directly in `httpd.conf` (see above), and production
keeps the stock `<Directory /> AllowOverride none`.  The
`AllowOverride All` inside the DocumentRoot `<Directory>` block is
sufficient.

### Reverse proxy to the RASTATIME API (server scope)

At **server scope** (not inside any `<Directory>` or `<VirtualHost>`):

```apache
ProxyPreserveHost On
ProxyPass        /api/v2/   http://127.0.0.1:8765/api/v2/
ProxyPassReverse /api/v2/   http://127.0.0.1:8765/api/v2/
ProxyPass        /api-auth/ http://127.0.0.1:8765/api-auth/
ProxyPassReverse /api-auth/ http://127.0.0.1:8765/api-auth/
```

Port **8765** is the RASTATIME API (`RASTATIME-API` service).  Do
not use 8000 — that port belongs to Icecast.  `ProxyPreserveHost On`
keeps the original `Host:` header so the API builds correct absolute
URLs.

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

### 3.1 CA bundle for outbound HTTPS (podcast feeds)

PHP on Windows ships **without** a CA bundle.  Every outbound HTTPS request
from the legacy frontend - above all the podcast RSS feeds read with
SimplePie - then fails with `cURL error 60: SSL certificate ... unable to
get local issuer certificate`, and the podcast editor shows an empty
episode list (plus a DataTables "Requested unknown parameter 'guid'"
warning).  Found 2026-09-16 on the studio machine: no podcast episode had
been fetched since the migration.

Put a bundle next to PHP and point both cURL and the OpenSSL stream
wrapper at it:

```powershell
# either the Mozilla bundle from curl.se ...
Invoke-WebRequest https://curl.se/ca/cacert.pem -OutFile C:\Tools\PHP\cacert.pem
# ... or the copy that ships with the RASTATIME venv (certifi)
Copy-Item C:\RASTATIME\.venv\Lib\site-packages\certifi\cacert.pem C:\Tools\PHP\cacert.pem
```

`C:\Tools\PHP\php.ini` (both keys exist commented out):

```ini
curl.cainfo    = "C:\Tools\PHP\cacert.pem"
openssl.cafile = "C:\Tools\PHP\cacert.pem"
```

Restart `RASTATIME-APACHE` (`nssm restart RASTATIME-APACHE`).  Verify with
the same PHP binary Apache uses:

```powershell
C:\Tools\PHP\php.exe -r "var_dump((bool) file_get_contents('https://cba.media/'));"
```

must print `bool(true)`.  Refresh the bundle about once a year (curl.se
and certifi publish new ones several times a year).

### 3.2 PHP 8.5 settings

PHP 8.5 (production since 2026-10-22) needs these `php.ini` changes on top
of the stock `php.ini-production`:

```ini
; OPcache is always loaded in 8.5.  Keep it off: legacy PHP edits must be
; live on the next request (no revalidate delay).
opcache.enable = 0
; PHP2Shell hardening (CVE-2026-109618/-109619), set 2026-10-21; the legacy
; uploader does not use upload progress.
session.upload_progress.enabled = Off
```

Leave these keys **unset** (comment them out if an older `php.ini` is
carried over): `session.sid_length` and `session.sid_bits_per_character`
are deprecated since 8.4 (a deprecation notice at every start), and
`disable_classes` no longer exists in 8.5.

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
  finish in ~5 s instead of 15+ s (see 5.2).  (`AppKillProcessTree` needs an
  NSSM 2.24-101 pre-release; NSSM 2.24 does not know it and always
  kills the process tree - see 5.1 for what it misses.)
* Captures NSSM-side stdout / stderr to
  `C:\rastatime\logs\apache-nssm-stdout.log` /
  `apache-nssm-stderr.log`.
  Apache's own port-80 logs are daily `rotatelogs` slices under
  `C:\RASTATIME\logs\` since 2026-10-14 (`http-error-YYYYMMDD.log`,
  `http-access-YYYYMMDD.log`, swept by the log janitor like the HTTPS
  slices).  `httpd.conf`:

  ```
  ErrorLog  "|C:/Tools/Apache24/bin/rotatelogs.exe -l C:/RASTATIME/logs/http-error-%Y%m%d.log 86400"
  CustomLog "|C:/Tools/Apache24/bin/rotatelogs.exe -l C:/RASTATIME/logs/http-access-%Y%m%d.log 86400" common
  ```

  Before that, `C:\Tools\Apache24\logs\error_log` grew to 890 MB
  (PHP deprecation flood until 2026-10-09) and, because Apache keeps
  it open, could never be rotated.

### 5.1 Orphaned php-cgi.exe after a stop (reaper task)

NSSM 2.24 (the version on the studio machine) stops Apache with Ctrl+C
and then kills the process tree it can still see.  The httpd child
process has usually exited by then, and its mod_fcgid `php-cgi.exe`
children are no longer reachable through their parent: they stay
behind as orphans (2026-10-21: ten of them, the oldest 13 days).  They
serve nothing but keep memory, the old `php.ini` and file locks on
`C:\Tools\PHP` - a PHP update cannot swap the folder while they run.
(`AppKillProcessTree` does not help: NSSM 2.24 does not know the
setting, and event hooks only came with the 2.24-101 pre-releases.)

Since 2026-10-22 the scheduled task **RASTATIME-PhpCgiReaper** cleans
up.  It runs as SYSTEM whenever NSSM logs a START/STOP control (event
1040) or a start of httpd (1008, also after a crash restart) for
`RASTATIME-APACHE` in the Application log, waits until the service has
left the *Pending state and stops every `php-cgi.exe` from
`C:\Tools\PHP` without a live httpd parent.  The workers of a running
Apache are never touched.  Register it once, elevated:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
    -File C:\RASTATIME\infra\scripts\register-php-cgi-reaper.ps1
```

Each run logs one line to `C:\RASTATIME\logs\php-cgi-reaper.log`
(`trigger=event service=Stopped kept=0 orphans=3 stopped: …`).
A manual run is harmless at any time:
`infra\scripts\rt-php-cgi-reaper.ps1 [-DryRun]`.

### 5.2 Stop time and the restart script

NSSM's Ctrl+C does not shut Apache down in an orderly way here: right
after it the access log goes silent, httpd keeps running until the
console timeout expires, and NSSM then terminates it.  Until 2026-10-22
the studio machine had `AppStopMethodConsole = 30000` (origin unknown,
the install script sets 5000), so every stop took ~30 s; it is 5000
again since then.  Whether an orderly stop is possible at all (for
example with `AppNoConsole = 0`) is a BACKLOG item for a probe instance.

A `nssm start` issued while the service is still stopping fails with
"Es wird bereits eine Instanz des Dienstes ausgeführt" / "An instance
of the service is already running", and Apache then stays down.  Use
the restart script instead, in an elevated PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
    -File C:\RASTATIME\infra\scripts\rt-apache-restart.ps1   # or -StopOnly / -StartOnly
```

It runs `httpd -t` first (a broken config stops nothing, exit 2), waits
until the service is really Stopped, reports and stops orphaned
php-cgi.exe, starts, waits for Running and checks that
`https://<RT_PUBLIC_HOST>/login` answers 200 through 127.0.0.1.  One line
per run goes to `C:\RASTATIME\logs\apache-restart.log`.  `-StopOnly`
is the stop step of a PHP update (folder swap), `-StartOnly` the start
step afterwards.

## 6. Verify

```powershell
Get-Service RASTATIME-APACHE              # Status: Running
powershell -NoProfile -ExecutionPolicy Bypass -File C:\RASTATIME\infra\scripts\rt-apache-restart.ps1
# expected: "stopped after ~5 s", reaper line, "login: 200", "OK (restart)"
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
