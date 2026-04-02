from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    id: str
    codename: str
    role: str
    purpose: str
    accent_color: str
    glow_color: str
    shape: str
    processing_order: int


AGENTS: tuple[AgentConfig, ...] = (
    AgentConfig(
        id="advocate",
        codename="Advocate",
        role="Constructive Reasoning",
        purpose="Builds the strongest possible case for a hypothesis.",
        accent_color="#818cf8",
        glow_color="rgba(99, 102, 241, 0.28)",
        shape="tetrahedron",
        processing_order=1,
    ),
    AgentConfig(
        id="skeptic",
        codename="Skeptic",
        role="Adversarial Stress-Testing",
        purpose="Challenges assumptions and surfaces risks.",
        accent_color="#f87171",
        glow_color="rgba(239, 68, 68, 0.28)",
        shape="icosahedron",
        processing_order=2,
    ),
    AgentConfig(
        id="synthesiser",
        codename="Synthesiser",
        role="Perspective Integration",
        purpose="Combines competing views into a balanced conclusion.",
        accent_color="#34d399",
        glow_color="rgba(16, 185, 129, 0.28)",
        shape="dodecahedron",
        processing_order=3,
    ),
    AgentConfig(
        id="oracle",
        codename="Oracle",
        role="Predictive Inference",
        purpose="Projects likely outcomes and next actions.",
        accent_color="#fbbf24",
        glow_color="rgba(245, 158, 11, 0.28)",
        shape="box",
        processing_order=4,
    ),
)
