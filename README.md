# Slack Exporter

Forked from:

https://github.com/chr1spy1/slack-export

Which is forked from:

https://github.com/andriuspetrauskis/slack-export

Original repo can be found here:

https://github.com/zach-snell/slack-export

## Description

The included script 'slack_export.py' works with a provided token to export Channels, Private Channels, Direct Messages and Multi Person Messages.

This script finds all channels, private channels and direct messages that your user participates in, downloads the complete history for those conversations and writes each conversation out to separate JSON files.

This user centric history gathering is nice because the official slack data exporter only exports public channels.

There may be limitations on what you can export based on the paid status of your slack account.

This use of the API is blessed by Slack : https://get.slack.help/hc/en-us/articles/204897248

"If you want to export the contents of your own private groups and direct messages
please see our API documentation."

This fork fixes some issues one the preceding fork, and adds step-by-step instructions.

Up-to-date step-by-step instructions can be found in [STEP-BY-STEP.md](STEP-BY-STEP.md).

## Token and Cookie

A guide to get your client token and cookie can be found on the ircslackd repo, see link below:

https://github.com/adsr/irslackd/wiki/IRC-Client-Config#xoxc-tokens

I'm not certain which cookies are necessary but there is a cookie table provided by slack here:

https://slack.com/intl/en-au/cookie-table#

## Dependencies

```
pip install -r requirements.txt
```

## Basic Usage
```
# Export all Channels and DMs
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..."

# List the Channels and DMs available for export
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --dryRun

# Prompt you to select the Channels and DMs to export
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --prompt

# Generate a `slack_export.zip` file for use with slack-export-viewer
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --zip slack_export
```

## Selecting Conversations to Export

This script exports **all** Channels and DMs by default.

To export only certain conversations, use one or more of the following arguments:

* `--publicChannels [CHANNEL_NAME [CHANNEL_NAME ...]]`\
Export Public Channels\
(optionally filtered by the given channel names)

* `--groups [GROUP_NAME [GROUP_NAME ...]]`\
Export Private Channels and Group DMs\
(optionally filtered by the given group names)

* `--directMessages [USER_NAME [USER_NAME ...]]`\
Export 1:1 DMs\
(optionally filtered by the given user names)

* `--prompt`\
Prompt you to select the conversations to export\
(Any channel/group/user names specified with the other arguments take precedence.)

* `--excludeArchived`\
Exclude any channels that have been archived

* `--excludeNonMember`\
Exclude any public channels for which the user is not a member

### Examples
```
# Export only Public Channels
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --publicChannels

# Export only the "General" and "Random" Public Channels
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --publicChannels General Random

# Export only Private Channels and Group DMs
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --groups

# Export only the "my_private_channel" Private Channel
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --groups my_private_channel

# Export only 1:1 DMs
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --directMessages

# Export only 1:1 DMs with jane_smith and john_doe
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --directMessages jane_smith john_doe

# Export only Public/Private Channels and Group DMs (no 1:1 DMs)
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --publicChannels --groups

# Export only 1:1 DMs with jane_smith and the Public Channels you select when prompted
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --directMessages jane_smith --publicChannels --prompt
```
This script is provided in an as-is state and I guarantee no updates or quality of service at this time.

## Downloading files and view them inside slack-export-viewer

To download all files hosted on Slack, you can specify the `--downloadSlackFiles` option. The files will be
downloaded into the `files.slack.com` local folder (inside the current working directory) and re-used for
all future export (files are compared for size before attempting to download them). This option will also
replace the URLs inside the export to point to the downloaded files assuming they are accessible with
`/static/files.slack.com/` from the slack-export-viewer webserver.

### Example including linking files.slack.com with `slack-export-viewer`
```
python slack_export.py --token xoxc-123... --cookie "b=...; d=...; x=..." --zip slack_export --downloadSlackFiles

# Clone slack-export-viewer from github
cd ..
git clone https://github.com/hfaran/slack-export-viewer.git

# Link the files.slack.com archive
ln -s ../../../slack-export/files.slack.com slack-export-viewer/slackviewer/static/files.slack.com

# Run slack-export-viewer with the archive previously created
./slack-export-viewer/app.py -z slack-export/slack_export.zip
```

# Recommended related libraries

This is designed to function with 'slack-export-viewer'.
  ```
  pip install slack-export-viewer
  ```

Then you can execute the viewer as documented
```
slack-export-viewer -z zipArchive.zip
```


