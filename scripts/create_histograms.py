#!/usr/bin/env python3
"""
Modern histogram generator for master CSV motor data
Works with the new master CSV format where all motor data is in one file
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
    FIGURE_SIZE = (12, 8)
    
    # Create output directory
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    print("🚀 Starting modern histogram generation from master CSV...")
    
    # Check if master CSV exists
    if not os.path.exists(MASTER_CSV):
        print(f"❌ Master CSV not found: {MASTER_CSV}")
        print("💡 Make sure to download some motor data first!")
        return False
    
    # Load master CSV
    try:
        df = pd.read_csv(MASTER_CSV)
        print(f"✅ Loaded master CSV with {len(df)} rows and {len(df.columns)} columns")
        
        if df.empty:
            print("❌ Master CSV is empty")
            return False
            
    except Exception as e:
        print(f"❌ Error reading master CSV: {e}")
        return False
    
    # Use the most recent row (last row)
    latest_row = df.iloc[-1]
    timestamp = latest_row.get('timestamp', 'Unknown')
    print(f"📅 Using data from: {timestamp}")
    
    # Define motor data categories with their column patterns and expected ranges
    categories = {
        'power': {
            'patterns': [r'power\d+', r'powerHigh', r'powerLow'],
            'title': 'Motor Power',
            'xlabel': 'Power Index',
            'ylabel': 'Power Values',
            'range': (25, 800)  # Expected range: 25-800
        },
        'torque': {
            'patterns': [r'torque\d+', r'torqueHigh', r'torqueLow'], 
            'title': 'Motor Torque',
            'xlabel': 'Torque Index', 
            'ylabel': 'Torque Values',
            'range': (2, 90)  # Expected range: 2-90
        },
        'motor_temp': {
            'patterns': [r'motor.*temp', r'Motor\.Temperature', r'motortemperature'],
            'title': 'Motor Temperature',
            'xlabel': 'Temperature Index',
            'ylabel': 'Temperature (°C)',
            'range': (10, 200)  # Expected range: 10-200°C
        },
        'mosfet_temp': {
            'patterns': [r'mosfet.*temp', r'MOSFET\.Temperature', r'mosfettemperature'],
            'title': 'MOSFET Temperature', 
            'xlabel': 'Temperature Index',
            'ylabel': 'Temperature (°C)',
            'range': (10, 200)  # Expected range: 10-200°C
        }
    }
    
    charts_created = 0
    
    # Process each category
    for category_name, category_info in categories.items():
        print(f"\n🔍 Processing {category_name}...")
        
        # Find columns matching this category
        matching_columns = []
        for col in df.columns:
            if col == 'timestamp':
                continue
                
            # Check if column matches any pattern for this category
            col_lower = col.lower()
            for pattern in category_info['patterns']:
                if re.search(pattern.lower(), col_lower):
                    matching_columns.append(col)
                    break
        
        if not matching_columns:
            print(f"   ⚠️ No columns found for {category_name}")
            continue
            
        print(f"   ✅ Found {len(matching_columns)} columns: {matching_columns[:5]}{'...' if len(matching_columns) > 5 else ''}")
        
        # Extract numeric data from matching columns
        chart_data = []
        for col in matching_columns:
            try:
                value = latest_row[col]
                
                # Convert to numeric
                if pd.isna(value):
                    continue
                    
                numeric_value = float(value)
                if np.isnan(numeric_value):
                    continue
                
                # Don't skip any values - show all including zeros for reference
                
                # Validate value is within expected range
                min_val, max_val = category_info.get('range', (0, float('inf')))
                if numeric_value < min_val or numeric_value > max_val:
                    print(f"   ⚠️ Value {numeric_value} for {col} outside expected range {min_val}-{max_val}, skipping")
                    continue
                
                # Extract numeric index from column name
                numeric_index = extract_numeric_index(col, category_name)
                if numeric_index is not None:
                    chart_data.append({
                        'index': numeric_index,
                        'value': numeric_value,
                        'column': col
                    })
                    
            except (ValueError, TypeError) as e:
                print(f"   ⚠️ Skipping {col}: {e}")
                continue
        
        if not chart_data:
            print(f"   ❌ No valid numeric data found for {category_name}")
            min_val, max_val = category_info.get('range', (0, float('inf')))
            print(f"   💡 Expected range: {min_val}-{max_val}, Shows all values including zeros")
            continue
        
        # Sort by index
        chart_data.sort(key=lambda x: x['index'])
        
        # Don't remove any values - show full x-axis range
        # Keep all data points for complete picture
        
        if not chart_data:
            print(f"   ❌ No data remaining after cleaning for {category_name}")
            continue
        
        # Create the chart
        success = create_chart(chart_data, category_name, category_info, OUTPUT_DIR, FIGURE_SIZE)
        if success:
            charts_created += 1
            print(f"   ✅ Created chart for {category_name}")
        else:
            print(f"   ❌ Failed to create chart for {category_name}")
    
    print(f"\n🎉 Histogram generation complete!")
    print(f"📊 Created {charts_created} charts in '{OUTPUT_DIR}' directory")
    
    if charts_created == 0:
        print("💡 No charts were created. This might be because:")
        print("   - Column names don't match expected patterns")
        print("   - Data values are invalid or missing")
        print("   - Try downloading fresh data")
    
    return charts_created > 0

def extract_numeric_index(column_name, category):
    """Extract numeric index from column name based on category"""
    
    # For torque: usually 2-digit suffixes (00, 25, 50, etc.) - skip index 0
    if 'torque' in category:
        match = re.search(r'(\d{2})$', column_name)
        if match:
            index = int(match.group(1))
            if index == 0:
                return None  # Skip index 0 for torque
            return index
    
    # For power: usually 3-digit suffixes (000, 025, 050, etc.) - skip index 0
    elif 'power' in category:
        match = re.search(r'(\d{3})$', column_name)
        if match:
            index = int(match.group(1))
            if index == 0:
                return None  # Skip index 0 for power
            return index
        # Handle special cases like powerHigh, powerLow
        elif 'high' in column_name.lower():
            return 999  # Put at end
        elif 'low' in column_name.lower():
            return -1   # Put at beginning
    
    # For temperature: various patterns
    elif 'temp' in category:
        # Try 3-digit pattern first
        match = re.search(r'(\d{3})$', column_name)
        if match:
            return int(match.group(1))
        # Try 2-digit pattern
        match = re.search(r'(\d{2})$', column_name)
        if match:
            return int(match.group(1))
        # Special temperature cases
        elif 'low' in column_name.lower():
            return -1
        elif 'high' in column_name.lower():
            return 999
    
    # Fallback: try to find any number in the column name
    numbers = re.findall(r'\d+', column_name)
    if numbers:
        return int(numbers[-1])  # Use last number found
    
    return None

def create_chart(chart_data, category_name, category_info, output_dir, figure_size):
    """Create and save a chart for the given category data"""
    
    try:
        # Extract data for plotting
        indices = [item['index'] for item in chart_data]
        values = [item['value'] for item in chart_data]
        columns = [item['column'] for item in chart_data]
        
        # Create the figure
        fig, ax = plt.subplots(1, 1, figsize=figure_size)
        
        # Create bar chart
        bars = ax.bar(range(len(indices)), values, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Color bars with gradient
        if len(values) > 1:
            # Normalize values for coloring
            norm_values = np.array(values)
            norm_values = (norm_values - norm_values.min()) / (norm_values.max() - norm_values.min() + 1e-8)
            colors = plt.cm.get_cmap('viridis')(norm_values)
            for bar, color in zip(bars, colors):
                bar.set_facecolor(color)
        
        # Customize the chart
        ax.set_title(f'{category_info["title"]} - Value Distribution', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(category_info['xlabel'], fontsize=12, fontweight='bold')
        ax.set_ylabel(category_info['ylabel'], fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set x-axis labels
        ax.set_xticks(range(len(indices)))
        if 'torque' in category_name:
            labels = [f'{idx:02d}' for idx in indices]
        else:
            labels = []
            for idx in indices:
                if idx == -1:
                    labels.append('Low')
                elif idx == 999:
                    labels.append('High')
                else:
                    labels.append(f'{idx:03d}')
        
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=10)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                   f'{value:.0f}', ha='center', va='bottom', fontsize=9)
        
        # Add statistics box
        stats_text = f'Properties: {len(chart_data)}\n'
        stats_text += f'Min: {min(values):.1f}\n'
        stats_text += f'Max: {max(values):.1f}\n'
        stats_text += f'Avg: {np.mean(values):.1f}\n'
        stats_text += f'Sum: {sum(values):.1f}'
        
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9),
               verticalalignment='top', horizontalalignment='right', fontsize=10,
               fontfamily='monospace')
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Save PNG
        png_file = os.path.join(output_dir, f'{category_name}_chart.png')
        plt.savefig(png_file, dpi=300, bbox_inches='tight')
        
        # Save CSV data
        csv_file = os.path.join(output_dir, f'{category_name}_numeric_values.csv')
        chart_df = pd.DataFrame(chart_data)
        chart_df = chart_df.rename(columns={'index': 'Numeric_Label', 'value': 'Value', 'column': 'Original_Property'})
        chart_df.to_csv(csv_file, index=False)
        
        plt.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating chart for {category_name}: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 