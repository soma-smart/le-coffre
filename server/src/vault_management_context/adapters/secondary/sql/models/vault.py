from sqlmodel import CheckConstraint, SQLModel, Field


class VaultTable(SQLModel, table=True):
    __tablename__: str = "vault"
    __table_args__ = (CheckConstraint("id = 1", name="only_one_vault"),)

    id: int = Field(primary_key=True, default=1, nullable=False)
    nb_shares: int = Field(description="Number of Shamir shares")
    threshold: int = Field(description="Minimum shares needed to unlock")
    encrypted_key: str = Field(description="Encrypted vault key")
    setup_id: str = Field(description="Unique setup identifier")
    status: str = Field(default="PENDING", description="Vault status")
