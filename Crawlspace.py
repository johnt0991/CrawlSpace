import webbrowser
import threading
import time
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import re
import os
import sys
import shutil

def load_folder():
    """Load a folder containing JSON files."""
    folder_path = filedialog.askdirectory()
    if folder_path:
        global folder_data, total_files
        folder_data = folder_path
        folder_label.config(text=f"Folder: {folder_path}")

        # Count total .json files in the folder
        total_files = sum(len(files) for _, _, files in os.walk(folder_data) if any(f.endswith(".json") for f in files))
        
        # Update the file count label
        file_count_label.config(text=f"Total JSON Files: {total_files}")

        progress_label.config(text=f"Files Scanned: 0/{total_files}")

def load_search_words():
    """Load a list of search words from a file."""
    file_path = filedialog.askopenfilename(
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                words = [line.strip() for line in file if line.strip()]
                search_words_entry.delete(1.0, tk.END)
                search_words_entry.insert(tk.END, "\n".join(words))
            messagebox.showinfo("Success", "Search words loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load search words: {e}")

def show_search_criteria_info():
    """Show a small window with instructions on how to use the search feature."""
    info_window = tk.Toplevel(root)
    info_window.title("Search Criteria Instructions")
    info_window.geometry("400x200")
    info_window.iconbitmap("crawl.ico")
    
    # Get the mouse position
    mouse_x = root.winfo_pointerx()
    mouse_y = root.winfo_pointery()
    
    # Position the popup window at the mouse location
    info_window.geometry(f"+{mouse_x}+{mouse_y}")
    
    info_label = ttk.Label(info_window, text=(
        "Search Criteria Format:\n\n"
        "- Enter one word per line to search for individual words.\n"
        "- Use multiple words on a single line for a phrase search.\n"
        "- Words are NOT case-insensitive.\n"
        "- The search will find matches for any word or phrase.\n"
        "- You can mix single words and phrases."
    ))
    info_label.pack(pady=10, padx=10)

    close_button = ttk.Button(info_window, text="Close", command=info_window.destroy)
    close_button.pack(pady=5)

def search_words():
    """Search for multiple words in all JSON files within the selected folder."""
    if not folder_data:
        messagebox.showerror("Error", "No folder selected!")
        return

    words = search_words_entry.get(1.0, tk.END).strip().splitlines()
    if not words:
        messagebox.showerror("Error", "Please enter or load search words.")
        return

    # Disable buttons during search
    search_button.config(state=tk.DISABLED)
    load_words_button.config(state=tk.DISABLED)
    search_words_label.config(state=tk.DISABLED)
    folder_button.config(state=tk.DISABLED)
    search_words_entry.config(state=tk.DISABLED)

    # Clear previous results
    results_text.config(state=tk.NORMAL)
    results_text.delete(1.0, tk.END)
    results_label.config(text="")
    progress_bar["value"] = 0
    progress_label.config(text="Files Scanned: 0/0")

    results = []

    def perform_search():
        """Run the search in a separate thread to avoid blocking the UI."""
        try:
            # Start the timer
            start_time = time.time()

            def extract_sentences(value, word_groups):
                """Extract sentences containing exact words or all words in a phrase (in any order)."""
                sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', value)
                return [
                    sentence
                    for sentence in sentences
                    if any(
                        all(re.search(r'\b{}\b'.format(re.escape(word)), sentence, re.IGNORECASE) for word in group)
                        for group in word_groups
                    )
                ]

            def find_real_name(data):
                """Find the real name in the JSON data, including for deleted messages."""
                if isinstance(data, dict):
                    # Check for regular message
                    if "user_profile" in data:
                        return data["user_profile"].get("real_name", "N/A")
                    
                    # Check for deleted message (real name is under 'original.user_profile')
                    elif "subtype" in data and data["subtype"] == "message_deleted" and "original" in data:
                        return data["original"].get("user_profile", {}).get("real_name", "N/A")
                
                return "N/A"

            def scan_dict(d, file_path, word_groups):
                """Scan dictionary for text and deleted messages."""
                real_name = find_real_name(d)
            
                # Handle regular messages
                if "text" in d and isinstance(d["text"], str):
                    sentences = extract_sentences(d["text"], word_groups)
                    for sentence in sentences:
                        highlighted_sentence = sentence
                        for word in sum(word_groups, []):  # Flatten word_groups to highlight individual words
                            highlighted_sentence = re.sub(
                                rf"(\b{re.escape(word)}\b)", r"*\1*", highlighted_sentence, flags=re.IGNORECASE
                            )
                        results.append((real_name, highlighted_sentence, file_path))
            
                # Handle deleted messages
                if d.get("subtype") == "message_deleted" and "original" in d and isinstance(d["original"], dict):
                    original_text = d["original"].get("text", "")
                    if original_text:
                        sentences = extract_sentences(original_text, word_groups)
                        for sentence in sentences:
                            highlighted_sentence = sentence
                            for word in sum(word_groups, []):  # Flatten word_groups to highlight individual words
                                highlighted_sentence = re.sub(
                                    rf"(\b{re.escape(word)}\b)", r"*\1*", highlighted_sentence, flags=re.IGNORECASE
                                )
                            results.append(
                                (f"{real_name} (Deleted Message)", highlighted_sentence, file_path)
                            )

            # Process search words into groups (single words or multi-word phrases on the same line)
            word_groups = [line.strip().split() for line in words if line.strip()]

            # Count total files for progress tracking
            total_files = sum(len(files) for _, _, files in os.walk(folder_data))
            current_file = 0

            # Loop through all JSON files in the folder
            for dirpath, _, files in os.walk(folder_data):
                for file in files:
                    if file.endswith(".json"):
                        file_path = os.path.join(dirpath, file)
                        current_file += 1
                        progress_bar["value"] = (current_file / total_files) * 100
                        progress_label.config(
                            text=f"Files Scanned: {current_file}/{total_files}"
                        )
                        root.update_idletasks()

                        try:
                            with open(file_path, "r", encoding="utf-8") as json_file:
                                data = json.load(json_file)
                                if isinstance(data, dict):
                                    scan_dict(data, file_path, word_groups)
                                elif isinstance(data, list):
                                    for item in data:
                                        if isinstance(item, dict):
                                            scan_dict(item, file_path, word_groups)
                        except Exception as e:
                            messagebox.showerror("Error", f"Error reading file {file_path}: {e}")

            # Stop the timer
            end_time = time.time()
            elapsed_time = end_time - start_time

            # Display results
            if results:
                for real_name, highlighted_sentence, file_path in results:
                    result_text = f"Real Name: {real_name}\nMatch: {highlighted_sentence}\nFile Path: {file_path}\n{'-'*50}\n"
                    results_text.insert(tk.END, result_text)

                results_label.config(
                    text=f"Total Results Found: {len(results)} in {elapsed_time:.2f} seconds"
                )
            else:
                results_label.config(
                    text=f"No matches found for the search words in {elapsed_time:.2f} seconds"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Error during search: {e}")
        finally:
            # Re-enable buttons after the search is complete
            search_button.config(state=tk.NORMAL)
            load_words_button.config(state=tk.NORMAL)
            search_words_label.config(state=tk.NORMAL)
            folder_button.config(state=tk.NORMAL)
            search_words_entry.config(state=tk.NORMAL)

            results_text.config(state=tk.DISABLED)

    # Run the search in a separate thread
    threading.Thread(target=perform_search, daemon=True).start()

def copy_to_clipboard(event):
    """Copy the clicked file path to the clipboard."""
    try:
        widget = event.widget
        index = widget.index(f"@{event.x},{event.y}")
        line = widget.get(index + " linestart", index + " lineend")
        match = re.search(r"File Path: (.+)", line)
        if match:
            file_path = match.group(1)
            root.clipboard_clear()
            root.clipboard_append(file_path)
            root.update()
            messagebox.showinfo("Copied", f"File path copied to clipboard:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to copy file path: {e}")

def on_hover(event):
    """Change the mouse cursor to a hand when hovering over file paths."""
    widget = event.widget
    try:
        index = widget.index(f"@{event.x},{event.y}")
        line = widget.get(index + " linestart", index + " lineend")
        
        # Check if the line contains 'File Path:'
        if "File Path:" in line:
            widget.config(cursor="hand2")  # Set cursor to hand pointer
        else:
            widget.config(cursor="")  # Reset cursor if not on file path
    except Exception as e:
        widget.config(cursor="")  # Reset cursor if there's an error

def open_html_file():
    """Open main.html located in the same directory as this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "viewer.html")
    if os.path.exists(html_path):
        webbrowser.open(f"file://{html_path}")
    else:
        messagebox.showerror("Error", f"main.html not found in:\n{script_dir}")

def resource_path(relative_path):
    """Get the correct path to bundled resources when running with PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def ensure_icon_exists(icon_path):
    """Ensure the icon file exists in the right directory."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller will bundle the icon in the temporary directory, ensure it's copied to the working directory
        dest_path = os.path.join(os.getcwd(), "crawl.ico")
        if not os.path.exists(dest_path):
            shutil.copy(icon_path, dest_path)
        return dest_path
    return icon_path

# Main Application
root = tk.Tk()

# Load the icon using the resource_path function
icon_path = resource_path("crawl.ico")
icon_path = ensure_icon_exists(icon_path)
root.iconbitmap(icon_path)  # Set the icon
root.title("CrawlSpace - Slack Audit Engine V1.0.0")
root.geometry("900x700")
root.iconbitmap("crawl.ico")


# Lock the window size (disable resizing)
root.resizable(False, False)

# Global variables
folder_data = None
total_files = 0

# Frame for organizing widgets
frame = ttk.Frame(root, padding="10", relief="solid", borderwidth=2)
frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
root.grid_columnconfigure(0, weight=1)
frame.grid_columnconfigure(0, weight=1)


# UI Frame
ui_frame = ttk.Frame(frame, padding="10", relief="solid", borderwidth=2)
ui_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
ui_frame.columnconfigure(0, minsize=150)
ui_frame.columnconfigure(1, minsize=400, weight=1)
ui_frame.columnconfigure(2, minsize=150)

# ROW 0
# Load Folder Button and Labels
folder_button = ttk.Button(ui_frame, text="Select Folder", command=load_folder)
folder_button.grid(row=0, column=0, pady=5, padx=5, sticky=(tk.N, tk.W))

folder_label = ttk.Label(ui_frame, text="Folder: None selected", font=("Arial", 10), relief="solid", borderwidth=2, width=75)
folder_label.grid(row=0, column=1, pady=5, sticky=tk.W, columnspan=2)

# Add a clickable label in the top-right corner to open the HTML file
html_link = ttk.Button(ui_frame, text="Open HTML File")
html_link.grid(row=0, column=2, pady=5, padx=5, sticky=tk.E)
html_link.bind("<Button-1>", lambda e: open_html_file())

# ROW 1

# Load Search Words Button
load_words_button = ttk.Button(ui_frame, text="Load Search Words", command=load_search_words)
load_words_button.grid(row=1, column=0, pady=5, padx=5, sticky=(tk.N, tk.W))

search_words_entry = tk.Text(ui_frame, wrap=tk.WORD, height=10, width=40, relief="solid", borderwidth=2)
search_words_entry.grid(row=1, column=1, rowspan=3, sticky=tk.W, pady=5)

# Row 2

# Search Button
search_button = ttk.Button(ui_frame, text="Search", command=search_words)
search_button.grid(row=4, column=0, pady=5, sticky=(tk.N, tk.W))

# Row 3

# Row 4

# Search Button
search_button = ttk.Button(ui_frame, text="Search", command=search_words)
search_button.grid(row=4, column=0, pady=5, sticky=(tk.N, tk.W))

# Search Words Entry
search_words_label = ttk.Label(ui_frame, text="(Click Here for citeria)")
search_words_label.grid(row=4, column=1, pady=5, sticky=(tk.N,tk.W, tk.E))
search_words_label.bind("<Button-1>", lambda e: show_search_criteria_info())  # Open info window on click




# Results Frame
results_frame = ttk.Frame(frame, padding="10", relief="solid", borderwidth=2)
results_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
results_frame.columnconfigure(0, minsize=150)
results_frame.columnconfigure(1, minsize=400, weight=1)
results_frame.columnconfigure(2, minsize=150)


# Row 0
# Results Text Widget with Scrollbar
results_content = ttk.Frame(results_frame)  # Frame to hold the text widget and scrollbar
results_content.grid(row=0, column=0, columnspan=4, pady=5, sticky=(tk.W, tk.E))

results_scrollbar = ttk.Scrollbar(results_content, orient="vertical")
results_text = tk.Text(results_content, wrap=tk.WORD, height=15, yscrollcommand=results_scrollbar.set, relief="solid", borderwidth=2)
results_scrollbar.config(command=results_text.yview)

results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

results_text.config(state=tk.DISABLED)

# Bind click events to the results text widget
results_text.bind("<Button-1>", copy_to_clipboard)
results_text.bind("<Motion>", on_hover)  # When mouse moves over the widget


# Row 1
# Add a progress label to show file count (moved to row 8)
progress_label = ttk.Label(results_frame, text="Files Scanned: 0/0", font=("Arial", 10))
progress_label.grid(row=1, column=0, pady=5, sticky=tk.W)

# Progress Bar
progress_bar = ttk.Progressbar(results_frame, orient="horizontal", length=400, mode="determinate")
progress_bar.grid(row=1, column=1, pady=10, columnspan=1)

# Total file count loaded
file_count_label = ttk.Label(results_frame, text=f"Total JSON Files: {total_files}", font=("Arial", 10))
file_count_label.grid(row=1, column=2, pady=5, sticky=tk.E)

# Row 2
# Results Count Label
results_label = ttk.Label(results_frame, text="", font=("Arial", 10, "bold"), foreground="blue")
results_label.grid(row=2, column=1, pady=5)


root.mainloop()
