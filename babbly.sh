#!/bin/bash

# 引数チェック -Argument Checking-
if [ "$1" == "-l" ]; then
    if [ "$2" == "en" ]; then
        echo "Start Babbly in English mode."
        clear
        python babbly_en.py
    elif [ "$2" == "ja" ]; then
        echo "Babblyを日本語モードで起動します。"
        clear
        python babbly_ja.py
    else
        echo "Error: Invalid language option."
        echo "Usage: $0 -l <en|ja>"
    fi
else
    echo "Error: Argument is incorrect."
    echo "Usage: $0 -l <en|ja>"
fi