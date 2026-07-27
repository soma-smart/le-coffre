from dataclasses import dataclass, field


@dataclass
class ConsumeOneTimeLinkCommand:
    token: str = field(repr=False)  # secret: keep it out of logs and tracebacks
