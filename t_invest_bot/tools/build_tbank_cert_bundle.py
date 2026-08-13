from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ROOT_CERTIFICATE = (
    PROJECT_ROOT
    / "RussianTrustedRootCA.pem"
)

SUB_CERTIFICATE = (
    PROJECT_ROOT
    / "RussianTrustedSubCA.pem"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "tbank_roots.pem"
)


def read_certificate(
    path: Path,
) -> str:
    if not path.exists():
        raise RuntimeError(
            f"Certificate not found: {path}"
        )

    content = path.read_text(
        encoding="utf-8",
    ).strip()

    if "BEGIN CERTIFICATE" not in content:
        raise RuntimeError(
            f"Invalid PEM certificate: {path}"
        )

    return content


def main() -> None:
    root_certificate = read_certificate(
        ROOT_CERTIFICATE
    )

    sub_certificate = read_certificate(
        SUB_CERTIFICATE
    )

    bundle = (
        root_certificate
        + "\n"
        + sub_certificate
        + "\n"
    )

    OUTPUT_FILE.write_text(
        bundle,
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print("T-BANK CERTIFICATE BUNDLE")
    print("=" * 60)

    print(
        f"Root : {ROOT_CERTIFICATE}"
    )

    print(
        f"Sub  : {SUB_CERTIFICATE}"
    )

    print(
        f"Bundle: {OUTPUT_FILE}"
    )

    print()
    print("Bundle created successfully.")


if __name__ == "__main__":
    main()
