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
        role="Opportunity Thesis and Value Realization",
        purpose="Builds the strongest evidence-based upside case and execution path.",
        accent_color="#818cf8",
        glow_color="rgba(99, 102, 241, 0.28)",
        shape="tetrahedron",
        processing_order=1,
    ),
    AgentConfig(
        id="skeptic",
        codename="Skeptic",
        role="Risk Decomposition and Failure Analysis",
        purpose="Challenges assumptions, identifies failure modes, and quantifies downside exposure.",
        accent_color="#f87171",
        glow_color="rgba(239, 68, 68, 0.28)",
        shape="icosahedron",
        processing_order=2,
    ),
    AgentConfig(
        id="synthesiser",
        codename="Synthesiser",
        role="Tradeoff Integration and Decision Framing",
        purpose="Integrates competing perspectives into a decision-ready recommendation.",
        accent_color="#34d399",
        glow_color="rgba(16, 185, 129, 0.28)",
        shape="dodecahedron",
        processing_order=3,
    ),
    AgentConfig(
        id="oracle",
        codename="Oracle",
        role="Scenario Forecasting and Operating Outlook",
        purpose="Forecasts near-term outcomes with scenario ranges, triggers, and confidence levels.",
        accent_color="#fbbf24",
        glow_color="rgba(245, 158, 11, 0.28)",
        shape="box",
        processing_order=4,
    ),
)
