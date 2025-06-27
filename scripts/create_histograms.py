import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

# === CONFIG ===
MASTER_CSV = "csv_outputs/motor_data_master.csv"
OUTPUT_DIR = "histogram_outputs"
FIGURE_SIZE = (14, 8)

# Create output directory if it doesn't exist
Path(OUTPUT_DIR).mkdir(exist_ok=True)

print("📊 Creating property value bar charts from master motor data...")

# Check if master CSV exists
if not os.path.exists(MASTER_CSV):
    print(f"❌ Master CSV file not found: {MASTER_CSV}")
    exit(1)

print(f"✅ Found master CSV file: {MASTER_CSV}")

try:
    # Read master CSV file
    df = pd.read_csv(MASTER_CSV)
    print(f"📊 Loaded {len(df)} rows from master CSV")
    
    if len(df) == 0:
        print("❌ Master CSV file is empty")
        exit(1)
    
    # Define motor data categories
    categories = {
        'power': ['Motor.Power', 'motorpower'],
        'torque': ['Motor.Torque', 'motortorque'],
        'motor_temp': ['Motor.Temperature', 'motortemperature'],
        'mosfet_temp': ['MOSFET.Temperature', 'mosfettemperature'], 
        'motor_cooldown': ['Motor.Cooldown', 'motorcooldown'],
        'mosfet_cooldown': ['MOSFET.Cooldown', 'mosfetcooldown']
    }
    
    # Process each category
    for category, keywords in categories.items():
        print(f"\n🔍 Processing category: {category}")
        
        # Skip cooldown files for now
        if 'cooldown' in category:
            print(f"   ⏭️  Skipping cooldown category: {category}")
            continue
        
        # Find columns that match this category
        category_columns = []
        for col in df.columns:
            if col != 'timestamp':
                col_lower = col.lower()
                if any(keyword.lower() in col_lower for keyword in keywords):
                    category_columns.append(col)
        
        if not category_columns:
            print(f"   ❌ No columns found for category: {category}")
            continue
        
        print(f"   ✅ Found {len(category_columns)} columns for {category}")
        
        # Use the most recent row (last row) for values
        latest_row = df.iloc[-1]
        
        # Get property names and their values
        property_data = []
        
        for col in category_columns:
            try:
                value = latest_row[col]
                
                # Try to convert to numeric
                try:
                    numeric_value = float(value)
                    if not np.isnan(numeric_value):
                        # Extract numeric suffix from property name
                        if 'torque' in col.lower():
                            # For torque, extract last 2 digits
                            match = re.search(r'(\d{2})$', col)
                            if match:
                                numeric_label = int(match.group(1))
                                property_data.append((numeric_label, numeric_value, col))
                        else:
                            # For temp/power, extract last 3 digits or handle special .Low properties
                            match = re.search(r'(\d{3})$', col)
                            if match:
                                numeric_label = int(match.group(1))
                                property_data.append((numeric_label, numeric_value, col))
                            elif col.lower().endswith('.low') and ('temp' in category):
                                # Special case for temperature .Low properties (values < 20)
                                numeric_label = -1  # Put at the beginning (before 020, 030, etc.)
                                property_data.append((numeric_label, numeric_value, col))
                                print(f"   ✅ Including temperature .Low property: {col}")
                            else:
                                print(f"   ⚠️  Could not extract numeric suffix from: {col}")
                except (ValueError, TypeError):
                    print(f"   ⚠️  Skipping non-numeric property: {col} = {value}")
                    continue
                    
            except Exception as e:
                print(f"   ⚠️  Error processing column {col}: {e}")
                continue
        
        if not property_data:
            print(f"   ❌ No valid properties found for category: {category}")
            continue
            
        # Sort by numeric label to get correct order
        property_data.sort(key=lambda x: x[0])
        
        # For torque and power, remove the lowest index (the first big bar)
        if ('torque' in category or 'power' in category) and len(property_data) > 1:
            property_data = property_data[1:]  # Remove the first (lowest) index
        
        # Extract sorted data
        numeric_labels = [item[0] for item in property_data]
        property_values = [item[1] for item in property_data]
        property_names = [item[2] for item in property_data]
        
        print(f"   📈 Creating bar chart for {len(property_data)} properties")
        
        # Create single figure
        fig, ax = plt.subplots(1, 1, figsize=FIGURE_SIZE)
        
        # Create bar chart
        x_positions = range(len(numeric_labels))
        bars = ax.bar(x_positions, property_values, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Customize the plot
        category_title = category.replace("_", " ").title()
        ax.set_title(f'{category_title} - Values by Numeric Index', fontsize=16, fontweight='bold', pad=20)
        if 'torque' in category:
            ax.set_xlabel('Torque Index (Last 2 Digits)', fontsize=14, fontweight='bold')
        else:
            ax.set_xlabel('Index (Last 3 Digits)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Values', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set x-axis labels to show numeric labels (handle special .Low properties)
        ax.set_xticks(x_positions)
        if 'torque' in category:
            # For torque, show as 2-digit format
            ax.set_xticklabels([f'{label:02d}' for label in numeric_labels], rotation=0, fontsize=10)
        else:
            # For temp/power, show as 3-digit format, but handle .Low as special case
            x_labels = []
            for label in numeric_labels:
                if label == -1:
                    x_labels.append('Low')
                else:
                    x_labels.append(f'{label:03d}')
            ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=10)
        
        # Color bars with a gradient based on value
        if len(property_values) > 1:
            # Normalize values for color mapping
            min_val = min(property_values)
            max_val = max(property_values)
            if max_val > min_val:
                normalized_values = [(val - min_val) / (max_val - min_val) for val in property_values]
            else:
                normalized_values = [0.5] * len(property_values)
            
            colors = plt.cm.get_cmap('viridis')(normalized_values)
            for bar, color in zip(bars, colors):
                bar.set_facecolor(color)
        else:
            bars[0].set_facecolor(plt.cm.get_cmap('viridis')(0.5))
        
        # Add value labels on top of bars
        max_value = max(property_values) if property_values else 0
        for i, (bar, value) in enumerate(zip(bars, property_values)):
            height = bar.get_height()
            # Show value on top of bar
            ax.text(bar.get_x() + bar.get_width()/2., height + max_value*0.01,
                   f'{value:.0f}', ha='center', va='bottom', fontsize=8)
        
        # Add statistics text box
        stats_text = f'Properties: {len(property_data)}\n'
        stats_text += f'Min Value: {min(property_values):.0f}\n'
        stats_text += f'Max Value: {max(property_values):.0f}\n'
        stats_text += f'Average: {sum(property_values)/len(property_values):.1f}\n'
        
        # Find properties with min and max values
        min_idx = property_values.index(min(property_values))
        max_idx = property_values.index(max(property_values))
        stats_text += f'Min: {numeric_labels[min_idx]}\n'
        stats_text += f'Max: {numeric_labels[max_idx]}'
        
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, 
               bbox=dict(boxstyle='round,pad=0.8', facecolor='white', alpha=0.9, edgecolor='gray'),
               verticalalignment='top', horizontalalignment='right', fontsize=10,
               fontfamily='monospace')
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        output_file = f"{OUTPUT_DIR}/{category}_numeric_values.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved bar chart: {output_file}")
        
        # Create detailed property values file
        values_file = f"{OUTPUT_DIR}/{category}_numeric_values.csv"
        
        # Create property values DataFrame
        values_df = pd.DataFrame({
            'Numeric_Label': numeric_labels,
            'Value': property_values,
            'Original_Property': property_names
        })
        values_df.to_csv(values_file, index=False)
        print(f"   📊 Saved property values: {values_file}")
        
        plt.close()  # Close to free memory

except Exception as e:
    print(f"❌ Error processing master CSV: {str(e)}")
    exit(1)

print(f"\n🎉 Numeric indexed bar chart generation complete!")
print(f"📁 Check the '{OUTPUT_DIR}' folder for your numeric indexed bar charts")
print(f"🔍 Generated files:")

# List generated files
chart_files = glob.glob(f"{OUTPUT_DIR}/*_numeric_values.png")
data_files = glob.glob(f"{OUTPUT_DIR}/*_numeric_values.csv")

for file in sorted(chart_files + data_files):
    file_size = os.path.getsize(file) / 1024  # Size in KB
    print(f"   📄 {file} ({file_size:.1f} KB)") 