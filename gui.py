import sys
import json
import os
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QTextEdit, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QSpinBox, QSplitter, QMessageBox, QFileDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
                             QInputDialog, QGroupBox, QFormLayout, QMenu, QAbstractItemView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QPixmap, QAction, QIcon, QFont, QColor, QPainter
from PIL import Image

import utils

# ================= Configuration =================
HISTORY_FILE = "history.json"
PROMPTS_FILE = "prompts.json"
OUTPUT_DIR = "outputs"
DEFAULT_MODELS = [
        "Playground-v2.5",
        "StableDiffusionXL",
        "DALL-E-3",
        "Nano-Banana-Pro",
        "Qwen-Image",
        "Flux-Pro"
    ]

# Sci-Fi / Tech Theme Stylesheet
TECH_STYLESHEET = """
QMainWindow {
    background-color: #121212;
    color: #e0e0e0;
}
QWidget {
    background-color: #1e1e24;
    color: #cfd8dc;
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 10pt;
}
QGroupBox {
    border: 1px solid #3f51b5;
    border-radius: 6px;
    margin-top: 12px;
    background-color: #23232e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #82b1ff;
    font-weight: bold;
}
QListWidget, QTableWidget, QTextEdit {
    background-color: #2b2b36;
    border: 1px solid #444;
    border-radius: 4px;
    color: #e0e0e0;
    selection-background-color: #3f51b5;
    selection-color: #ffffff;
    gridline-color: #444;
}
QListWidget::item:hover, QTableWidget::item:hover {
    background-color: #323242;
}
QTableWidget::item:selected {
    background-color: #3f51b5;
    color: white;
    border: none;
    outline: none;
}
QTableWidget::item:focus {
    border: none;
    outline: none;
    background-color: #3f51b5;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #2b2b36;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #82b1ff;
    background-color: #323242;
}
QPushButton {
    background-color: #3f51b5;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    text-transform: uppercase;
}
QPushButton:hover {
    background-color: #5c6bc0;
    border: 1px solid #82b1ff;
}
QPushButton:pressed {
    background-color: #303f9f;
}
QPushButton:disabled {
    background-color: #333;
    color: #666;
    border: none;
}
QHeaderView::section {
    background-color: #23232e;
    color: #82b1ff;
    border: 1px solid #444;
    padding: 6px;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #444;
    background-color: #23232e;
}
QTabBar::tab {
    background-color: #1e1e24;
    color: #aaa;
    padding: 8px 12px;
    border: 1px solid #444;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #3f51b5;
    color: white;
}
QSplitter::handle {
    background-color: #121212;
}
"""

