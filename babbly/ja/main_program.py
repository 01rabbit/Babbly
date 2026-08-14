#!/usr/bin/python3
import argparse
import logging
import sys

import pyfiglet

from babbly.adapters.factory import create_situation_engine
from babbly.asr import create_asr
from babbly.core.engine import SituationEngine
from babbly.core.operator_intent import OperatorIntent, SourceModality
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.render import (
    render_recommendation_for_attention,
    render_situation_for_attention,
)
from babbly.core.runtime_factory import build_operator_runtime
from babbly.core.situation import SituationSnapshot
from babbly.ja.japanese_tts import Japanese_TTS
from babbly.modules.commands_manager import CommandManager
from babbly.modules.ipaddress_manager import IPAddressManager
from babbly.modules.network_scanner import NetworkScanner
from babbly.modules.operation_manager import OperationManager
from babbly.modules.utils import analyze_text, assist_command_mode, load_config, select_target
from babbly.nlu.japanese import IntentResolver, normalize_japanese
from babbly.nlu.policy import Decision, IntentPolicy
from babbly.nlu.vocabulary import build_aliases
from babbly.profiles import apply_profile_to_config, list_profiles, load_profile, resolve_profile_name
from babbly.wake import create_wake_detector


tts = Japanese_TTS()
lang_ja = 1
situation_engine = SituationEngine()
operator_runtime = OperatorIntentRuntime(situation_engine)
agent_profile = None


def set_situation_engine(engine):
    """Inject read-only situation adapters without coupling the voice loop to Azazel."""
    global situation_engine, operator_runtime
    situation_engine = engine
    operator_runtime.situation_engine = engine


def set_agent_profile(profile):
    """Set identity/persona metadata; this does not grant execution authority."""
    global agent_profile
    agent_profile = profile


def configure_operator_runtime(config, engine):
    """Rebuild the shared operator runtime from config.

    Activates the controlled write path (#18) only when the config enables it;
    otherwise the runtime keeps the read/confirmation-only behaviour. Binds the
    read-only situation engine.
    """
    global situation_engine, operator_runtime
    situation_engine = engine
    operator_runtime = build_operator_runtime(config, engine)


def set_globals(config):
    global WAKEUP_PHRASE, EXIT_PHRASE, COMMANDS_PATH, TARGETS_PATH, SOP_PATH, DRY_RUN
    global intent_resolver, intent_policy, domain_aliases, operator_runtime
    WAKEUP_PHRASE = config.get("WAKEUP_PHRASE")
    EXIT_PHRASE = config.get("EXIT_PHRASE")
    COMMANDS_PATH = config.get("COMMANDS_PATH")
    TARGETS_PATH = config.get("TARGETS_PATH")
    SOP_PATH = config.get("SOP_PATH")
    DRY_RUN = bool(config.get("DRY_RUN", False))
    operator_runtime.dry_run = DRY_RUN

    packs = config.get("DOMAIN_VOCABULARY", ["core", "kali"])
    domain_aliases = build_aliases(*packs)
    intent_resolver = IntentResolver(domain_aliases)
    intent_policy = IntentPolicy(
        execute_threshold=float(config.get("INTENT_EXECUTE_THRESHOLD", 0.90)),
        clarify_threshold=float(config.get("INTENT_CLARIFY_THRESHOLD", 0.60)),
    )


def _persona_value(field, fallback):
    if agent_profile is None:
        return fallback
    value = getattr(agent_profile.persona, field, None)
    return value or fallback


def _voice_intent(intent_id, *, confidence=None, parameters=None, target_ref=None, context_ref=None):
    return OperatorIntent(
        intent_id=intent_id,
        source_modality=SourceModality.VOICE,
        confidence=confidence,
        parameters=parameters or {},
        target_ref=target_ref,
        context_ref=context_ref,
    )


def introduce_agent():
    print("自己紹介をします")
    if agent_profile is None:
        tts.say("私はバブリー。ミスターラビットによって開発された人工無能システムです")
        tts.say("私の役割は、ペネトレーションテストにおいて、あなたをサポートすることです")
        return
    for sentence in agent_profile.persona.introduction:
        tts.say(sentence)


