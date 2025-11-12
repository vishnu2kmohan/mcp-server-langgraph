#!/usr/bin/env python3
"""
GKE Autopilot Resource Calculator

Calculate compliant resource requests and limits for GKE Autopilot (4.0x ratio constraint).

TDD Context:
- RED (2025-11-12): Multiple services had non-compliant CPU ratios (5.0x, 8.0x, 10.0x)
- GREEN: Fixed all violations, created this calculator
- REFACTOR: Tool helps developers calculate compliant values

Usage:
    # Calculate request for a given limit
    python scripts/calculate_gke_resources.py --limit 1000m

    # Calculate limit for a given request
    python scripts/calculate_gke_resources.py --request 250m

    # Interactive mode
    python scripts/calculate_gke_resources.py --interactive

    # Show common service configurations
    python scripts/calculate_gke_resources.py --examples
"""

import argparse
import sys
from typing import Tuple


class GKEResourceCalculator:
    """Calculator for GKE Autopilot compliant resources"""

    MAX_RATIO = 4.0

    def __init__(self):
        self.common_limits = ["400m", "500m", "800m", "1000m", "2000m", "4000m"]
        self.common_requests = ["100m", "125m", "200m", "250m", "500m", "1000m"]

    def parse_cpu(self, cpu_str: str) -> float:
        """Parse CPU string to millicores"""
        cpu_str = cpu_str.strip()
        if cpu_str.endswith('m'):
            return float(cpu_str[:-1])
        return float(cpu_str) * 1000

    def format_cpu(self, millicores: float) -> str:
        """Format millicores to CPU string"""
        if millicores >= 1000 and millicores % 1000 == 0:
            return f"{int(millicores / 1000)}"
        return f"{int(millicores)}m"

    def calculate_min_request(self, limit: str) -> Tuple[str, float]:
        """Calculate minimum request for a given limit to achieve 4.0x ratio"""
        limit_mc = self.parse_cpu(limit)
        min_request_mc = limit_mc / self.MAX_RATIO
        ratio = limit_mc / min_request_mc

        return self.format_cpu(min_request_mc), ratio

    def calculate_max_limit(self, request: str) -> Tuple[str, float]:
        """Calculate maximum limit for a given request to achieve 4.0x ratio"""
        request_mc = self.parse_cpu(request)
        max_limit_mc = request_mc * self.MAX_RATIO
        ratio = max_limit_mc / request_mc

        return self.format_cpu(max_limit_mc), ratio

    def validate_ratio(self, request: str, limit: str) -> Tuple[bool, float]:
        """Validate if request/limit combination is compliant"""
        request_mc = self.parse_cpu(request)
        limit_mc = self.parse_cpu(limit)

        if request_mc == 0:
            return False, float('inf')

        ratio = limit_mc / request_mc
        is_compliant = ratio <= self.MAX_RATIO

        return is_compliant, ratio

    def suggest_compliant_values(self, request: str, limit: str) -> dict:
        """Suggest compliant values for a non-compliant configuration"""
        request_mc = self.parse_cpu(request)
        limit_mc = self.parse_cpu(limit)
        current_ratio = limit_mc / request_mc

        # Option 1: Increase request (preserve burst capacity)
        new_request_mc = limit_mc / self.MAX_RATIO
        option1 = {
            "strategy": "Increase Request (Recommended)",
            "request": self.format_cpu(new_request_mc),
            "limit": limit,
            "ratio": self.MAX_RATIO,
            "pros": "Preserves burst capacity, better for production",
            "cons": f"Increases baseline cost by {((new_request_mc - request_mc) / request_mc * 100):.1f}%"
        }

        # Option 2: Decrease limit (reduce burst capacity)
        new_limit_mc = request_mc * self.MAX_RATIO
        option2 = {
            "strategy": "Decrease Limit",
            "request": request,
            "limit": self.format_cpu(new_limit_mc),
            "ratio": self.MAX_RATIO,
            "pros": "Lower resource costs",
            "cons": f"Reduces burst capacity by {((limit_mc - new_limit_mc) / limit_mc * 100):.1f}%"
        }

        return {
            "current": {"request": request, "limit": limit, "ratio": current_ratio},
            "option1": option1,
            "option2": option2
        }

    def get_service_examples(self) -> dict:
        """Get example configurations for common services"""
        return {
            "otel-collector": {
                "description": "OpenTelemetry Collector (telemetry data)",
                "old": {"request": "200m", "limit": "1000m", "ratio": 5.0},
                "fixed": {"request": "250m", "limit": "1000m", "ratio": 4.0},
            },
            "qdrant": {
                "description": "Qdrant Vector Database (similarity search)",
                "old": {"request": "100m", "limit": "1000m", "ratio": 10.0},
                "fixed": {"request": "250m", "limit": "1000m", "ratio": 4.0},
            },
            "postgres": {
                "description": "PostgreSQL Database (primary data store)",
                "old": {"request": "250m", "limit": "2000m", "ratio": 8.0},
                "fixed": {"request": "500m", "limit": "2000m", "ratio": 4.0},
            },
            "redis-session": {
                "description": "Redis Session Store (caching)",
                "old": {"request": "100m", "limit": "500m", "ratio": 5.0},
                "fixed": {"request": "125m", "limit": "500m", "ratio": 4.0},
            },
            "mcp-server (dev)": {
                "description": "MCP Server Application (development)",
                "old": {"request": "100m", "limit": "500m", "ratio": 5.0},
                "fixed": {"request": "125m", "limit": "500m", "ratio": 4.0},
            },
            "mcp-server (prod)": {
                "description": "MCP Server Application (production)",
                "fixed": {"request": "500m", "limit": "2000m", "ratio": 4.0},
            },
        }


