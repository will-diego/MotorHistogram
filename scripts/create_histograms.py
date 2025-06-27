#!/usr/bin/env python3
"""
Simple histogram generator for motor data - shows complete ranges without smart editing
Sums all values across all events for each index
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
from pathlib import Path

def main():
    # Configuration
    MASTER_CSV = "csv_outputs/motor_data_master.csv"
    OUTPUT_DIR = "histogram_outputs"
    FIGURE_SIZE = (14, 8)
    
    # Create output directory
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    print("📊 Creating histograms from master CSV (summing all events)...")
    
    # Check master CSV
    if not os.path.exists(MASTER_CSV):
        print(f"❌ Master CSV not found: {MASTER_CSV}")
        return False
    
    # Load data
    df = pd.read_csv(MASTER_CSV)
    if df.empty:
        print("❌ Master CSV is empty")
        return False
    
    print(f"📅 Processing {len(df)} events from master CSV")
    
    # Define exact ranges - NO SMART EDITING
    categories = {
        'power': {
            'range': list(range(25, 901, 25)),  # 25, 50, 75... 900
            'title': 'Motor Power Distribution (Sum of All Events)',
            'ylabel': 'Total Power Values',
            'pattern': r'power(\d+)'
        },
        'torque': {
            'range': list(range(2, 91, 2)),     # 2, 4, 6... 90
            'title': 'Motor Torque Distribution (Sum of All Events)', 
            'ylabel': 'Total Torque Values',
            'pattern': r'torque(\d+)'
        },
        'motor_temp': {
            'range': list(range(10, 201, 10)),  # 10, 20, 30... 200
            'title': 'Motor Temperature Distribution (Sum of All Events)',
            'ylabel': 'Total Temperature (°C)',
            'pattern': r'motor.*temp.*(\d+)'
        },
        'mosfet_temp': {
            'range': list(range(10, 201, 10)), # 10, 20, 30... 200
            'title': 'MOSFET Temperature Distribution (Sum of All Events)',
            'ylabel': 'Total Temperature (°C)', 
            'pattern': r'mosfet.*temp.*(\d+)'
        }
    }
    
    charts_created = 0
    
    # Process each category
    for category_name, config in categories.items():
        print(f"\n🔍 Processing {category_name}...")
        
        # Find matching columns and sum all values
        matching_data = {}
        for col in df.columns:
            if col == 'timestamp':
                continue
                
            # Check if column matches pattern and extract index
            index = None
            if category_name == 'power' and 'power' in col.lower():
                match = re.search(r'(\d+)', col)
                if match:
                    index = int(match.group(1))
            
            elif category_name == 'torque' and 'torque' in col.lower():
                match = re.search(r'(\d+)', col)
                if match:
                    index = int(match.group(1))
            
            elif category_name == 'motor_temp' and ('motor' in col.lower() and 'temp' in col.lower()):
                match = re.search(r'(\d+)', col)
                if match:
                    index = int(match.group(1))
            
            elif category_name == 'mosfet_temp' and ('mosfet' in col.lower() and 'temp' in col.lower()):
                match = re.search(r'(\d+)', col)
                if match:
                    index = int(match.group(1))
            
            # If we found a valid index and it's in our range, sum all values
            if index is not None and index in config['range']:
                # Sum all non-null values in this column across all rows
                column_sum = df[col].fillna(0).sum()
                if column_sum > 0:  # Only include if there's actual data
                    matching_data[index] = column_sum
        
        # Create complete range with zeros for missing values
        full_range = config['range']
        full_values = [matching_data.get(idx, 0) for idx in full_range]
        
        print(f"   ✅ Found data for {len(matching_data)} indices out of {len(full_range)} total")
        total_sum = sum(matching_data.values())
        print(f"   📊 Total sum across all events: {total_sum:.1f}")
        
        # Create chart
        if create_simple_chart(full_range, full_values, category_name, config, OUTPUT_DIR, FIGURE_SIZE):
            charts_created += 1
            print(f"   ✅ Created {category_name} chart")
        else:
            print(f"   ❌ Failed to create {category_name} chart")
    
    print(f"\n🎉 Created {charts_created} charts")
    return charts_created > 0

def create_simple_chart(indices, values, category_name, config, output_dir, figure_size):
    """Create a simple chart showing the complete range"""
    
    try:
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=figure_size)
        
        # Create bars
        x_positions = range(len(indices))
        bars = ax.bar(x_positions, values, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Color bars - simple gradient based on values
        if max(values) > 0:
            norm_values = np.array(values)
            norm_values = norm_values / max(values)  # Normalize to 0-1
            colors = plt.colormaps['viridis'](norm_values)
            for bar, color in zip(bars, colors):
                bar.set_facecolor(color)
        
        # Title and labels
        ax.set_title(config['title'], fontsize=16, fontweight='bold')
        ax.set_xlabel('Index', fontsize=12)
        ax.set_ylabel(config['ylabel'], fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')
        
        # X-axis labels - show every few indices to avoid crowding
        step = max(1, len(indices) // 20)  # Show roughly 20 labels max
        tick_positions = list(range(0, len(indices), step))
        tick_labels = [str(indices[i]) for i in tick_positions]
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right')
        
        # Add value labels only for non-zero bars
        max_val = max(values) if values else 1
        for i, (bar, value) in enumerate(zip(bars, values)):
            if value > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max_val*0.01,
                       f'{value:.0f}', ha='center', va='bottom', fontsize=8)
        
        # Statistics box
        non_zero_values = [v for v in values if v > 0]
        if non_zero_values:
            stats_text = f'Total Indices: {len(indices)}\n'
            stats_text += f'With Data: {len(non_zero_values)}\n'
            stats_text += f'Max Value: {max(non_zero_values):.1f}\n'
            stats_text += f'Total Sum: {sum(non_zero_values):.1f}'
        else:
            stats_text = f'Total Indices: {len(indices)}\nNo data found'
        
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9),
               verticalalignment='top', horizontalalignment='right', fontsize=10)
        
        # Save files
        plt.tight_layout()
        
        # PNG file
        png_file = os.path.join(output_dir, f'{category_name}_chart.png')
        plt.savefig(png_file, dpi=300, bbox_inches='tight')
        
        # CSV file
        csv_file = os.path.join(output_dir, f'{category_name}_numeric_values.csv')
        chart_df = pd.DataFrame({
            'Numeric_Label': indices,
            'Value': values,
            'Original_Property': [f'{category_name}{idx}' for idx in indices]
        })
        chart_df.to_csv(csv_file, index=False)
        
        plt.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating {category_name} chart: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 