def listen_result(asr):
    result = asr.listen()
    if result.is_empty:
        return result
    confidence = "unknown" if result.confidence is None else f"{result.confidence:.2f}"
    logging.info("ASR backend=%s confidence=%s text=%s", result.backend, confidence, result.text)
    return result


def ask_confirmation(asr, prompt):
    tts.say(prompt + "。よろしければ、はい。中止する場合は、いいえ、と答えてください")
    result = listen_result(asr)
    normalized = normalize_japanese(result.text, domain_aliases)
    if any(token in normalized for token in ("はい", "実行", "お願いします", "よし")):
        return True
    if any(token in normalized for token in ("いいえ", "中止", "やめ", "キャンセル")):
        return False
    tts.say("確認できなかったため実行しません")
    return False


def report_dry_run(action, detail=""):
    message = f"DRY RUN: {action}"
    if detail:
        message += f" {detail}"
    logging.info(message)
    print(message)
    tts.say("ドライランのため、実際の処理は実行しません")


def speak_situation_report(confidence=None):
    result = operator_runtime.submit(_voice_intent("situation.report", confidence=confidence))
    snapshot = SituationSnapshot.from_dict(result.payload.get("snapshot", {}))
    # Render at the current operator-attention density (NORMAL/HEADS_UP/CRITICAL).
    message = render_situation_for_attention(snapshot, operator_runtime.attention.state)
    print(message)
    tts.say(message)


def speak_recommendation(confidence=None):
    result = operator_runtime.submit(_voice_intent("recommendation.explain", confidence=confidence))
    snapshot = SituationSnapshot.from_dict(result.payload.get("snapshot", {}))
    message = render_recommendation_for_attention(snapshot, operator_runtime.attention.state)
    print(message)
    tts.say(message)


# Operator-controlled attention mode switch via voice. This changes presentation
# density only; it never changes execution authority or confirmation policy.
_ATTENTION_PHRASES = (
    ("ヘッドアップ", "heads_up"),
    ("ヘッズアップ", "heads_up"),
    ("クリティカル", "critical"),
    ("ノーマル", "normal"),
    ("通常モード", "normal"),
)
_ATTENTION_LABELS = {"normal": "通常", "heads_up": "ヘッドアップ", "critical": "クリティカル"}


def maybe_set_attention(normalized):
    """Handle a spoken attention-mode change; return True if one was applied."""
    for phrase, state in _ATTENTION_PHRASES:
        if phrase in normalized:
            result = operator_runtime.submit(
                _voice_intent("attention.set", parameters={"state": state})
            )
            if result.status == "ok":
                message = f"注意モードを{_ATTENTION_LABELS[state]}に切り替えました"
                print(message)
                tts.say(message)
                return True
    return False


def wait_for_wakeup(wake_detector, asr):
    """Wait at the low-authority wake gate, then enter normal ASR command mode."""
    try:
        while True:
            result = wake_detector.wait()
            if not result.triggered:
                continue
            confidence = "unknown" if result.confidence is None else f"{result.confidence:.2f}"
            logging.info(
                "wake triggered backend=%s keyword=%s confidence=%s",
                result.backend,
                result.keyword,
                confidence,
            )
            print(f"ウェイクアップ検知: {result.keyword} ({result.backend})")
            tts.say(_persona_value("acknowledgement", "はい、ボス"))
            listen_for_command(asr)
    except KeyboardInterrupt:
        print("\nCtrl+Cが押されました。プログラムを終了します。")
        logging.info("システム終了")
        raise SystemExit(0)


