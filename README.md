# Babbly

![Babbly banner](images/Babbly_banner.png)

## Overview of Tools

**Babbly** is a penetration testing support tool featuring **Artificial Incompetence**. Instead of relying on cloud AI, it achieves intuitive dialogue-based operation through natural language processing and voice recognition. Supporting eyes-free and hands-free operation, security tests can be efficiently performed alongside other tasks since they can be executed through voice commands alone without checking the screen. With its human-like conversational interface, it's easy for beginners to use and offers high flexibility.

The current next-generation work is evolving Babbly into a reusable **offline voice-agent foundation**. The migration keeps the original deterministic/SOP model while adding pluggable offline ASR, Japanese normalization, domain vocabulary packs, confidence-aware intent routing, explicit clarification, and a dry-run validation mode. See [`docs/offline-asr.md`](docs/offline-asr.md).

「**Babbly**」は**人工無能**（**Artificial Incompetence**）を特徴とするペネトレーションテスト支援ツールです。クラウドAIに依存せず、自然言語処理と音声認識により直感的な対話型操作を実現します。アイズフリー・ハンズフリーに対応し、音声指示だけでテストを実行できるため、画面確認なしで他の作業と並行して効率的なセキュリティテストが可能です。

現在は次世代化として、Babblyを再利用可能な**オフライン音声エージェント基盤**へ進化させています。従来の決定論的なSOPモデルを維持しつつ、差し替え可能なオフラインASR、日本語正規化、ドメイン語彙、信頼度ベースのIntent判定、明示的な聞き返し、DRY RUN検証を追加する方針です。詳細は [`docs/offline-asr.md`](docs/offline-asr.md) を参照してください。

## Development workflow

Babbly is developed **MacBook-first**. The reference development host is Apple Silicon macOS; Raspberry Pi is the later deployment/hardware-validation target. Core logic, NLU, policy, adapters, dry-run behavior, and development benchmarks should pass on the Mac before Pi-specific audio/resource validation.

```bash
python3 -m venv .venv
source .venv/bin/activate
./run_babbly.sh test
./run_babbly.sh ja
```

See [`docs/development-macos.md`](docs/development-macos.md) for setup, the Mac-to-Pi promotion gate, and the platform-aware development benchmark flow.

### [日本語モード](babbly/ja/README.md)

日本語を使用するユーザは、こちらのリンクをご確認ください。

### [English mode](babbly/en/README.md)

For users who use English, please check this link.

---

## Babbly's image character

![logo](images/Babbly_logo.JPG)
