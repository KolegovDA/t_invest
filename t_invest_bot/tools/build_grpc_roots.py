from pathlib import Path
import ssl

import certifi


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "grpc_roots.pem"
)


def main() -> None:
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pem_parts: list[str] = []

    #
    # 1. Стандартный CA bundle certifi
    #
    certifi_path = Path(
        certifi.where()
    )

    certifi_bundle = certifi_path.read_text(
        encoding="utf-8",
    )

    pem_parts.append(
        certifi_bundle
    )

    #
    # 2. Корневые сертификаты Windows
    #
    windows_certificates_count = 0

    stores = [
        "ROOT",
        "CA",
    ]

    for store_name in stores:
        try:
            certificates = ssl.enum_certificates(
                store_name,
            )
        except Exception as error:
            print(
                f"WARNING: cannot read Windows "
                f"certificate store {store_name}: "
                f"{error!r}"
            )
            continue

        for (
            certificate_bytes,
            encoding_type,
            trust,
        ) in certificates:
            #
            # Нам нужны обычные X509 DER certificates.
            #
            if encoding_type != "x509_asn":
                continue

            try:
                pem = ssl.DER_cert_to_PEM_cert(
                    certificate_bytes,
                )
            except Exception:
                continue

            pem_parts.append(
                pem
            )

            windows_certificates_count += 1

    #
    # Записываем итоговый bundle.
    #
    OUTPUT_FILE.write_text(
        "\n".join(pem_parts),
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print("GRPC ROOT CERTIFICATES")
    print("=" * 60)

    print(
        f"Created: {OUTPUT_FILE}"
    )

    print(
        "Certifi bundle:",
        certifi_path,
    )

    print(
        "Windows certificates added:",
        windows_certificates_count,
    )

    print()
    print("Use:")
    print(
        "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="
        + str(OUTPUT_FILE)
    )


if __name__ == "__main__":
    main()
