#!/usr/bin/bash

TOKEN="%%INSTALLATION_PATH%%"
REPLACEMENT=`pwd`

SOURCE_SCRIPT="dnsfilter.service"
DESTINATION_SCRIPT="/etc/systemd/system/dnsfilter.service"

script=$(<"$SOURCE_SCRIPT")

# Replace the path token with the desired path
content="${script//$TOKEN/$REPLACEMENT}"

echo "$content" > "$DESTINATION_SCRIPT"
chmod +x "$DESTINATION_SCRIPT"

systemctl daemon-reload
