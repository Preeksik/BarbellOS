"""Generuje wartość APP_PASSWORD_HASH.  Użycie:  python -m app.tools.hash_password"""

import getpass

from app.security import hash_password


def main() -> None:
    first = getpass.getpass("Hasło: ")
    if len(first) < 10:
        raise SystemExit("Hasło musi mieć co najmniej 10 znaków.")
    if first != getpass.getpass("Powtórz hasło: "):
        raise SystemExit("Hasła się różnią.")
    print("\nWklej do .env (w cudzysłowie pojedynczym, bo wartość zawiera znaki $):\n")
    print(f"APP_PASSWORD_HASH='{hash_password(first)}'")


if __name__ == "__main__":
    main()
