import argparse
from pathlib import Path
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.simulator import generate_canteen_dataset
from app.core.logging import logger


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic canteen queue data using SimPy")
    parser.add_argument("--orders", type=int, default=5000, help="Number of orders to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="data/canteen_simulation.csv", help="Output CSV path")
    args = parser.parse_args()

    logger.info(f"Generating {args.orders} simulated orders with seed {args.seed}...")
    df = generate_canteen_dataset(target_orders=args.orders, seed=args.seed)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    logger.info(f"Dataset successfully saved to {out_path} ({len(df)} rows, {len(df.columns)} columns)")


if __name__ == "__main__":
    main()