def print_suggestions(calculator: GKEResourceCalculator, request: str, limit: str):
    """Print suggestions for a configuration"""
    is_compliant, ratio = calculator.validate_ratio(request, limit)

    print(f"\n{'='*70}")
    print(f"GKE Autopilot Resource Analysis")
    print(f"{'='*70}\n")

    print(f"Current Configuration:")
    print(f"  Request: {request}")
    print(f"  Limit:   {limit}")
    print(f"  Ratio:   {ratio:.2f}x")

    if is_compliant:
        print(f"  Status:  ✅ COMPLIANT (ratio ≤ {calculator.MAX_RATIO}x)")
        print(f"\n✨ Your configuration is GKE Autopilot compliant!")
    else:
        print(f"  Status:  ❌ VIOLATION (ratio > {calculator.MAX_RATIO}x)")

        suggestions = calculator.suggest_compliant_values(request, limit)

        print(f"\n{'─'*70}")
        print(f"Recommended Fixes:")
        print(f"{'─'*70}\n")

        # Option 1
        opt1 = suggestions["option1"]
        print(f"Option 1: {opt1['strategy']}")
        print(f"  Request: {opt1['request']} (was: {request})")
        print(f"  Limit:   {opt1['limit']}")
        print(f"  Ratio:   {opt1['ratio']:.1f}x ✅")
        print(f"  Pros:    {opt1['pros']}")
        print(f"  Cons:    {opt1['cons']}\n")

        # Option 2
        opt2 = suggestions["option2"]
        print(f"Option 2: {opt2['strategy']}")
        print(f"  Request: {opt2['request']}")
        print(f"  Limit:   {opt2['limit']} (was: {limit})")
        print(f"  Ratio:   {opt2['ratio']:.1f}x ✅")
        print(f"  Pros:    {opt2['pros']}")
        print(f"  Cons:    {opt2['cons']}\n")

        print(f"💡 Recommendation: Use Option 1 for production workloads")

    print(f"{'='*70}\n")


