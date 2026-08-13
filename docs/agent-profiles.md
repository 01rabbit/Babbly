# Agent and environment profiles

Babbly is the offline agent framework. The operator-facing agent identity is selected by profile.

This separates framework identity from the name spoken by the user:

```text
Babbly Core
  -> Agent Profile
      -> identity / wake phrases
      -> persona / response style
      -> environment vocabulary
      -> read-only situation sources
  -> Intent / Policy / Authority
```

Profiles deliberately do **not** control execution authority.

## Built-in profiles

### `generic`

- display name: `Babbly`
- spoken name: `バブリー`
- wake phrase: `バブリー`
- persona: friendly, concise operator assistant
- vocabulary: `core`, `kali`
- situation source: none

### `kali`

- display name: `Babbly`
- spoken name: `バブリー`
- wake phrase: `バブリー`
- persona: focused operator
- vocabulary: `core`, `kali`
- situation source: none

### `azazel-edge`

- display name: `M.I.O`
- spoken name: `ミオ`
- wake phrase: `ミオ`
- persona: calm, tactical, short responses
- vocabulary: `core`, `azazel`
- situation source: read-only `azazel-edge`

The Azazel profile does not give M.I.O enforcement authority. It enables only the existing read-only situation adapter. Any future action request path remains separate and must preserve Azazel-Edge's deterministic decision authority.

## Selecting a profile

Mac-first launcher:

```bash
./run_babbly.sh ja --profile generic
./run_babbly.sh ja --profile kali
./run_babbly.sh ja --profile azazel-edge
```

Environment variable:

```bash
BABBLY_PROFILE=azazel-edge ./run_babbly.sh ja
```

Precedence is:

```text
--profile
  > BABBLY_PROFILE
  > PROFILE in config_ja.yaml
  > generic
```

List available profiles:

```bash
python babbly_ja.py --list-profiles
```

## Local/custom profile directory

Set `BABBLY_PROFILE_DIR` to a local directory containing profile JSON files. Profile names are restricted to safe filename characters, and path traversal is rejected.

```bash
BABBLY_PROFILE_DIR="$HOME/.config/babbly/profiles" \
BABBLY_PROFILE=my-agent \
./run_babbly.sh ja
```

This allows local persona variants without committing them to the repository.

## Profile schema

```json
{
  "id": "azazel-edge",
  "identity": {
    "id": "mio",
    "display_name": "M.I.O",
    "spoken_name": "ミオ",
    "wake_phrases": ["ミオ"],
    "language": "ja"
  },
  "persona": {
    "tone": "calm_tactical",
    "style": "tactical_concise",
    "verbosity": "short",
    "startup_phrase": "ミオ、起動。Azazel-Edge支援を開始します。",
    "acknowledgement": "はい",
    "command_prompt": "指示をどうぞ",
    "unknown_prompt": "指示を特定できません。再度お願いします",
    "shutdown_phrase": "ミオを終了します。",
    "introduction": [
      "ミオです。Azazel-Edgeの状況確認とオペレーター支援を行います",
      "判断と実行権限はAzazel-Edge側の決定論的ポリシーに従います"
    ]
  },
  "environment": {
    "type": "azazel-edge",
    "vocabulary_packs": ["core", "azazel"],
    "situation_sources": ["azazel-edge"]
  }
}
```

## Authority boundary

Profile projection is intentionally narrow. It may change:

- agent identity
- wake phrases
- response/persona wording
- vocabulary packs
- approved read-only situation sources

It cannot change:

- `DRY_RUN`
- intent execute/clarify thresholds
- command or SOP registries
- confirmation policy
- execution authority
- Azazel-Edge decision authority

Persona therefore changes **how the agent presents itself**, not **what the agent is authorized to do**.

## Wake backends

The ASR-compatible wake backend supports multiple profile wake phrases. For KWS/sherpa-onnx deployments, the selected local keyword model/file still has to contain a compatible keyword. Selecting `azazel-edge` changes the intended wake identity to `ミオ`, but it does not dynamically retrain or download a KWS model.
