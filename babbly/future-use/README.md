# メモ

## Metasploitの設定

1. Metasploit RPC serverの起動:

``` bash
msfrpcd -P your_password -S -a 127.0.0.1
```

- -P: RPCサーバーのパスワード設定
- -S: SSL無効化（テスト環境のみ）
- -a: リッスンアドレス

## 構造

``` bash
📂 Babbly/
├── 📄Pipfile
├── 📄Pipfile.lock
├── 📄README.md
├── 📂 babbly/
│   ├── 📂 en/
│   │   ├── 📄README.md
│   │   ├── ⚙️commands.txt
│   │   ├── ⚙️config_en.yaml
│   │   ├── 📄main_program.py
│   │   ├── 📂 model/
│   │   ├── ⚙️sop.json
│   │   ├── ⚙️targets.json
│   │   ├── 📄tts_speaker.py
│   │   └── 📄vosk_asr_module.py
│   ├── 📂 ja/
│   │   ├── 📄README.md
│   │   ├── ⚙️commands.txt
│   │   ├── ⚙️config_ja.yaml
│   │   ├── 📄main_program.py
│   │   ├── 📂 model/
│   │   ├── ⚙️opa.lst
│   │   ├── ⚙️sop.json
│   │   ├── ⚙️targets.json
│   │   ├── 📄voice_synthesizer.py
│   │   └── 📄vosk_asr_module.py
│   └── 📂 modules/
│       ├── 📄ipaddress_manager.py
│       ├── 📄network_scanner.py
│       └── 📄operation_manager.py
├── 📄babbly_en.py
├── 📄babbly_ja.py
└── 📂 images/
     ├── 📄Babbly_banner.png
     └── 📄Babbly_logo.JPG
```

### Japanese

``` bash
📂 Babbly/
├── 📂 images/
│   ├── 📄Babbly_banner.png
│   ├── 📄Babbly_logo.JPG
├── 📂 babbly/
│   ├── 📂 en/
│   ├── 📂 ja/
│   │   ├── 📄README.md
│   │   ├── ⚙️commands.txt
│   │   ├── ⚙️config_ja.yaml
│   │   ├── 📄main_program.py
│   │   ├── 📂 model/
│   │   ├── ⚙️opa.lst
│   │   ├── ⚙️sop.json
│   │   ├── ⚙️targets.json
│   │   ├── 📄voice_synthesizer.py
│   │   └── 📄vosk_asr_module.py
│   └── 📂 modules/
│       ├── 📄ipaddress_manager.py
│       ├── 📄network_scanner.py
│       └── 📄operation_manager.py
├── 📄babbly_en.py
├── 📄babbly_ja.py
├── 📄Pipfile
├── 📄Pipfile.lock
└── 📄README.md
```

## English

``` bash
📂 Babbly/
├── 📄Pipfile
├── 📄Pipfile.lock
├── 📄README.md
├── 📂 babbly/
│   ├── 📂 en/
│   │   ├── 📄README.md
│   │   ├── ⚙️commands.txt
│   │   ├── ⚙️config_en.yaml
│   │   ├── 📄main_program.py
│   │   ├── 📂 model/
│   │   ├── ⚙️sop.json
│   │   ├── ⚙️targets.json
│   │   ├── 📄tts_speaker.py
│   │   └── 📄vosk_asr_module.py
│   ├── 📂 ja/
│   └── 📂 modules/
│       ├── 📄ipaddress_manager.py
│       ├── 📄network_scanner.py
│       └── 📄operation_manager.py
├── 📄babbly_en.py
├── 📄babbly_ja.py
└── 📂 images/
     ├── 📄Babbly_banner.png
     └── 📄Babbly_logo.JPG
```