def print_examples(calculator: GKEResourceCalculator):
    """Print example service configurations"""
    examples = calculator.get_service_examples()

    print(f"\n{'='*70}")
    print(f"Common Service Configurations (GKE Autopilot Compliant)")
    print(f"{'='*70}\n")

    for service, config in examples.items():
        print(f"{service}:")
        print(f"  {config['description']}")

        if "old" in config:
            old = config["old"]
            print(f"  ❌ Old:   {old['request']} request / {old['limit']} limit = {old['ratio']}x")

        fixed = config["fixed"]
        print(f"  ✅ Fixed: {fixed['request']} request / {fixed['limit']} limit = {fixed['ratio']}x")
        print()

    print(f"{'='*70}\n")


def interactive_mode(calculator: GKEResourceCalculator):
    """Interactive calculator mode"""
    print(f"\n{'='*70}")
    print("GKE Autopilot Resource Calculator (Interactive Mode)")
    print(f"{'='*70}\n")
    print("Calculate compliant resource values for GKE Autopilot.")
    print(f"Maximum CPU limit/request ratio: {calculator.MAX_RATIO}x\n")

    while True:
        print("Options:")
        print("  1. Calculate minimum request for a limit")
        print("  2. Calculate maximum limit for a request")
        print("  3. Validate request + limit combination")
        print("  4. Show common service examples")
        print("  5. Exit")

        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "1":
            limit = input("Enter CPU limit (e.g., 1000m, 2): ").strip()
            try:
                min_request, ratio = calculator.calculate_min_request(limit)
                print(f"\n✅ For limit {limit}:")
                print(f"   Minimum request: {min_request}")
                print(f"   Ratio: {ratio:.1f}x")
            except Exception as e:
                print(f"❌ Error: {e}")

        elif choice == "2":
            request = input("Enter CPU request (e.g., 250m, 0.5): ").strip()
            try:
                max_limit, ratio = calculator.calculate_max_limit(request)
                print(f"\n✅ For request {request}:")
                print(f"   Maximum limit: {max_limit}")
                print(f"   Ratio: {ratio:.1f}x")
            except Exception as e:
                print(f"❌ Error: {e}")

        elif choice == "3":
            request = input("Enter CPU request (e.g., 250m): ").strip()
            limit = input("Enter CPU limit (e.g., 1000m): ").strip()
            try:
                print_suggestions(calculator, request, limit)
            except Exception as e:
                print(f"❌ Error: {e}")

        elif choice == "4":
            print_examples(calculator)

        elif choice == "5":
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please enter 1-5.")

        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Calculate GKE Autopilot compliant resource values",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate minimum request for a 1000m limit
  %(prog)s --limit 1000m

  # Calculate maximum limit for a 250m request
  %(prog)s --request 250m

  # Validate a configuration
  %(prog)s --request 200m --limit 1000m

  # Show common service examples
  %(prog)s --examples

  # Interactive mode
  %(prog)s --interactive
        """
    )

    parser.add_argument("--request", help="CPU request (e.g., 250m, 0.5)")
    parser.add_argument("--limit", help="CPU limit (e.g., 1000m, 2)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Run in interactive mode")
    parser.add_argument("--examples", "-e", action="store_true",
                        help="Show common service configuration examples")

    args = parser.parse_args()

    calculator = GKEResourceCalculator()

    if args.interactive:
        interactive_mode(calculator)
        return 0

    if args.examples:
        print_examples(calculator)
        return 0

    if args.request and args.limit:
        # Validate and suggest
        print_suggestions(calculator, args.request, args.limit)
        is_compliant, _ = calculator.validate_ratio(args.request, args.limit)
        return 0 if is_compliant else 1

    elif args.limit:
        # Calculate minimum request
        min_request, ratio = calculator.calculate_min_request(args.limit)
        print(f"\n✅ For CPU limit: {args.limit}")
        print(f"   Minimum request: {min_request}")
        print(f"   Ratio: {ratio:.1f}x (compliant)\n")
        return 0

    elif args.request:
        # Calculate maximum limit
        max_limit, ratio = calculator.calculate_max_limit(args.request)
        print(f"\n✅ For CPU request: {args.request}")
        print(f"   Maximum limit: {max_limit}")
        print(f"   Ratio: {ratio:.1f}x (compliant)\n")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
