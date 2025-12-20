"""
Basic usage example for PyBovespa

This script demonstrates how to download and analyze B3 options data.
"""

import pybovespa as pyb
import pandas as pd


def main():
    print("PyBovespa - Basic Usage Example")
    print("=" * 50)
    
    # Initialize
    print("\n1. Initializing PyBovespa...")
    b3 = pyb.PyBovespa(cache_dir="./data")
    
    # Download options for 2024
    print("\n2. Downloading options data for 2024...")
    print("   (This may take a few minutes on first run)")
    
    try:
        options = b3.get_options(year=2024)
        print(f"   ✓ Downloaded {len(options):,} option records")
    except Exception as e:
        print(f"   ✗ Download failed: {e}")
        print("\n   If CAPTCHA is required, download manually from:")
        print("   https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/")
        return
    
    # Basic analysis
    print("\n3. Basic Analysis")
    print("-" * 50)
    
    # Count by instrument type
    print("\nOptions by type:")
    print(options['instrument_type'].value_counts())
    
    # Top underlyings by number of series
    print("\nTop 10 underlyings by number of option series:")
    top_underlyings = options['underlying'].value_counts().head(10)
    print(top_underlyings)
    
    # Filter PETR4 options
    print("\n4. Analyzing PETR4 options")
    print("-" * 50)
    petr_options = options[options['underlying'] == 'PETR'].copy()
    print(f"Total PETR options: {len(petr_options):,}")
    
    # Separate calls and puts
    petr_calls = petr_options[petr_options['instrument_type'] == 'CALL']
    petr_puts = petr_options[petr_options['instrument_type'] == 'PUT']
    
    print(f"  - Calls: {len(petr_calls):,}")
    print(f"  - Puts:  {len(petr_puts):,}")
    
    # Statistics
    print("\nPETR4 options statistics:")
    print(f"  Strike range: R$ {petr_options['strike_price'].min():.2f} - R$ {petr_options['strike_price'].max():.2f}")
    print(f"  Premium range: R$ {petr_options['close_price'].min():.2f} - R$ {petr_options['close_price'].max():.2f}")
    print(f"  Total volume: R$ {petr_options['volume'].sum():,.2f}")
    
    # Show sample data
    print("\n5. Sample PETR4 call options:")
    print("-" * 50)
    sample = petr_calls[
        ['ticker', 'strike_price', 'maturity_date', 'close_price', 'volume', 'days_to_maturity']
    ].head(10)
    print(sample.to_string(index=False))
    
    # Save to file
    output_file = "data/petr4_options_2024.csv"
    petr_options.to_csv(output_file, index=False)
    print(f"\n✓ PETR4 options saved to {output_file}")
    
    print("\n" + "=" * 50)
    print("Example completed successfully!")


if __name__ == "__main__":
    main()
