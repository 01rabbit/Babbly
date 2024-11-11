# Babbly

## 日本語モード

![Babbly banner](../../images/Babbly_banner.png)
**Beautiful** in flaws, **Artificial incompetence** remains our **Buddy**, **Bypassing** threats while **Leaving** us **Yearning** for growth.
*(不完全さの中に美しく、人工無能は私たちの仲間であり続け、脅威を回避しながら、成長への憧れを残していく)*

---

## ツールの詳細

「**Babbly**」は、AIではなく「**人工無能**」を搭載した、独自のペネトレーションテスト支援ツールです。完全オフラインかつオンプレミスで動作するため、インターネット接続が不要。機密性が求められる環境や特殊な制約があるシステムでも、リスクなく導入できる柔軟性を備えています。以下、Babblyの主な特徴と活用できる環境をご紹介します。

### 主な特徴とアピールポイント

1. 人工無能による直感的対話型操作
   BabblyはAIではなく「人工無能」を採用。これによりシンプルな対話型インターフェースを実現し、学習や精度に依存しない安定した操作が可能です。複雑な調整なしで初心者でも使いやすい設計になっています。
2. SOP（標準操作手順）に基づいた柔軟なテスト実行
   BabblyはSOPに基づき、オペレーション単位でユーザーが実行したい手順を登録可能です。これにより、ユーザーは企業のレギュレーションに沿ったテストを実行でき、カスタマイズされたシナリオ設定が可能です。
3. アイズフリー・ハンズフリー操作
   音声認識機能を活用し、音声指示だけでテスト実行が可能。画面を注視する必要がないため、他の作業と並行して効率的にテストが進行します。
4. シンプルなターゲットと攻撃シナリオ設定
   簡単な操作でターゲットや攻撃シナリオを指定でき、初心者でも柔軟にペネトレーションテストを実施できます。
5. 結果の即時通知
   テスト結果は音声や画面表示で即座に確認可能。現場での状況把握がスムーズに行えます。
6. 高コストパフォーマンスと環境適応性
   オフラインで動作するため、AI搭載のオンラインツールと比較してコストが低く、特殊環境でも柔軟に導入が可能です。

### 適応環境と活用例

Babblyは以下のような、インターネット接続が制限される環境でも柔軟に対応します：  

- **隔離ネットワーク環境**：高セキュリティ施設や軍事施設、原子力発電所の制御システムなど、外部ネットワークと遮断された環境でのテスト。
- **フィールドでの即時セキュリティ評価**：遠隔地や災害現場での迅速なセキュリティ評価。
- **EMP耐性テスト環境**：EMPシールドルーム内で、極限状況下でのインフラ耐性確認。
- **航空機・船舶のオンボードシステム**：飛行中や航行中に外部ネットワークに接続できない状況でのセキュリティチェック。
- **オフグリッドシステムの評価**：独立したマイクログリッドや遠隔地の通信基地局などのセキュリティテスト。
- **プライバシー重視の環境**：データ流出を完全に防ぎたい医療機関や金融機関の内部評価。
- **産業用制御システム（ICS）**：工場やインフラ施設で、外部から隔離された制御システムのテスト。
- **電波管制区域でのテスト**：電波が制限された区域での物理接続を使ったセキュリティ評価。
- **災害時のネットワーク評価**：災害時に臨時ネットワークを使ったセキュリティチェック。
- **教育機関でのトレーニング**：オフラインで実践的なトレーニングを提供し、安全に学習できる環境を構築。
- **コンプライアンス要件の厳しい環境**：HIPAAやPCI DSSに準拠した医療システムや金融システムの評価。
- **スタンドアロンIoTデバイスのテスト**：インターネット接続が不要な独立型IoTデバイス（産業用センサーなど）のセキュリティチェック。

### AI搭載型ツールとの差別化

Babblyは、AIツールが求めるオンライン接続やデータ依存を排除し、低コストで高信頼性を提供します。AI特有の精度や学習結果に頼らず、SOPに基づく操作で企業基準に応じたテストが可能です。高セキュリティ環境や特殊な制約がある場でも、柔軟で効率的なテストが行えます。

---

## Setup

1. 依存関係のインストール  
   `open_jtalk`、`mecab`、`aplay`、および必要な辞書データや音声データをインストールします。  

    ``` bash
    sudo apt install open-jtalk open-jtalk-mecab-naist-jdic hts-voice-nitech-jp-atr503-m001 aplay
    ```

2. ディレクトリの配置と確認  
   辞書ディレクトリ：`/var/lib/mecab/dic/open-jtalk/naist-jdic/`  
   音声ファイル：`/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice`  

3. voskモデルのダウンロード  

   | Model | Size | Word error rate/Speed | Notes | License |
   | ---- | ---- |---- | ---- |---- |
   | [vosk-model-small-ja-0.22](https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip) | 48M | 9.52(csj CER) 17.07(ted10k CER) | Lightweight wideband model for Japanese | Apache 2.0 |
   | [vosk-model-ja-0.22](https://alphacephei.com/vosk/models/vosk-model-ja-0.22.zip) | 1Gb | 8.40(csj CER) 13.91(ted10k CER) | Big model for Japanese| Apache 2.0 |

4. ダウンロードしたvoskモデルを`model`とリネームして`Babbly/babbly/ja/`直下に配置する。  

   ``` bash
   mv vosk-model-ja-0.22 /home/kali/Babbly/babbly/ja/model
   ```

5. 構成ファイル（`babbly/ja/config_en.yaml`）を開き、**WAKEUP_PHRASE**と**EXIT_PHRASE**を編集する。それ以外の項目は変更をしない。  
   *ウェイクアップフレーズは、呼びやすくて、認識されやすければ何でも大丈夫。好きな名前を設定してくれ*

   ``` yaml
   WAKEUP_PHRASE: "バブリー"
   EXIT_PHRASE: "終了"
   COMMANDS_PATH: "babbly/ja/commands.txt"
   TARGETS_PATH: "babbly/ja/targets.json"
   SOP_PATH: "babbly/ja/sop.json"
   MODEL_PATH: "babbly/ja/model"
   ```