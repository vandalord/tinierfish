from __future__ import annotations

from agents.pipeline_service import run_demo_pipeline


def main() -> None:
    payload = run_demo_pipeline()
    print("Demo pipeline completed.")
    print(f"HTML map: {payload['visualization_batch']['html_path']}")


if __name__ == "__main__":
    main()
