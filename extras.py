from nicegui import ui, app
import pandas as pd
import os
import json

# --- 1. CONFIGURATION & STYLING ---
ui.dark_mode().enable() # Force Dark Mode

# Custom CSS
ui.add_head_html('''
<style>
    body { background-color: #0E1117; }
    
    /* Responsive Tile Styling */
    .kit-tile {
        background-color: #262730;
        border: 1px solid #363945;
        border-radius: 12px;
        padding: 16px;
        transition: transform 0.2s, border-color 0.2s;
        color: white;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        min-height: 120px;
    }
    .kit-tile:hover {
        border-color: #F4A460;
        transform: translateY(-2px); /* Subtle lift effect */
    }
    
    .tile-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #E0E0E0;
        border-bottom: 1px solid #444;
        padding-bottom: 8px;
        margin-bottom: 12px;
        line-height: 1.3;
        word-wrap: break-word; /* Prevent long words breaking layout */
    }
    
    .stat-label { font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; }
    .stat-val-white { font-size: 1.3rem; font-weight: 500; color: #FFF; }
    .stat-val-orange { font-size: 1.6rem; font-weight: 700; color: #F4A460; }
    
    /* Better spacing for mobile inputs */
    .q-field--outlined .q-field__control { border-radius: 8px; }
</style>
''')

DATA_FILENAME = "master_kit_data.xlsx"
CONFIG_FILENAME = "app_config.json"

# --- 2. DATA LOADING & SORTING ---

def smart_sort_key(val):
    """
    Robust sorting that handles Numbers, Strings, and Dates without crashing.
    """
    # 1. Convert everything to string first (Fixes the 'datetime' error)
    s_val = str(val).strip()
    
    # 2. Check for empty/junk
    if pd.isna(val) or s_val == "" or s_val.lower() in ['nan', 'none', '-', 'nat']:
        return (3, 0, "")
    
    # 3. Try to treat as a Number
    try:
        f_val = float(s_val) # converting the STRING to float is safer
        return (1, f_val, "")
    except (ValueError, TypeError):
        # 4. If it's text (or a date string), treat as Text
        return (2, 0, s_val)

def load_data(file_path):
    valid_sheets = {}
    try:
        xl = pd.read_excel(file_path, sheet_name=None, header=None)
        
        for sheet_name, raw_df in xl.items():
            if raw_df.empty: continue
            
            try:
                # Smart Header Detection
                header_row = None
                for i in range(min(20, len(raw_df))):
                    row = raw_df.iloc[i].astype(str).str.strip().tolist()
                    if "Item" in row and "Packed in Case #" in row:
                        header_row = i
                        break
                
                if header_row is not None:
                    raw_df.columns = raw_df.iloc[header_row]
                    df = raw_df.iloc[header_row + 1:].copy()
                    df.columns = df.columns.astype(str).str.strip()
                    
                    req_cols = ["Item", "Total Quantity", "Packed in Case #"]
                    if set(req_cols).issubset(df.columns):
                        df = df.dropna(subset=["Item"])
                        df["Total Quantity"] = pd.to_numeric(df["Total Quantity"], errors='coerce').fillna(0).astype(int)
                        
                        # Apply Smart Sort
                        df['sort_key'] = df['Packed in Case #'].apply(smart_sort_key)
                        df = df.sort_values(by=['sort_key', 'Item'])
                        df = df.drop(columns=['sort_key'])
                        
                        valid_sheets[sheet_name] = df[req_cols]
            except Exception as e:
                print(f"⚠️ Skipped sheet '{sheet_name}' due to error: {e}")
                continue

    except Exception as e:
        print(f"Critical Error loading file: {e}")
        return {}
        
    return valid_sheets

if os.path.exists(DATA_FILENAME):
    all_sheets = load_data(DATA_FILENAME)
else:
    all_sheets = {}

# --- 3. UI LOGIC ---

loc_map = {k.split("-")[-1].strip() if "-" in k else k: k for k in all_sheets.keys()}
locations = sorted(list(loc_map.keys()))

last_loc = ""
if os.path.exists(CONFIG_FILENAME):
    try:
        with open(CONFIG_FILENAME, "r") as f:
            saved = json.load(f).get("last_location", "")
            if saved in locations: last_loc = saved
    except: pass

# Fallback: Select first location if memory is empty or invalid
if (not last_loc or last_loc not in locations) and locations:
    last_loc = locations[0]

current_df = None
if last_loc and locations:
    current_df = all_sheets.get(loc_map[last_loc])

