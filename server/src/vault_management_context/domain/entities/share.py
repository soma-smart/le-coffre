from dataclasses import dataclass, asdict


@dataclass
class Share:
    index: int
    secret: str

    def to_dict(self) -> dict:
        return asdict(self)
