# Exporting Message From Slack - Step-by-Step

## Install

1. Create and move into a destination directory for the archive and downloaders -
   
1. Clone the "slack-export" repo -

   ```
   git clone https://github.com/trianglee/slack-export.git
   ```
   
1. Create virtualenv -

   Windows -

   ```
   py -3 -m virtualenv venv
   ```

   Linux -

   ```
   python3 -m virtualenv venv
   ```
   
1. Install requirements -

   Windows -

   ```
   venv\scripts\pip install -r slack-export\requirements.txt
   ```

   Linux -

   ```
   venv/bin/pip install -r slack-export/requirements.txt
   ```

1. Windows only - install Windows ncurses package -

   Windows -

   ```
   venv\scripts\pip install install windows-curses
   ```

1. Windows only - increase maximal path length limitation.

   Done by adding a registry key named `LongPathsEnabled` of type
   `DWORD` and value `1`, under 
   `Computer\HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`.

   This *might* be needed if there are long file names in static files
   stored by Slack.

   See more details in https://docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation.

1. Install "slack-export-viewer" -

   Windows -

   ```
   venv\scripts\pip install git+https://github.com/trianglee/slack-export-viewer.git
   ```

   Linux -

   ```
   venv/bin/pip install git+https://github.com/trianglee/slack-export-viewer.git
   ```

## Obtain Token and Cookies

1. In Firefox, open https://pelioniot.slack.com/customize.

1. Sign in with SSO (if needed).

1. F12, for Web Developer Tools.

1. Select the "Console" tab.

1. Type the command -

   `TS.boot_data.api_token`

   (you might need to confirm copy&paste to Firefox)
   
1. Copy the value printed. It should be of the form `"xoxc-..."`.  
   This is your token.

1. Set the token as an environment variable -

   Windows -

   ```
   set SLACK_TOKEN="xoxc-..."
   ```

   Linux -

   ```
   SLACK_TOKEN="xoxc-..."
   ```
   or
   ```
   export SLACK_TOKEN="xoxc-..."
   ```

1. Select the "Storage" tab.

1. Find the "d" cookie, and copy its value. Add a "d=" at the beginning, so it would
   end up being of the form `d=CD0I...`.  
   This is your cookie.

1. Set the cookie as an environment variable -

   Windows -

   ```
   set SLACK_COOKIE="d=CD0I..."
   ```

   Linux -

   ```
   SLACK_COOKIE="d=CD0I..."
   ```
   or
   ```
   export SLACK_COOKIE="d=CD0I..."
   ```

## Run

1. Perform a dry-run, without saving anything, **using the token and the cookie from above**,
   to verify authentication is successful -

   Windows -

   ```
   venv\scripts\python slack_export.py --token %SLACK_TOKEN% --cookie %SLACK_COOKIE% --dryRun 
   ```

   Linux -

   ```
   venv/bin/python slack_export.py --token $SLACK_TOKEN --cookie $SLACK_COOKIE --dryRun 
   ```

1. Export all direct-messages and all static files (see [Exporting Options](#exporting-options) for other options) -

   Windows -

   ```
   venv\scripts\python slack_export.py --token %SLACK_TOKEN% --cookie %SLACK_COOKIE%  --directMessages --downloadSlackFiles 
   ```

   Linux -

   ```
   venv/bin/python slack_export.py \
     --token $SLACK_TOKEN --cookie $SLACK_COOKIE \
     --directMessages \
     --downloadSlackFiles 
   ```

   The messages are exported to a directory of the form `YYYYMMDD-HHMMSS-slack_export`.
   We shall call it EXPORT-DIRECCTORY.

1. Copy or link the static Slack files to the viewer directory inside the virtual environment -

   Windows (copy) -

   ```
   robocopy /mir files.slack.com venv\Lib\site-packages\slackviewer\static\files.slack.com\
   ```

   Linux (link) -

   ```
   ln -s $(pwd)/files.slack.com venv/lib/python3*/site-packages/slackviewer/static
   ```

1. Run viewer (a browser window automatically opens) -

   Windows -

   ```
   venv\scripts\slack-export-viewer -z <EXPORT-DIRECTORY>
   ```

   Linux -

   ```
   venv/bin/slack-export-viewer -z <EXPORT-DIRECTORY>
   ```

### Exporting Options

* To export all public channels, use `--publicChannels`.
* To export all private channels and group messages, use `--groups`.
* To export all direct messages, use `--directMessages`.
* To export specific channels or direct messages, add a list following each parameter 
  (like `--directMessages some.user1 some.user2 --groups channel1 channel2`).
