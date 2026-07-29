from taxi_pipeline.extract import ingest_year


def main() -> None:
    results = ingest_year(
        year=2025,
        taxi_types=["yellow", "green"],
    )

    print("\nFinal summary")
    print(f"Year: {results['year']}")
    print(f"Successful: {results['successful_count']}")
    print(f"Failed: {results['failed_count']}")


if __name__ == "__main__":
    main()