def listen_for_command(asr):
    cmd_mgr = CommandManager(COMMANDS_PATH)
    command_dict = cmd_mgr.get_search_dict()
    ip_mgr = IPAddressManager(TARGETS_PATH)
    op_mgr = OperationManager(SOP_PATH)

    try:
        print(f"コマンドを入力してください（終了するには {EXIT_PHRASE} を言ってください）")
        tts.say(_persona_value("command_prompt", "指示をどうぞ"))

        while True:
            asr_result = listen_result(asr)
            if asr_result.is_empty:
                continue

            recog_text = asr_result.text
            print(f"認識テキスト: {recog_text}")
            intent = intent_resolver.resolve(recog_text)
            normalized = intent.normalized_text
            user_order = analyze_text(normalized)
            policy = intent_policy.evaluate(intent, asr_result.confidence)
            logging.info(
                "intent=%s intent_confidence=%.2f decision=%s reason=%s normalized=%s",
                intent.name,
                intent.confidence,
                policy.decision.value,
                policy.reason,
                normalized,
            )

            if intent.name == "system.exit" or normalize_japanese(EXIT_PHRASE, domain_aliases) in normalized:
                if policy.decision == Decision.REJECT:
                    tts.say("終了指示を確認できませんでした")
                    continue
                print("終了フレーズ認識。処理を終了します。")
                tts.say(_persona_value("shutdown_phrase", "システムを終了します。お疲れ様でした。"))
                raise SystemExit(0)

            # Presentation-only attention switch. No confidence gate: it grants
            # no execution authority and only changes rendering density.
            if maybe_set_attention(normalized):
                break

            if intent.name != "unknown" and policy.decision == Decision.CLARIFY:
                if not ask_confirmation(asr, f"{recog_text}、という指示でよろしいですか"):
                    continue
                policy = type(policy)(Decision.EXECUTE, "operator confirmed")

            if intent.name != "unknown" and policy.decision == Decision.REJECT:
                tts.say("認識の確信度が不足しています。もう一度お願いします")
                continue

            if intent.name == "system.introduce":
                introduce_agent()
                break

            if intent.name == "situation.report":
                speak_situation_report(intent.confidence)
                break

            if intent.name == "recommendation.explain":
                speak_recommendation(intent.confidence)
                break

            if intent.name == "network.scan":
                if DRY_RUN:
                    report_dry_run("network.scan")
                else:
                    NetworkScanner().network_scan(tts, ip_mgr, lang_ja)
                break

            if intent.name == "target.show":
                target_name, target_ip = ip_mgr.find_target_ip(user_order)
                if target_name:
                    operator_runtime.context.current_target = target_ip
                    print(f"{target_name}: {target_ip}")
                    tts.say(f"{target_name}: {target_ip}")
                else:
                    print("ターゲットが見つかりません")
                    tts.say("ターゲットが見つかりません")
                break

            if intent.name == "command.mode":
                if DRY_RUN:
                    report_dry_run("command.mode")
                else:
                    assist_command_mode(cmd_mgr, ip_mgr, asr, tts, command_dict, lang_ja)
                break

            ipaddress = cmd_name = op_name = None
            cmd_arg = None
            for word in user_order:
                if not ipaddress:
                    result = ip_mgr.get_target_values(word)
                    if result:
                        _, ipaddress = result
                if not cmd_name:
                    result = cmd_mgr.get_command_values(word)
                    if result:
                        cmd_name, cmd_arg = result
                if not op_name:
                    result = op_mgr.get_operation_values(word)
                    if result:
                        op_name, _ = result
                if ipaddress and (op_name or cmd_name):
                    break

            if op_name:
                canonical = _voice_intent(
                    "operation.run",
                    confidence=asr_result.confidence,
                    parameters={"operation": op_name},
                    target_ref=ipaddress,
                    context_ref="registered-sop",
                )
                pending = operator_runtime.submit(canonical)
                approved = ask_confirmation(asr, f"登録済みオペレーション {op_name} を実行します")
                resolved = operator_runtime.resolve_pending(approved, SourceModality.VOICE)
                logging.info(
                    "canonical operation status=%s correlation=%s confirmation=%s",
                    resolved.status,
                    resolved.correlation_id,
                    resolved.confirmation_id,
                )
                if not approved:
                    continue
                if DRY_RUN:
                    report_dry_run("operation", op_name)
                    break
                # A confirmed external write action (#18) is dispatched by the
                # runtime and reports its own result; Azazel-Edge keeps final
                # authority and may reject it.
                if resolved.status == "completed":
                    detail = resolved.payload.get("detail")
                    message = f"オペレーション {op_name} を実行しました"
                    if detail:
                        message += f"。{detail}"
                    print(message)
                    tts.say(message)
                    break
                if resolved.status == "failed":
                    detail = resolved.payload.get("detail") or ""
                    message = f"オペレーション {op_name} は承認先で拒否または失敗しました"
                    if detail:
                        message += f"。{detail}"
                    print(message)
                    tts.say(message)
                    break
                # Otherwise this is a registered local operation (SOP boundary).
                if resolved.status != "ready_for_registered_executor":
                    tts.say("オペレーションを実行可能な状態にできませんでした")
                    continue
                if ipaddress is None:
                    ipaddress = select_target(ip_mgr, tts, asr, lang_ja)
                    operator_runtime.context.current_target = ipaddress
                op_mgr.run_operation(op_name, ipaddress)
                break

            if cmd_name:
                if not ask_confirmation(asr, f"登録済みコマンド {cmd_name} を実行します"):
                    continue
                if DRY_RUN:
                    report_dry_run("command", cmd_name)
                    break
                if cmd_arg and not ipaddress:
                    ipaddress = select_target(ip_mgr, tts, asr, lang_ja)
                cmd_mgr.execute_command(cmd_name, ipaddress if cmd_arg else None)
                break

            tts.say(_persona_value("unknown_prompt", "指示を特定できませんでした。もう一度お願いします"))

        print("再度ウェイクアップフレーズを待機します。")
    except KeyboardInterrupt:
        print("\nCtrl+Cが押されました。プログラムを終了します。")
        logging.info("システム終了")
        raise SystemExit(0)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Babbly Japanese offline agent")
    parser.add_argument(
        "--profile",
        help="Agent/environment profile name. Overrides BABBLY_PROFILE and config PROFILE.",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List available local profiles and exit.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    base_config = load_config("babbly/ja/config_ja.yaml")

    if args.list_profiles:
        for name in list_profiles():
            print(name)
        return

    profile_name = resolve_profile_name(args.profile, base_config)
    profile = load_profile(profile_name)
    config = apply_profile_to_config(base_config, profile)
    set_agent_profile(profile)
    set_globals(config)
    configure_operator_runtime(config, create_situation_engine(config))

    ascii_art = pyfiglet.figlet_format(profile.identity.display_name, font="dos_rebel")
    print(ascii_art)
    print(
        f"profile={profile.id} agent={profile.identity.display_name} "
        f"wake={', '.join(profile.identity.wake_phrases)} environment={profile.environment.type}"
    )
    logging.info("プログラム開始")

    asr = create_asr(config)
    wake_detector = create_wake_detector(config, asr, domain_aliases)
    logging.info(
        "設定読み込み完了 profile=%s agent=%s persona=%s dry_run=%s azazel_edge=%s asr=%s wake=%s",
        profile.id,
        profile.identity.display_name,
        profile.persona.style,
        DRY_RUN,
        bool(config.get("AZAZEL_EDGE_ENABLED", False)),
        config.get("ASR_BACKEND", "vosk"),
        config.get("WAKE_BACKEND", "asr"),
    )

    # Optionally serve the compact Web/EUD surface in a background thread bound
    # to THIS shared runtime, so voice and the wearable EUD keep one target,
    # attention state, and pending confirmation.
    web_server = None
    if bool(config.get("WEB_SURFACE_ENABLED", False)):
        from babbly.web.server import start_web_surface

        web_host = str(config.get("WEB_SURFACE_HOST", "127.0.0.1"))
        web_port = int(config.get("WEB_SURFACE_PORT", 8787))
        web_server, _web_thread = start_web_surface(operator_runtime, host=web_host, port=web_port)
        print(f"Web surface: http://{web_host}:{web_port} (shared runtime)")

    print("＜音声認識開始 - 入力を待機します＞")
    if DRY_RUN:
        print("DRY_RUN is enabled: executable actions will be suppressed")
    tts.say(profile.persona.startup_phrase)
    try:
        wait_for_wakeup(wake_detector, asr)
    finally:
        if web_server is not None:
            web_server.shutdown()
            web_server.server_close()


if __name__ == '__main__':
    main()
