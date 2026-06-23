from password_management_context.adapters.secondary.readers.keepass_reader import (
    KeepassEntry,
    KeepassReader,
)


class PyKeepassReaderGateway:
    """Gateway implementation to read password entries from a KeePass file.

    This adapter lives in the Password Management context and uses the KeePass
    reader to isolate KeePass parsing from the application layer.
    """

    def __init__(self, keepass_reader: KeepassReader):
        self.keepass_reader = keepass_reader

    def read_entries(
        self,
        content: bytes,
        master_password: str,
    ) -> list[KeepassEntry]:
        """Read password entries from a KeePass file.

        Args:
            content: The raw KeePass `.kdbx` file content
            master_password: The KeePass master password

        Returns:
            The list of password entries found in the KeePass file
        """
        return self.keepass_reader.read_entries(
            content=content,
            master_password=master_password,
        )
