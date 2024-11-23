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
from datetime import datetime
import hashlib


def hsl_to_rgb(h, s, l):
    """Convert HSL values to RGB hexadecimal color."""
    s /= 100
    l /= 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2

    r, g, b = 0, 0, 0
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    elif 300 <= h < 360:
        r, g, b = c, 0, x

    r, g, b = int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def display_slack_chat(file_path):
    """Display Slack chat messages in a tkinter window."""
    
    def on_mousewheel(event):
        if chat_canvas.winfo_exists():  # Check if the canvas exists before scrolling
            chat_canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def update_scroll_region(event=None):
        chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))

    def format_timestamp(ts):
        try:
            ts_float = float(ts)
            return datetime.fromtimestamp(ts_float).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return "Unknown Time"

    def extract_message_text(message):
        text = ""
        blocks = message.get("blocks", [])
        try:
            for block in blocks:
                if block.get("type") == "rich_text":
                    for element in block.get("elements", []):
                        if element.get("type") == "rich_text_section":
                            text += ''.join(
                                el.get("text", "") if el.get("type") == "text" else el.get("url", "")
                                for el in element.get("elements", []))
        except Exception:
            text = "[Error Extracting Text]"
        return text if text else message.get("text", "[No Text]")

    def create_message_bubble(user_name, text, timestamp, color, deleted=False):
        bubble_frame = tk.Frame(chat_container, bg="white", padx=10, pady=5)
        bubble_frame.pack(fill=tk.X, pady=5)

        user_label = tk.Label(bubble_frame, text=user_name, bg=color, font=("Arial", 10, "bold"), anchor="w")
        user_label.pack(fill=tk.X)

        message_label = tk.Label(bubble_frame, text=text, bg=color, fg="black", wraplength=600, anchor="w", justify="left")
        message_label.pack(fill=tk.X)

        timestamp_label = tk.Label(bubble_frame, text=timestamp, bg="white", fg="gray", font=("Arial", 8), anchor="e")
        timestamp_label.pack(fill=tk.X)

    def get_user_color(user_id):
        """Ensure unique color is assigned to each user based on user_id."""
        if user_id not in user_colors:
            # Generate a numeric value from the user_id using hashing
            hashed_value = int(hashlib.md5(user_id.encode('utf-8')).hexdigest(), 16)
            
            # Generate a unique hue based on the hashed value
            # Using a prime number (137) ensures wide color separation
            hue = (hashed_value * 137) % 360  # Get hue by cycling through the color wheel
            
            # Adjust saturation and lightness for better readability
            saturation = 40  # Moderate saturation to avoid overly vibrant colors
            lightness = 60   # Increase lightness for better contrast and readability
    
            # Convert HSL to RGB (returns hex string)
            user_colors[user_id] = hsl_to_rgb(hue, saturation, lightness)
        
        return user_colors[user_id]

    def display_chat(data):
        for widget in chat_container.winfo_children():
            widget.destroy()

        for message in data:
            if message.get('subtype') == "message_deleted":
                display_deleted_message(message)
            else:
                display_regular_message(message)

    def load_users(folder_path):
        """Load the user data from the users.json file in the selected folder."""
        try:
            # Construct the full path to the users.json file
            users_file_path = os.path.join(folder_path, "users.json")
            
            with open(users_file_path, "r") as f:
                data = json.load(f)
                
                # Ensure the data is a list
                if isinstance(data, list):
                    return data
                else:
                    raise ValueError("The users.json file must be an array of user objects.")
        
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            print(f"Error loading users: {e}")  # Log the error for debugging
            return []

    
    def get_real_name_from_users(user_id):
        """Get the real name of a user from the users.json file."""
        users = load_users(folder_path)  # Load users from the given folder
        if not users:
            return "Unknown User"
        
        # Search for the user in the list by matching the 'id'
        user = next((u for u in users if u.get('id') == user_id), None)
        
        if user:
            return user.get("profile", {}).get("real_name", "Unknown User")
        else:
            return "Unknown User"

    
    def display_regular_message(message):
        # Check if the message contains files (file upload handling)
        if "files" in message and message["files"]:
            # Get the user ID from the message
            user_id = message.get("user", "unknown_user")
            # Use the user ID to fetch the real name from the users.json file
            display_name = get_real_name_from_users(user_id)
            text = f"posted a file or image."
        elif message.get("subtype") == "message_changed":
            # Handle edited messages
            user_profile = message.get("original", {}).get("user_profile", {})
            display_name = user_profile.get("real_name") or "Unknown User"  # Fallback to "Unknown User"
            display_name += " (Edited Message)"  # Append (Edited Message) to the display name
            user_id = message.get("original", {}).get("user", "unknown_user")
            # Get the text from the edited message
            text = extract_message_text(message.get("original", {}))
        elif message.get("subtype") in ["channel_name", "channel_topic", "channel_purpose"]:
            # Handle system messages for channel updates
            user_id = "system"  # Use a placeholder ID for system messages
            display_name = f"System ({message.get('subtype')})"  # Display System with subtype
            text = extract_message_text(message)  # Extract text for channel updates
        else:
            # Regular message handling (not a file upload or edited message)
            user_id = message.get("user", "unknown_user")
            user_profile = message.get("user_profile", {})
            display_name = user_profile.get("real_name") or "Unknown User"  # Fallback to "Unknown User"
            # Get the text from the message
            text = extract_message_text(message)
        
        # Check for attachments and mark the message if there are any, without displaying them again
        if "attachments" in message and message["attachments"]:
            text += "\nThis message has attachments."
        
        # Get the color associated with this user (or bot)
        user_color = get_user_color(user_id)
        
        # Create the message bubble with the correct user or bot details
        create_message_bubble(display_name, text, format_timestamp(message.get("ts", "0")), user_color)

    
    def get_user_name(user_id):
        # Retrieve user profile information based on user_id
        # Assume a function get_user_profile_by_id that fetches the user data by user_id
        user_profile = get_user_profile_by_id(user_id)
        return user_profile.get("real_name", "Unknown User")
    
    def get_user_profile_by_id(user_id):
        # This function simulates fetching the user profile by user_id.
        # Replace this with your actual method to get user profiles.
        user_profiles = {
            "U079R4A554J": {"real_name": "Matthew Baker"},
            "U0664M6ATQE": {"real_name": "Chris Tang"},
            # Add more user profiles here as needed
        }
        return user_profiles.get(user_id, {"real_name": "Unknown User"})


    
    def display_deleted_message(message):
        original_message = message.get("original", {})
        user_id = original_message.get("user", "unknown_user")
        user_profile = original_message.get("user_profile", {})
        user_name = user_profile.get("display_name") or user_profile.get("real_name") or "Unknown User"
        timestamp = format_timestamp(message.get("ts", "0"))
        text = extract_message_text(original_message)

        user_color = get_user_color(user_id)
        create_message_bubble(user_name + " (Deleted)", text, timestamp, user_color, deleted=True)

    user_colors = {}  # Dictionary to hold the user colors

    if not file_path or not os.path.exists(file_path):
        messagebox.showerror("Error", "Invalid file path or file does not exist.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except json.JSONDecodeError as e:
        messagebox.showerror("Error", "Invalid JSON file format.")
        return
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load JSON file: {e}")
        return

    # Create a new window for Slack Chat Viewer
    slack_chat_window = tk.Toplevel()  # Create a new window (Toplevel)
    slack_chat_window.title("Crawlspace Chat Viewer")
    slack_chat_window.geometry("800x600")
    slack_chat_window.iconbitmap("crawl.ico")

    # Layout
    file_path_label = tk.Label(slack_chat_window, text="File Path:")
    file_path_label.pack(pady=5)

    file_path_entry = tk.Entry(slack_chat_window, width=80)
    file_path_entry.pack(pady=5)
    file_path_entry.insert(0, file_path)

    chat_frame = tk.Frame(slack_chat_window)
    chat_frame.pack(fill=tk.BOTH, expand=True)

    chat_canvas = tk.Canvas(chat_frame, bg="white")
    chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=chat_canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    chat_canvas.configure(yscrollcommand=scrollbar.set)

    chat_container = tk.Frame(chat_canvas, bg="white")
    chat_canvas.create_window((0, 0), window=chat_container, anchor="nw")

    chat_canvas.bind_all("<MouseWheel>", on_mousewheel)
    chat_container.bind("<Configure>", update_scroll_region)

    # Call display_chat automatically after loading the file
    display_chat(data)





def load_folder():
    """Load a folder containing JSON files."""
    global folder_path
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

def on_file_path_click(event):
    """Trigger display_slack_chat when file path is clicked."""
    try:
        widget = event.widget
        index = widget.index(f"@{event.x},{event.y}")
        line = widget.get(index + " linestart", index + " lineend")
        match = re.search(r"File Path: (.+)", line)
        if match:
            file_path = match.group(1)
            display_slack_chat(file_path)  # Call display_slack_chat with the file path
        else:
            messagebox.showerror("Error", "No valid file path clicked.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to trigger chat display: {e}")


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
root.title("CrawlSpace - Slack Audit Engine V1.1.0")
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
html_link = ttk.Button(ui_frame, text="Open Conversation Viewer")
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
results_text.bind("<Button-1>", on_file_path_click)
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
