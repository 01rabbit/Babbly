from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentIdentity:
    id: str
    display_name: str
    spoken_name: str
    wake_phrases: tuple[str, ...]
    language: str = "ja"

    @property
    def primary_wake_phrase(self) -> str:
        return self.wake_phrases[0]


@dataclass(frozen=True)
class PersonaProfile:
    tone: str
    style: str
    verbosity: str
    startup_phrase: str
    acknowledgement: str
    command_prompt: str
    unknown_prompt: str
    shutdown_phrase: str
    introduction: tuple[str, ...]


@dataclass(frozen=True)
class EnvironmentProfile:
    type: str
    vocabulary_packs: tuple[str, ...]
    situation_sources: tuple[str, ...]


@dataclass(frozen=True)
class AgentProfile:
    id: str
    identity: AgentIdentity
    persona: PersonaProfile
    environment: EnvironmentProfile