def update_tiles(e=None):
    search_text = search_input.value
    results_container.clear()
    
    if current_df is None: 
        return

    if search_text:
        filtered = current_df[current_df["Item"].astype(str).str.contains(search_text, case=False, na=False)]
    else:
        filtered = current_df
    
    if filtered.empty:
        with results_container:
            ui.label("No items found.").classes('text-white text-lg opacity-50')
        return

    with results_container:
        # Responsive Grid: 1 col mobile -> 2 col tablet -> 3 col laptop -> 4 col desktop
        with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 w-full'):
            for _, row in filtered.iterrows():
                case_val = str(row['Packed in Case #'])
                if case_val.lower() in ['nan', 'none', '', 'nat']: case_val = "-"
                
                with ui.element('div').classes('kit-tile'):
                    ui.label(row["Item"]).classes('tile-header')
                    
                    with ui.row().classes('w-full justify-between items-center'):
                        # Qty
                        with ui.column().classes('items-center gap-0'):
                            ui.label('QTY').classes('stat-label')
                            ui.label(str(row["Total Quantity"])).classes('stat-val-white')
                        
                        # Divider
                        ui.element('div').style('height: 40px; border-left: 1px solid #444;')

                        # Case
                        with ui.column().classes('items-center gap-0'):
                            ui.label('CASE').classes('stat-label')
                            ui.label(case_val).classes('stat-val-orange')

def on_location_change(e):
    global current_df
    new_loc = e.value
    if new_loc:
        current_df = all_sheets.get(loc_map[new_loc])
        with open(CONFIG_FILENAME, "w") as f: json.dump({"last_location": new_loc}, f)
        search_input.value = ""
        update_tiles()

def handle_upload(e):
    with open(DATA_FILENAME, "wb") as f: f.write(e.content.read())
    ui.notify("File Updated! Reloading...", type='positive')
    
    global all_sheets, locations, loc_map, current_df, last_loc
    all_sheets = load_data(DATA_FILENAME)
    loc_map = {k.split("-")[-1].strip() if "-" in k else k: k for k in all_sheets.keys()}
    locations = sorted(list(loc_map.keys()))
    
    location_selector.options = locations
    if locations:
        location_selector.value = locations[0]
        location_selector.enable()
        last_loc = locations[0]
        current_df = all_sheets.get(loc_map[locations[0]])
        update_tiles()
    else:
        location_selector.value = None
        location_selector.disable()
        current_df = None
        results_container.clear()
        
    upload_dialog.close()

# --- 4. LAYOUT ---
with ui.column().classes('w-full max-w-7xl mx-auto p-4'):
    
    # Header Area
    with ui.row().classes('w-full justify-between items-center mb-6 gap-4 flex-wrap'):
        # Title
        with ui.row().classes('items-center gap-2'):
            ui.label("📦").classes('text-3xl sm:text-4xl')
            ui.label("Kit Locator").classes('text-xl sm:text-2xl font-bold text-white')
        
        # Controls Group
        with ui.row().classes('items-center gap-3 flex-wrap'):
            # Upload Button
            with ui.dialog() as upload_dialog, ui.card().classes('bg-[#262730] text-white'):
                ui.label("Update Master List").classes('text-xl font-bold mb-4')
                ui.upload(on_upload=handle_upload, auto_upload=True).props('accept=".xlsx" dark')
                ui.button('Close', on_click=upload_dialog.close).classes('mt-4 w-full')

            ui.button('Update', on_click=upload_dialog.open).props('outline color=orange icon=upload').classes('text-sm')

            # Dropdown - SAFE INIT (Handles empty list)
            # We set value to None if locations is empty to prevent crash
            sel_val = last_loc if (locations and last_loc in locations) else (locations[0] if locations else None)
            
            location_selector = ui.select(locations, value=sel_val, on_change=on_location_change)\
                .classes('w-full sm:w-64')\
                .props('outlined input-class="text-orange-400"')
            
            if not locations:
                location_selector.disable()

    if not locations:
        ui.label("⚠️ No Data Found. Upload a file.").classes('text-red-400 text-xl')
    else:
        # Search Bar
        search_input = ui.input(placeholder='🔍 Type item name...')\
            .classes('w-full mb-6 text-lg')\
            .props('autofocus outlined rounded input-class="text-white" clearable')\
            .on_value_change(update_tiles) 

        # Results Grid
        results_container = ui.column().classes('w-full')
        update_tiles()

import os

# Cloud hosting assigns a port automatically in the environment variables
# If running locally, it defaults to 8080
port = int(os.environ.get("PORT", 8080))

ui.run(title="Kit Locator", dark=True, host='0.0.0.0', port=port)