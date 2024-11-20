import threading
import time
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import re
import os

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




# Main Application
root = tk.Tk()
root.title("CrawlSpace - Slack Audit Engine V0.2.2")
root.geometry("900x750")
root.iconbitmap("crawl.ico")

# Global variables
folder_data = None
total_files = 0

# Frame for organizing widgets
frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# Center alignment for the frame
for i in range(11):  # Number of rows to match the widgets
    frame.grid_rowconfigure(i, weight=1)
frame.grid_columnconfigure(0, weight=1)

# Load Folder Button and Labels
folder_button = ttk.Button(frame, text="Select Folder", command=load_folder)
folder_button.grid(row=0, column=0, pady=5, padx=5, sticky=tk.N)

folder_label = ttk.Label(frame, text="Folder: None selected", font=("Arial", 10))
folder_label.grid(row=1, column=0, pady=5)

file_count_label = ttk.Label(frame, text=f"Total JSON Files: {total_files}", font=("Arial", 10))
file_count_label.grid(row=2, column=0, pady=5)

# Load Search Words Button
load_words_button = ttk.Button(frame, text="Load Search Words", command=load_search_words)
load_words_button.grid(row=3, column=0, pady=5)

# Search Words Entry
search_words_label = ttk.Label(frame, text="Search Words (Click Here for citeria):")
search_words_label.grid(row=4, column=0, pady=5)
search_words_label.bind("<Button-1>", lambda e: show_search_criteria_info())  # Open info window on click
search_words_entry = tk.Text(frame, wrap=tk.WORD, height=10, width=50)
search_words_entry.grid(row=5, column=0, pady=5)

# Search Button
search_button = ttk.Button(frame, text="Search", command=search_words)
search_button.grid(row=6, column=0, pady=10)

# Progress Bar
progress_bar = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate")
progress_bar.grid(row=7, column=0, pady=10)

# Results Count Label
results_label = ttk.Label(frame, text="", font=("Arial", 10, "bold"), foreground="blue")
results_label.grid(row=9, column=0, pady=5)

# Results Text Widget with Scrollbar
results_frame = ttk.Frame(frame)  # Frame to hold the text widget and scrollbar
results_frame.grid(row=10, column=0, pady=5, sticky=(tk.W, tk.E))

results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical")
results_text = tk.Text(results_frame, wrap=tk.WORD, height=15, width=80, yscrollcommand=results_scrollbar.set)
results_scrollbar.config(command=results_text.yview)

results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

results_text.config(state=tk.DISABLED)

# Add a progress label to show file count (moved to row 8)
progress_label = ttk.Label(frame, text="Files Scanned: 0/0", font=("Arial", 10))
progress_label.grid(row=8, column=0, pady=5)

root.mainloop()
