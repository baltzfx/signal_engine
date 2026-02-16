#!/usr/bin/env python3
"""
SignalEngine CLI - Command Line Interface for Market Analysis
Usage: python cli.py [command] [options]
"""

import argparse
import requests
import json
import sys
from datetime import datetime

API_BASE = "http://localhost:8000"

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*50}")
    print(f"🚀 {title}")
    print(f"{'='*50}")

def print_error(message):
    """Print an error message"""
    print(f"❌ Error: {message}")

def print_success(message):
    """Print a success message"""
    print(f"✅ {message}")

def check_server():
    """Check if the server is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Server is running")
            print(f"   Status: {data['status']}")
            print(f"   Redis: {'✅' if data['redis'] else '❌'}")
            print(f"   Symbols: {data['symbols_tracked']}")
            print(f"   Queue: {data['event_queue_size']} items")
            return True
        else:
            print_error(f"Server responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to server: {e}")
        print("   Make sure the server is running with: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return False

def get_top_symbols(count=5):
    """Get top symbols analysis"""
    print_header(f"Top {count} Symbols Analysis")

    if not check_server():
        return

    try:
        response = requests.get(f"{API_BASE}/query/top-symbols?count={count}", timeout=30)
        if response.status_code == 200:
            data = response.json()

            print(f"\n📊 Query: {data['query']}")
            print(f"⏰ Timestamp: {datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")

            print(f"\n🏆 TOP {count} SYMBOLS:")
            for i, symbol in enumerate(data['top_symbols'], 1):
                direction_emoji = "🟢" if symbol['direction'] == 'long' else "🔴"
                confidence = symbol['score'] * 100
                print(f"\n{i}. {direction_emoji} {symbol['symbol']} ({confidence:.1f}% confidence)")
                print(f"   {symbol['explanation']}")

            print(f"\n🤖 AI ANALYSIS:")
            print("-" * 40)
            print(data['ai_analysis'])

        else:
            error_data = response.json()
            print_error(error_data.get('error', f'HTTP {response.status_code}'))

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")

def list_symbols():
    """List all tracked symbols"""
    print_header("Tracked Symbols")

    if not check_server():
        return

    try:
        response = requests.get(f"{API_BASE}/symbols", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Tracking {data['count']} symbols")

            # Group symbols by category for better display
            major_coins = [s for s in data['symbols'] if s in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']]
            other_coins = [s for s in data['symbols'] if s not in major_coins]

            if major_coins:
                print(f"\n⭐ Major Coins ({len(major_coins)}):")
                for symbol in major_coins:
                    print(f"   {symbol.replace('USDT', '')}")

            if other_coins:
                print(f"\n📈 Other Symbols ({len(other_coins)}):")
                # Show first 20, then summarize
                for symbol in other_coins[:20]:
                    print(f"   {symbol.replace('USDT', '')}")
                if len(other_coins) > 20:
                    print(f"   ... and {len(other_coins) - 20} more")

        else:
            print_error(f"Failed to get symbols: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")

def get_recent_signals(limit=10):
    """Get recent signals"""
    print_header(f"Recent Signals (Last {limit})")

    if not check_server():
        return

    try:
        response = requests.get(f"{API_BASE}/signals?limit={limit}", timeout=10)
        if response.status_code == 200:
            data = response.json()

            if data['signals'] and len(data['signals']) > 0:
                print_success(f"Found {data['count']} total signals, showing last {len(data['signals'])}")

                for signal in data['signals']:
                    timestamp = datetime.fromtimestamp(signal['timestamp']).strftime('%m-%d %H:%M')
                    symbol = signal['symbol'].replace('USDT', '')
                    confidence = signal.get('confidence', 0) * 100
                    signal_type = signal.get('signal_type', 'unknown')

                    direction_emoji = "🟢" if signal.get('direction') == 'long' else "🔴"
                    print(f"{timestamp} | {direction_emoji} {symbol} | {signal_type} | {confidence:.1f}%")

            else:
                print("📭 No recent signals found")
                print("   The system may still be collecting data or no significant events have occurred.")

        else:
            print_error(f"Failed to get signals: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")

def get_metrics():
    """Get system metrics"""
    print_header("System Metrics")

    if not check_server():
        return

    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=10)
        if response.status_code == 200:
            data = response.json()

            print("🔧 SYSTEM METRICS:")
            if 'system' in data:
                system = data['system']
                print(f"   CPU Usage: {system.get('cpu_percent', 'N/A')}%")
                print(f"   Memory: {system.get('memory_mb', 'N/A'):.1f} MB")
                print(f"   Disk Free: {system.get('disk_free_gb', 'N/A'):.1f} GB")

            if 'counters' in data:
                print(f"   Active Counters: {len(data['counters'])}")

            if 'gauges' in data:
                print(f"   Active Gauges: {len(data['gauges'])}")

        else:
            print_error(f"Failed to get metrics: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="SignalEngine CLI - Market Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py status                    # Check server status
  python cli.py top 10                    # Get top 10 symbols analysis
  python cli.py symbols                   # List all tracked symbols
  python cli.py signals                   # Show recent signals
  python cli.py metrics                   # Show system metrics
        """
    )

    parser.add_argument('command', choices=['status', 'top', 'symbols', 'signals', 'metrics'],
                       help='Command to execute')
    parser.add_argument('count', nargs='?', type=int, default=5,
                       help='Number of items (for top command)')

    args = parser.parse_args()

    if args.command == 'status':
        check_server()
    elif args.command == 'top':
        get_top_symbols(args.count)
    elif args.command == 'symbols':
        list_symbols()
    elif args.command == 'signals':
        get_recent_signals()
    elif args.command == 'metrics':
        get_metrics()

if __name__ == "__main__":
    main()