# ================= Custom Widgets =================
class ImageLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.scale_factor = 1.0
        self.offset = QPoint(0, 0)
        self.last_mouse_pos = QPoint(0, 0)
        self.is_panning = False
        
        self.setStyleSheet("""
            border: 2px dashed #444; 
            background-color: #1a1a20; 
            color: #555; 
            font-weight: bold; 
            letter-spacing: 2px;
        """)
        self.setMouseTracking(True)
        
    def set_image(self, file_path):
        if file_path and os.path.exists(file_path):
            self.original_pixmap = QPixmap(file_path)
            self.setText("")
            self.reset_view()
            return True
        else:
            self.clear_image()
            return False

    def clear_image(self):
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.setText("NO SIGNAL")
        self.update()

    def reset_view(self):
        if self.original_pixmap:
            # Calculate initial scale to fit
            s = self.size()
            ps = self.original_pixmap.size()
            
            if not ps.isEmpty():
                width_ratio = s.width() / ps.width()
                height_ratio = s.height() / ps.height()
                self.scale_factor = min(width_ratio, height_ratio, 1.0)
            else:
                self.scale_factor = 1.0
                
            self.offset = QPoint(0, 0)
            self.update_display()

    def update_display(self):
        if self.original_pixmap:
            new_size = self.original_pixmap.size() * self.scale_factor
            if not new_size.isEmpty():
                self.scaled_pixmap = self.original_pixmap.scaled(
                    new_size, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
        self.update()
            
    def resizeEvent(self, event):
        # We don't auto-resize the image box, but if the window is resized, 
        # we might want to re-fit? Actually the user said "image box don't auto change with image".
        # But if the user resizes the window/splitter, we should probably handle it.
        # For now, let's keep it simple.
        super().resizeEvent(event)
        
    def paintEvent(self, event):
        # Draw background and text (if any)
        super().paintEvent(event)
        
        if self.original_pixmap and self.scaled_pixmap:
            painter = QPainter(self)
            # Calculate center position + offset
            rect = self.scaled_pixmap.rect()
            center_pos = self.rect().center() - rect.center() + self.offset
            painter.drawPixmap(center_pos, self.scaled_pixmap)

    def wheelEvent(self, event):
        if self.original_pixmap:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            
            if event.angleDelta().y() > 0:
                self.scale_factor *= zoom_in_factor
            else:
                self.scale_factor *= zoom_out_factor
            
            # Limit scale
            self.scale_factor = max(0.01, min(self.scale_factor, 50.0))
            self.update_display()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.reset_view()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.pos() - self.last_mouse_pos
            self.offset += delta
            self.last_mouse_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

# ================= Worker Thread =================
class GenerationWorker(QThread):
    progress_signal = pyqtSignal(str)  # Log message
    result_signal = pyqtSignal(dict)   # Result data {status, file_path, ...}
    finished_signal = pyqtSignal()

    def __init__(self, api_key, model, prompt, batch_size, output_prefix):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.batch_size = batch_size
        self.output_prefix = output_prefix
        self.is_running = True

    def run(self):
        try:
            # Ensure output directory exists
            if not os.path.exists(OUTPUT_DIR):
                os.makedirs(OUTPUT_DIR)
                
            # Set a longer timeout for image generation (e.g. 5 minutes)
            client = utils.create_client(self.api_key, timeout=300)
            self.progress_signal.emit(f"🚀 Starting generation batch (Total: {self.batch_size})...")
            
            for i in range(self.batch_size):
                if not self.is_running:
                    break
                
                self.progress_signal.emit(f"Generating image {i+1}/{self.batch_size}...")
                
                try:
                    # Create full path: outputs/prefix_1.png
                    base_filename = os.path.join(OUTPUT_DIR, f"{self.output_prefix}.png")
                    output_file = utils.get_unique_filename(base_filename)
                    
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": self.prompt}],
                        stream=False
                    )
                    
                    content = response.choices[0].message.content
                    image_url = utils.get_image_url(content)
                    
                    if image_url:
                        self.progress_signal.emit(f"⬇️ Image URL found. Downloading...")
                        success = utils.download_image(image_url, output_file)
                        if success:
                            self.progress_signal.emit(f"✅ Success: Saved to {output_file}")
                            self.result_signal.emit({
                                "status": "success",
                                "file_path": output_file,
                                "model": self.model,
                                "prompt": self.prompt,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                        else:
                            self.progress_signal.emit(f"❌ Error: Failed to download image.")
                    else:
                        # Check for known error messages from Poe
                        lower_content = content.lower()
                        if "timeout" in lower_content or "network" in lower_content:
                            self.progress_signal.emit(f"⚠️ Poe Server Timeout: The model took too long to respond.")
                            self.progress_signal.emit(f"👉 Suggestion: Try again or switch to a faster model.")
                        else:
                            self.progress_signal.emit(f"⚠️ Error: No image URL found in response.")
                        
                        # Log partial content for debugging
                        preview_len = 200
                        clean_content = content.replace('\n', ' ')[:preview_len]
                        self.progress_signal.emit(f"🔍 Response Content: {clean_content}...")
                        
                except Exception as e:
                    self.progress_signal.emit(f"❌ Error in task {i+1}: {str(e)}")
                
        except Exception as e:
            self.progress_signal.emit(f"🔥 Critical Error: {str(e)}")
        
        self.finished_signal.emit()

    def stop(self):
        self.is_running = False

# ================= Main Window =================
class PoeImageStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poe Image Studio")
        self.resize(1280, 850)
        self.setStyleSheet(TECH_STYLESHEET)
        
        # Data
        self.prompts = []
        self.history = []
        self.load_data()
        
        # UI Components
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Splitter to resize panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        main_layout.addWidget(splitter)
        
        # --- Left Panel: Prompt Manager ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        left_label = QLabel("PROMPT LIBRARY")
        left_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #82b1ff; letter-spacing: 1px;")
        left_layout.addWidget(left_label)
        
        self.prompt_list = QListWidget()
        self.prompt_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.prompt_list.itemClicked.connect(self.load_prompt_from_list)
        left_layout.addWidget(self.prompt_list)
        
        btn_layout = QHBoxLayout()
        self.btn_add_prompt = QPushButton("+ NEW")
        self.btn_add_prompt.setStyleSheet("background-color: #2b2b36; border: 1px solid #555;")
        self.btn_add_prompt.clicked.connect(self.new_prompt)
        
        self.btn_save_prompt = QPushButton("SAVE")
        self.btn_save_prompt.setStyleSheet("background-color: #2b2b36; border: 1px solid #555;")
        self.btn_save_prompt.clicked.connect(self.save_current_prompt)
        
        self.btn_del_prompt = QPushButton("DEL")
        self.btn_del_prompt.setStyleSheet("background-color: #b71c1c; border: none;")
        self.btn_del_prompt.clicked.connect(self.delete_prompt)
        
        btn_layout.addWidget(self.btn_add_prompt)
        btn_layout.addWidget(self.btn_save_prompt)
        btn_layout.addWidget(self.btn_del_prompt)
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_panel)
        
        # --- Middle Panel: Settings & Generation ---
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.setContentsMargins(15, 10, 15, 10)
        
        # Prompt Editing
        mid_layout.addWidget(QLabel("Prompt Title:"))
        self.prompt_title_edit = QLineEdit()
        self.prompt_title_edit.setPlaceholderText("Enter a title for this prompt...")
        mid_layout.addWidget(self.prompt_title_edit)
        
        mid_layout.addWidget(QLabel("Prompt Content:"))
        self.prompt_text_edit = QTextEdit()
        self.prompt_text_edit.setPlaceholderText("Describe your image in detail here...")
        mid_layout.addWidget(self.prompt_text_edit)
        
        # Settings Group
        settings_group = QGroupBox("CONFIGURATION")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(DEFAULT_MODELS)
        self.model_combo.setEditable(True) 
        form_layout.addRow("Model Selection:", self.model_combo)
        
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 10)
        self.batch_spin.setValue(1)
        form_layout.addRow("Batch Quantity:", self.batch_spin)
        
        self.filename_edit = QLineEdit("image")
        self.filename_edit.setPlaceholderText("e.g. cyberpunk_city")
        form_layout.addRow("Filename Prefix:", self.filename_edit)
        
        settings_group.setLayout(form_layout)
        mid_layout.addWidget(settings_group)
        
        # API Key Config
        api_layout = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("POE_API_KEY (Leave empty to use .env)")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(QLabel("API Key:"))
        api_layout.addWidget(self.api_key_edit)
        mid_layout.addLayout(api_layout)
        
        mid_layout.addSpacing(10)

        # Actions
        action_layout = QHBoxLayout()
        self.btn_generate = QPushButton("INITIATE GENERATION")
        self.btn_generate.setFixedHeight(45)
        self.btn_generate.setStyleSheet("background-color: #3f51b5; font-size: 14px; letter-spacing: 1px;")
        self.btn_generate.clicked.connect(self.start_generation)
        
        self.btn_stop = QPushButton("ABORT")
        self.btn_stop.setFixedHeight(45)
        self.btn_stop.setStyleSheet("background-color: #b71c1c; font-size: 14px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_generation)
        
        action_layout.addWidget(self.btn_generate, 3)
        action_layout.addWidget(self.btn_stop, 1)
        mid_layout.addLayout(action_layout)
        
        # Logs
        mid_layout.addWidget(QLabel("SYSTEM LOGS:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(120)
        self.log_output.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; color: #81c784;")
        mid_layout.addWidget(self.log_output)
        
        splitter.addWidget(mid_panel)
        
        # --- Right Panel: History & Preview ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Tab Widget for History/Preview
        tabs = QTabWidget()
        
        # History Tab
        history_widget = QWidget()
        h_layout = QVBoxLayout(history_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["TIME", "MODEL", "PROMPT", "FILE"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Give PROMPT column more space if possible, or keep all stretch
        # Let's make PROMPT stretch more than others? 
        # For simplicity, keep all stretch for now, user can resize if interactive, but ResizeMode.Stretch makes it fixed ratio.
        # Maybe set specific modes: Time (Fixed/ResizeToContents), Model (ResizeToContents), Prompt (Stretch), File (ResizeToContents)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Time
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Model
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Prompt
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # File
        
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.setShowGrid(False)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_history_context_menu)
        self.history_table.itemSelectionChanged.connect(self.on_history_selection_changed)
        h_layout.addWidget(self.history_table)
        tabs.addTab(history_widget, "HISTORY")
        
        right_layout.addWidget(tabs)
        
        # Preview Area
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("PREVIEW:"))
        preview_header.addStretch()
        self.btn_close_preview = QPushButton("✕")
        self.btn_close_preview.setFixedSize(24, 24)
        self.btn_close_preview.setStyleSheet("""
            QPushButton { 
                background-color: #b71c1c; 
                color: white; 
                border-radius: 12px; 
                font-weight: bold;
                padding: 0;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #e53935; }
        """)
        self.btn_close_preview.clicked.connect(self.clear_preview)
        preview_header.addWidget(self.btn_close_preview)
        right_layout.addLayout(preview_header)

        self.preview_label = ImageLabel("NO SIGNAL")
        self.preview_label.setMinimumHeight(350)
        right_layout.addWidget(self.preview_label)
        
        self.btn_open_file = QPushButton("OPEN FILE LOCATION")
        self.btn_open_file.setStyleSheet("background-color: #2b2b36; border: 1px solid #555;")
        self.btn_open_file.clicked.connect(self.open_current_file)
        self.btn_open_file.setEnabled(False)
        right_layout.addWidget(self.btn_open_file)
        
        splitter.addWidget(right_panel)
        
        # Set initial sizes
        splitter.setSizes([250, 500, 450])
        
        self.update_prompt_list()
        self.update_history_table()

    # ================= Data Management =================
    def load_data(self):
        # Load Prompts
        if os.path.exists(PROMPTS_FILE):
            try:
                with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                    self.prompts = json.load(f)
            except:
                self.prompts = []
        
        # Load History
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def save_data(self):
        with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.prompts, f, indent=4, ensure_ascii=False)
            
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=4, ensure_ascii=False)

    # ================= Prompt Logic =================
    def update_prompt_list(self):
        self.prompt_list.clear()
        for p in self.prompts:
            self.prompt_list.addItem(p.get("title", "Untitled"))

    def load_prompt_from_list(self, item):
        idx = self.prompt_list.row(item)
        if 0 <= idx < len(self.prompts):
            data = self.prompts[idx]
            self.prompt_title_edit.setText(data.get("title", ""))
            self.prompt_text_edit.setText(data.get("content", ""))

    def new_prompt(self):
        self.prompt_title_edit.clear()
        self.prompt_text_edit.clear()
        self.prompt_list.clearSelection()

    def save_current_prompt(self):
        title = self.prompt_title_edit.text().strip()
        content = self.prompt_text_edit.toPlainText().strip()
        
        if not title:
            QMessageBox.warning(self, "Error", "Title cannot be empty")
            return
            
        # Check if updating existing or creating new
        selected_items = self.prompt_list.selectedItems()
        if selected_items:
            idx = self.prompt_list.row(selected_items[0])
            self.prompts[idx] = {"title": title, "content": content}
        else:
            self.prompts.append({"title": title, "content": content})
            
        self.save_data()
        self.update_prompt_list()
        self.log(f"System: Prompt '{title}' saved to library.")

    def delete_prompt(self):
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            return
        
        idx = self.prompt_list.row(selected_items[0])
        confirm = QMessageBox.question(self, "Confirm", "Delete this prompt template?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            del self.prompts[idx]
            self.save_data()
            self.update_prompt_list()
            self.new_prompt()

    # ================= Generation Logic =================
    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_output.append(f"{timestamp} {message}")
        # Scroll to bottom
        sb = self.log_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start_generation(self):
        prompt = self.prompt_text_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Error", "Please enter a prompt.")
            return

        model = self.model_combo.currentText()
        batch_size = self.batch_spin.value()
        prefix = self.filename_edit.text().strip() or "image"
        
        # Get API Key
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            api_key = os.getenv("POE_API_KEY")
        
        if not api_key:
            QMessageBox.critical(self, "Error", "API Key is missing. Please set it in .env or the text box.")
            return

        self.btn_generate.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log("System: Initializing generation sequence...")

        self.worker = GenerationWorker(api_key, model, prompt, batch_size, prefix)
        self.worker.progress_signal.connect(self.log)
        self.worker.result_signal.connect(self.handle_generation_result)
        self.worker.finished_signal.connect(self.generation_finished)
        self.worker.start()

    def stop_generation(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.log("System: Aborting sequence...")
            self.btn_stop.setEnabled(False)

    def generation_finished(self):
        self.btn_generate.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.log("System: Sequence completed.")

    def handle_generation_result(self, result):
        if result["status"] == "success":
            self.history.insert(0, result) # Add to top
            self.save_data()
            self.update_history_table()
            # Auto preview latest
            self.show_preview(result["file_path"])

    # ================= History & Preview =================
    def update_history_table(self):
        self.history_table.setRowCount(len(self.history))
        for i, item in enumerate(self.history):
            # Time
            time_item = QTableWidgetItem(item.get("timestamp", ""))
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.history_table.setItem(i, 0, time_item)
            
            # Model
            model_item = QTableWidgetItem(item.get("model", ""))
            model_item.setFlags(model_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.history_table.setItem(i, 1, model_item)

            # Prompt (Truncated)
            full_prompt = item.get("prompt", "")
            # Truncate for display
            display_prompt = (full_prompt[:50] + '...') if len(full_prompt) > 50 else full_prompt
            prompt_item = QTableWidgetItem(display_prompt)
            prompt_item.setToolTip(full_prompt) # Show full prompt on hover
            prompt_item.setFlags(prompt_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.history_table.setItem(i, 2, prompt_item)
            
            # File
            file_item = QTableWidgetItem(os.path.basename(item.get("file_path", "")))
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.history_table.setItem(i, 3, file_item)

    def on_history_selection_changed(self):
        selected_items = self.history_table.selectedItems()
        if selected_items:
            # We get multiple items per row, just take the first one's row
            row = self.history_table.row(selected_items[0])
            self.load_history_preview_by_row(row)

    def load_history_preview_by_row(self, row):
        if 0 <= row < len(self.history):
            file_path = self.history[row].get("file_path", "")
            self.show_preview(file_path)

    def show_history_context_menu(self, pos):
        item = self.history_table.itemAt(pos)
        if not item:
            return
            
        menu = QMenu()
        delete_action = menu.addAction("Delete Record Only")
        delete_file_action = menu.addAction("Delete Record & File")
        
        action = menu.exec(self.history_table.mapToGlobal(pos))
        
        if action:
            row = self.history_table.row(item)
            delete_file = (action == delete_file_action)
            self.delete_history_item(row, delete_file)

    def delete_history_item(self, row, delete_file):
        if 0 <= row < len(self.history):
            item_data = self.history[row]
            file_path = item_data.get("file_path", "")
            
            # Confirm
            msg = "Are you sure you want to delete this history record?"
            if delete_file:
                msg += "\nThe image file will also be permanently deleted."
            
            confirm = QMessageBox.question(self, "Confirm Delete", msg, 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if confirm == QMessageBox.StandardButton.Yes:
                # Remove file if requested
                if delete_file and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Failed to delete file: {e}")
                
                # Remove from data
                del self.history[row]
                self.save_data()
                self.update_history_table()
                
                # Clear preview if it was showing this item
                if hasattr(self, 'current_preview_path') and self.current_preview_path == file_path:
                    self.preview_label.set_image("") # Resets to missing/empty
                    self.btn_open_file.setEnabled(False)

    def show_preview(self, file_path):
        if self.preview_label.set_image(file_path):
            self.current_preview_path = file_path
            self.btn_open_file.setEnabled(True)
        else:
            self.btn_open_file.setEnabled(False)

    def clear_preview(self):
        self.preview_label.clear_image()
        self.current_preview_path = None
        self.btn_open_file.setEnabled(False)

    def open_current_file(self):

        if hasattr(self, 'current_preview_path') and os.path.exists(self.current_preview_path):
            # Windows specific
            os.startfile(self.current_preview_path)
        elif hasattr(self, 'current_preview_path'):
            # Fallback to folder
            folder = os.path.dirname(os.path.abspath(self.current_preview_path))
            os.startfile(folder)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Fix for QFont warning
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    
    window = PoeImageStudio()
    window.show()
    sys.exit(app.exec())
