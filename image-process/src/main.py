from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
DISPLAY_MAX_SIZE = (360, 360)
STAGE_PREVIEW_SIZE = (220, 220)
BATCH_SUFFIX = "_processed"
GRAYSCALE_WEIGHTS = (30, 59, 11)
GRAYSCALE_EXPR = f"({GRAYSCALE_WEIGHTS[0]}*r + {GRAYSCALE_WEIGHTS[1]}*g + {GRAYSCALE_WEIGHTS[2]}*b) / 100"

MODE_GRAYSCALE = "grayscale"
MODE_CUSTOM = "custom_rgb"


@dataclass(slots=True)
class PipelineOperation:
    mode: str
    red_expr: str
    green_expr: str
    blue_expr: str


class ImageLabel(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setScaledContents(False)
        self.setWordWrap(True)


class StageImageLabel(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(*STAGE_PREVIEW_SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setScaledContents(False)
        self.setWordWrap(True)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Filter Viewer")
        self.resize(1480, 920)
        self.setMinimumSize(1120, 760)

        self.current_directory: Path | None = None
        self.image_paths: list[Path] = []
        self.original_image: Image.Image | None = None
        self.preview_image: Image.Image | None = None
        self.original_pixmap: QPixmap | None = None
        self.filtered_pixmap: QPixmap | None = None

        self.batch_input_directory: Path | None = None
        self.batch_output_directory: Path | None = None

        self.pipeline_operations: list[PipelineOperation] = []
        self._syncing_operation_editor = False

        self.image_list = QListWidget()
        self.image_list.currentRowChanged.connect(self.on_image_selected)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setWordWrap(True)

        self.original_label = ImageLabel("No image selected")
        self.filtered_label = ImageLabel("No image selected")

        self.gray_radio = QRadioButton("Grayscale")
        self.custom_radio = QRadioButton("Custom RGB expression")
        self.custom_radio.setChecked(True)

        for radio in [self.gray_radio, self.custom_radio]:
            radio.toggled.connect(self.on_filter_toggled)

        self.red_expr_input = QLineEdit("r")
        self.green_expr_input = QLineEdit("g")
        self.blue_expr_input = QLineEdit("b")

        for expr_input in [self.red_expr_input, self.green_expr_input, self.blue_expr_input]:
            expr_input.textChanged.connect(self.on_custom_expression_changed)

        self.output_red_label = QLabel()
        self.output_green_label = QLabel()
        self.output_blue_label = QLabel()
        self.output_details_label = QLabel()
        self.output_details_label.setWordWrap(True)

        self.pipeline_list = QListWidget()
        self.pipeline_list.currentRowChanged.connect(self.on_pipeline_selection_changed)

        self.pipeline_help_label = QLabel(
            "Select a pipeline step to edit it live. Clear the selection to draft a new step, then add it."
        )
        self.pipeline_help_label.setWordWrap(True)

        self.pipeline_stage_scroll = QScrollArea()
        self.pipeline_stage_scroll.setWidgetResizable(True)
        self.pipeline_stage_container = QWidget()
        self.pipeline_stage_layout = QHBoxLayout()
        self.pipeline_stage_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.pipeline_stage_container.setLayout(self.pipeline_stage_layout)
        self.pipeline_stage_scroll.setWidget(self.pipeline_stage_container)

        self.batch_input_label = QLabel("No input folder selected")
        self.batch_input_label.setWordWrap(True)

        self.batch_output_label = QLabel("No output folder selected")
        self.batch_output_label.setWordWrap(True)

        self.batch_summary_label = QLabel()
        self.batch_summary_label.setWordWrap(True)

        self.batch_status_label = QLabel("No batch job has been run yet")
        self.batch_status_label.setWordWrap(True)

        self._build_ui()
        self.update_operation_output_preview()
        self.update_pipeline_buttons()
        self.update_batch_settings_summary()
        self.refresh_pipeline_stage_previews([])

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_prototype_tab(), "Prototype")
        tabs.addTab(self._build_batch_tab(), "Batch Process")
        self.setCentralWidget(tabs)

    def _build_prototype_tab(self) -> QWidget:
        tab = QWidget()

        open_folder_button = QPushButton("Open Folder")
        open_folder_button.clicked.connect(self.open_folder)

        open_image_button = QPushButton("Open Image")
        open_image_button.clicked.connect(self.open_image_file)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(open_folder_button)
        controls_layout.addWidget(open_image_button)
        controls_layout.addWidget(self.folder_label, stretch=1)

        filter_group = QGroupBox("Operation mode")
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(self.gray_radio)
        filter_layout.addWidget(self.custom_radio)
        filter_group.setLayout(filter_layout)

        expression_group = QGroupBox("Custom channel expressions")
        expression_layout = QGridLayout()
        expression_layout.addWidget(QLabel("Output Red"), 0, 0)
        expression_layout.addWidget(self.red_expr_input, 0, 1)
        expression_layout.addWidget(QLabel("Output Green"), 1, 0)
        expression_layout.addWidget(self.green_expr_input, 1, 1)
        expression_layout.addWidget(QLabel("Output Blue"), 2, 0)
        expression_layout.addWidget(self.blue_expr_input, 2, 1)
        expression_group.setLayout(expression_layout)

        output_group = QGroupBox("Expected RGB output")
        output_layout = QGridLayout()
        output_layout.addWidget(QLabel("Red"), 0, 0)
        output_layout.addWidget(self.output_red_label, 0, 1)
        output_layout.addWidget(QLabel("Green"), 1, 0)
        output_layout.addWidget(self.output_green_label, 1, 1)
        output_layout.addWidget(QLabel("Blue"), 2, 0)
        output_layout.addWidget(self.output_blue_label, 2, 1)
        output_layout.addWidget(self.output_details_label, 3, 0, 1, 2)
        output_group.setLayout(output_layout)

        pipeline_group = QGroupBox("Pipeline")
        pipeline_layout = QVBoxLayout()
        pipeline_layout.addWidget(QLabel("Committed steps"))
        pipeline_layout.addWidget(self.pipeline_list)

        pipeline_buttons = QGridLayout()
        add_step_button = QPushButton("Add Current Step")
        add_step_button.clicked.connect(self.add_current_step_to_pipeline)
        pipeline_buttons.addWidget(add_step_button, 0, 0)

        new_draft_button = QPushButton("New Draft Step")
        new_draft_button.clicked.connect(self.start_new_pipeline_draft)
        pipeline_buttons.addWidget(new_draft_button, 0, 1)

        self.remove_step_button = QPushButton("Remove Selected")
        self.remove_step_button.clicked.connect(self.remove_selected_pipeline_step)
        pipeline_buttons.addWidget(self.remove_step_button, 1, 0)

        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.clicked.connect(lambda: self.move_selected_pipeline_step(-1))
        pipeline_buttons.addWidget(self.move_up_button, 1, 1)

        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.clicked.connect(lambda: self.move_selected_pipeline_step(1))
        pipeline_buttons.addWidget(self.move_down_button, 2, 0)

        clear_pipeline_button = QPushButton("Clear Pipeline")
        clear_pipeline_button.clicked.connect(self.clear_pipeline)
        pipeline_buttons.addWidget(clear_pipeline_button, 2, 1)

        pipeline_layout.addLayout(pipeline_buttons)
        pipeline_layout.addWidget(self.pipeline_help_label)
        pipeline_group.setLayout(pipeline_layout)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Images in folder"))
        left_layout.addWidget(self.image_list)
        left_layout.addWidget(filter_group)
        left_layout.addWidget(expression_group)
        left_layout.addWidget(output_group)
        left_layout.addWidget(pipeline_group)
        left_layout.addStretch(1)

        original_layout = QVBoxLayout()
        original_layout.addWidget(QLabel("Original"))
        original_layout.addWidget(self.original_label)

        filtered_layout = QVBoxLayout()
        filtered_layout.addWidget(QLabel("Output"))
        filtered_layout.addWidget(self.filtered_label)

        preview_layout = QHBoxLayout()
        preview_layout.addLayout(original_layout, stretch=1)
        preview_layout.addLayout(filtered_layout, stretch=1)

        stage_group = QGroupBox("Pipeline stage previews")
        stage_layout = QVBoxLayout()
        stage_layout.addWidget(self.pipeline_stage_scroll)
        stage_group.setLayout(stage_layout)

        preview_column = QVBoxLayout()
        preview_column.addLayout(preview_layout, stretch=3)
        preview_column.addWidget(stage_group, stretch=3)

        content_layout = QHBoxLayout()
        content_layout.addLayout(left_layout, stretch=0)
        content_layout.addLayout(preview_column, stretch=1)

        root_layout = QVBoxLayout()
        root_layout.addLayout(controls_layout)
        root_layout.addLayout(content_layout)

        tab.setLayout(root_layout)
        return tab

    def _build_batch_tab(self) -> QWidget:
        tab = QWidget()

        select_input_button = QPushButton("Select Input Folder")
        select_input_button.clicked.connect(self.select_batch_input_folder)

        select_output_button = QPushButton("Select Output Folder")
        select_output_button.clicked.connect(self.select_batch_output_folder)

        process_button = QPushButton("Process Folder")
        process_button.clicked.connect(self.process_batch_folder)

        controls_layout = QVBoxLayout()
        controls_layout.addWidget(select_input_button)
        controls_layout.addWidget(self.batch_input_label)
        controls_layout.addSpacing(8)
        controls_layout.addWidget(select_output_button)
        controls_layout.addWidget(self.batch_output_label)
        controls_layout.addSpacing(16)
        controls_layout.addWidget(QLabel("Current batch configuration"))
        controls_layout.addWidget(self.batch_summary_label)
        controls_layout.addSpacing(16)
        controls_layout.addWidget(process_button)
        controls_layout.addStretch(1)

        status_group = QGroupBox("Batch status")
        status_layout = QVBoxLayout()
        status_layout.addWidget(self.batch_status_label)
        status_group.setLayout(status_layout)

        root_layout = QHBoxLayout()
        root_layout.addLayout(controls_layout, stretch=0)
        root_layout.addWidget(status_group, stretch=1)

        tab.setLayout(root_layout)
        return tab

    def on_filter_toggled(self, checked: bool) -> None:
        if not checked or self._syncing_operation_editor:
            return

        self.persist_editor_to_selected_pipeline_step()
        self.update_operation_output_preview()
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def capture_current_operation(self) -> PipelineOperation:
        return PipelineOperation(
            mode=self.get_selected_filter_mode(),
            red_expr=self.red_expr_input.text().strip() or "r",
            green_expr=self.green_expr_input.text().strip() or "g",
            blue_expr=self.blue_expr_input.text().strip() or "b",
        )

    def get_selected_filter_mode(self) -> str:
        if self.gray_radio.isChecked():
            return MODE_GRAYSCALE
        return MODE_CUSTOM

    def load_operation_into_editor(self, operation: PipelineOperation) -> None:
        self._syncing_operation_editor = True
        self.set_filter_mode(operation.mode)
        self.red_expr_input.setText(operation.red_expr)
        self.green_expr_input.setText(operation.green_expr)
        self.blue_expr_input.setText(operation.blue_expr)
        self._syncing_operation_editor = False
        self.update_operation_output_preview()

    def set_filter_mode(self, mode: str) -> None:
        radio_by_mode = {
            MODE_GRAYSCALE: self.gray_radio,
            MODE_CUSTOM: self.custom_radio,
        }
        radio_by_mode.get(mode, self.custom_radio).setChecked(True)

    def update_operation_output_preview(self) -> None:
        operation = self.capture_current_operation()
        red_expr, green_expr, blue_expr = self.get_operation_output_expressions(operation)

        self.output_red_label.setText(red_expr)
        self.output_green_label.setText(green_expr)
        self.output_blue_label.setText(blue_expr)

        is_custom = operation.mode == MODE_CUSTOM
        self.red_expr_input.setEnabled(is_custom)
        self.green_expr_input.setEnabled(is_custom)
        self.blue_expr_input.setEnabled(is_custom)

        if is_custom:
            self.output_details_label.setText("The pipeline will evaluate these expressions against the current image.")
        else:
            self.output_details_label.setText(
                "Grayscale uses the fixed weights "
                f"{GRAYSCALE_WEIGHTS[0]}/{GRAYSCALE_WEIGHTS[1]}/{GRAYSCALE_WEIGHTS[2]} and writes the same value "
                "into red, green, and blue."
            )

    def get_operation_output_expressions(self, operation: PipelineOperation) -> tuple[str, str, str]:
        if operation.mode == MODE_GRAYSCALE:
            return (GRAYSCALE_EXPR, GRAYSCALE_EXPR, GRAYSCALE_EXPR)
        return (operation.red_expr, operation.green_expr, operation.blue_expr)

    def add_current_step_to_pipeline(self) -> None:
        operation = self.capture_current_operation()
        self.pipeline_operations.append(operation)
        self.refresh_pipeline_list(select_index=len(self.pipeline_operations) - 1)
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def start_new_pipeline_draft(self) -> None:
        self.clear_pipeline_selection()
        self.update_pipeline_buttons()
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def remove_selected_pipeline_step(self) -> None:
        index = self.pipeline_list.currentRow()
        if index < 0 or index >= len(self.pipeline_operations):
            return

        del self.pipeline_operations[index]
        next_index = min(index, len(self.pipeline_operations) - 1)
        self.refresh_pipeline_list(select_index=next_index if next_index >= 0 else None)
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def move_selected_pipeline_step(self, offset: int) -> None:
        index = self.pipeline_list.currentRow()
        new_index = index + offset
        if index < 0 or new_index < 0 or new_index >= len(self.pipeline_operations):
            return

        self.pipeline_operations[index], self.pipeline_operations[new_index] = (
            self.pipeline_operations[new_index],
            self.pipeline_operations[index],
        )
        self.refresh_pipeline_list(select_index=new_index)
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def clear_pipeline(self) -> None:
        self.pipeline_operations.clear()
        self.refresh_pipeline_list(select_index=None)
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def refresh_pipeline_list(self, select_index: int | None) -> None:
        self.pipeline_list.blockSignals(True)
        self.pipeline_list.clear()
        for index, operation in enumerate(self.pipeline_operations, start=1):
            QListWidgetItem(self.format_pipeline_item_label(index, operation), self.pipeline_list)
        self.pipeline_list.blockSignals(False)

        if select_index is None or not self.pipeline_operations:
            self.clear_pipeline_selection()
        else:
            self.pipeline_list.setCurrentRow(select_index)

        self.update_pipeline_buttons()

    def clear_pipeline_selection(self) -> None:
        self.pipeline_list.blockSignals(True)
        self.pipeline_list.clearSelection()
        self.pipeline_list.setCurrentRow(-1)
        self.pipeline_list.blockSignals(False)

    def update_pipeline_buttons(self) -> None:
        index = self.pipeline_list.currentRow()
        has_selection = 0 <= index < len(self.pipeline_operations)
        self.remove_step_button.setEnabled(has_selection)
        self.move_up_button.setEnabled(has_selection and index > 0)
        self.move_down_button.setEnabled(has_selection and index < len(self.pipeline_operations) - 1)

    def persist_editor_to_selected_pipeline_step(self) -> None:
        index = self.pipeline_list.currentRow()
        if self._syncing_operation_editor or index < 0 or index >= len(self.pipeline_operations):
            return

        self.pipeline_operations[index] = self.capture_current_operation()
        item = self.pipeline_list.item(index)
        if item is not None:
            item.setText(self.format_pipeline_item_label(index + 1, self.pipeline_operations[index]))

    def on_pipeline_selection_changed(self, index: int) -> None:
        self.update_pipeline_buttons()

        if 0 <= index < len(self.pipeline_operations):
            self.load_operation_into_editor(self.pipeline_operations[index])
        else:
            self.update_operation_output_preview()

        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def format_pipeline_item_label(self, index: int, operation: PipelineOperation) -> str:
        return f"{index}. {self.describe_operation(operation)}"

    def describe_operation(self, operation: PipelineOperation) -> str:
        if operation.mode == MODE_GRAYSCALE:
            return f"Grayscale ({GRAYSCALE_WEIGHTS[0]}/{GRAYSCALE_WEIGHTS[1]}/{GRAYSCALE_WEIGHTS[2]})"
        return f"Custom RGB (R={operation.red_expr}, G={operation.green_expr}, B={operation.blue_expr})"

    def open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select image folder")
        if not folder:
            return

        self.current_directory = Path(folder)
        self.folder_label.setText(str(self.current_directory))
        self._load_directory_images()

    def _load_directory_images(self) -> None:
        if self.current_directory is None:
            return

        self.image_paths = sorted(
            [
                path
                for path in self.current_directory.iterdir()
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
            ],
            key=lambda path: path.name.lower(),
        )

        self.image_list.clear()
        for image_path in self.image_paths:
            QListWidgetItem(image_path.name, self.image_list)

        if not self.image_paths:
            QMessageBox.information(
                self, "No images found", "The selected folder does not contain supported image files."
            )
            self.clear_images()
            return

        self.image_list.setCurrentRow(0)

    def open_image_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff)",
        )
        if not file_name:
            return

        path = Path(file_name)
        self.current_directory = path.parent
        self.folder_label.setText(str(self.current_directory))
        self._load_directory_images()

        try:
            index = self.image_paths.index(path)
        except ValueError:
            self.load_image(path)
            return

        self.image_list.setCurrentRow(index)

    def on_image_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.image_paths):
            return

        self.load_image(self.image_paths[index])

    def load_image(self, image_path: Path) -> None:
        try:
            self.original_image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open image:\n{exc}")
            return

        self.preview_image = self.original_image.copy()
        self.preview_image.thumbnail(DISPLAY_MAX_SIZE)

        self.show_original_image()
        self.refresh_filtered_image()

    def show_original_image(self) -> None:
        if self.preview_image is None:
            return

        self.original_pixmap = self._to_pixmap(self.preview_image)
        self.original_label.setPixmap(self.original_pixmap)
        self.original_label.setText("")

    def refresh_filtered_image(self) -> None:
        if self.preview_image is None:
            self.refresh_pipeline_stage_previews([])
            return

        try:
            final_image, stage_images = self.build_preview_images(self.preview_image)
        except Exception as exc:
            self.filtered_pixmap = None
            self.filtered_label.clear()
            self.filtered_label.setText(f"Preview unavailable:\n{exc}")
            self.refresh_pipeline_stage_previews([])
            return

        self.filtered_pixmap = self._to_pixmap(final_image)
        self.filtered_label.setPixmap(self.filtered_pixmap)
        self.filtered_label.setText("")
        self.refresh_pipeline_stage_previews(stage_images)

    def build_preview_images(self, image: Image.Image) -> tuple[Image.Image, list[tuple[str, Image.Image]]]:
        base_image = image.copy()
        stage_images: list[tuple[str, Image.Image]] = []

        if self.pipeline_operations:
            working_image = base_image
            for index, operation in enumerate(self.pipeline_operations, start=1):
                working_image = self.apply_operation(working_image, operation)
                stage_images.append((f"Step {index}: {self.describe_operation(operation)}", working_image.copy()))

            final_image = working_image.copy()

            if self.pipeline_list.currentRow() == -1:
                draft_operation = self.capture_current_operation()
                draft_preview = self.apply_operation(working_image.copy(), draft_operation)
                stage_images.append((f"Draft: {self.describe_operation(draft_operation)}", draft_preview))

            return final_image, stage_images

        current_operation = self.capture_current_operation()
        final_image = self.apply_operation(base_image, current_operation)
        stage_images.append((f"Current: {self.describe_operation(current_operation)}", final_image.copy()))
        return final_image, stage_images

    def refresh_pipeline_stage_previews(self, stage_images: list[tuple[str, Image.Image]]) -> None:
        while self.pipeline_stage_layout.count():
            item = self.pipeline_stage_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not stage_images:
            placeholder = QLabel("Load an image to preview how each pipeline step changes it.")
            placeholder.setWordWrap(True)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pipeline_stage_layout.addWidget(placeholder)
            return

        for title, image in stage_images:
            self.pipeline_stage_layout.addWidget(self.create_stage_preview_card(title, image))

        self.pipeline_stage_layout.addStretch(1)

    def create_stage_preview_card(self, title: str, image: Image.Image) -> QWidget:
        card = QGroupBox(title)
        layout = QVBoxLayout()

        label = StageImageLabel("Preview unavailable")
        preview_image = image.copy()
        preview_image.thumbnail(STAGE_PREVIEW_SIZE)
        label.setPixmap(self._to_pixmap(preview_image))
        label.setText("")

        layout.addWidget(label)
        card.setLayout(layout)
        return card

    def apply_operation(self, image: Image.Image, operation: PipelineOperation) -> Image.Image:
        red_channel, green_channel, blue_channel = image.split()

        if operation.mode == MODE_GRAYSCALE:
            red_weight, green_weight, blue_weight = GRAYSCALE_WEIGHTS
            total = max(red_weight + green_weight + blue_weight, 1)

            r_scaled = red_channel.point(lambda x: x * red_weight / total)
            g_scaled = green_channel.point(lambda x: x * green_weight / total)
            b_scaled = blue_channel.point(lambda x: x * blue_weight / total)

            gray = Image.merge("RGB", (r_scaled, g_scaled, b_scaled)).convert("L")
            return Image.merge("RGB", (gray, gray, gray))

        if operation.mode == MODE_CUSTOM:
            return self.apply_custom_expression_filter(image, operation)

        return image.copy()

    def apply_batch_configuration(self, image: Image.Image) -> Image.Image:
        if not self.pipeline_operations:
            return self.apply_operation(image, self.capture_current_operation())

        working_image = image
        for operation in self.pipeline_operations:
            working_image = self.apply_operation(working_image, operation)
        return working_image

    def _to_pixmap(self, image: Image.Image) -> QPixmap:
        qt_image = ImageQt(image)
        return QPixmap.fromImage(qt_image)

    def clear_images(self) -> None:
        self.original_image = None
        self.preview_image = None
        self.original_pixmap = None
        self.filtered_pixmap = None
        self.original_label.clear()
        self.filtered_label.clear()
        self.original_label.setText("No image selected")
        self.filtered_label.setText("No image selected")
        self.refresh_pipeline_stage_previews([])

    def update_batch_settings_summary(self) -> None:
        if self.pipeline_operations:
            lines = [
                f"Mode: pipeline ({len(self.pipeline_operations)} step(s))",
                *[
                    f"{index}. {self.describe_operation(operation)}"
                    for index, operation in enumerate(self.pipeline_operations, start=1)
                ],
            ]
            if self.pipeline_list.currentRow() == -1:
                lines.append("Draft step preview is shown in Prototype, but batch uses committed steps only.")
        else:
            operation = self.capture_current_operation()
            lines = [
                "Mode: single operation",
                f"Step 1. {self.describe_operation(operation)}",
            ]

        self.batch_summary_label.setText("\n".join(lines))

    def select_batch_input_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select batch input folder")
        if not folder:
            return

        self.batch_input_directory = Path(folder)
        self.batch_input_label.setText(str(self.batch_input_directory))

    def select_batch_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select batch output folder")
        if not folder:
            return

        self.batch_output_directory = Path(folder)
        self.batch_output_label.setText(str(self.batch_output_directory))

    def process_batch_folder(self) -> None:
        if self.batch_input_directory is None:
            QMessageBox.warning(self, "Missing input folder", "Select a batch input folder first.")
            return

        if self.batch_output_directory is None:
            QMessageBox.warning(self, "Missing output folder", "Select a batch output folder first.")
            return

        input_paths = sorted(
            [
                path
                for path in self.batch_input_directory.iterdir()
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
            ],
            key=lambda path: path.name.lower(),
        )

        if not input_paths:
            QMessageBox.information(
                self, "No images found", "The batch input folder does not contain supported image files."
            )
            return

        processed_count = 0
        failed_paths: list[str] = []

        for image_path in input_paths:
            try:
                image = Image.open(image_path).convert("RGB")
                filtered = self.apply_batch_configuration(image)
                output_path = self.batch_output_directory / f"{image_path.stem}{BATCH_SUFFIX}{image_path.suffix}"
                filtered.save(output_path)
                processed_count += 1
            except Exception:
                failed_paths.append(image_path.name)

        status = f"Processed {processed_count} image(s)."
        if failed_paths:
            status += f" Failed: {', '.join(failed_paths)}"
        self.batch_status_label.setText(status)

        if failed_paths:
            QMessageBox.warning(self, "Batch finished with errors", status)
        else:
            QMessageBox.information(self, "Batch complete", status)

    def on_custom_expression_changed(self) -> None:
        if self._syncing_operation_editor:
            return

        self.custom_radio.setChecked(True)
        self.persist_editor_to_selected_pipeline_step()
        self.update_operation_output_preview()
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def apply_custom_expression_filter(self, image: Image.Image, operation: PipelineOperation) -> Image.Image:
        rgb = np.asarray(image, dtype=np.float32)
        r = rgb[:, :, 0]
        g = rgb[:, :, 1]
        b = rgb[:, :, 2]

        red_out = self.evaluate_channel_expression(operation.red_expr, r, g, b)
        green_out = self.evaluate_channel_expression(operation.green_expr, r, g, b)
        blue_out = self.evaluate_channel_expression(operation.blue_expr, r, g, b)

        output = np.stack([red_out, green_out, blue_out], axis=2)
        output = np.clip(output, 0, 255).astype(np.uint8)
        return Image.fromarray(output, mode="RGB")

    def evaluate_channel_expression(
        self,
        expression: str,
        r: np.ndarray,
        g: np.ndarray,
        b: np.ndarray,
    ) -> np.ndarray:
        allowed_names = {
            "r": r,
            "g": g,
            "b": b,
            "min": np.minimum,
            "max": np.maximum,
            "abs": np.abs,
            "clip": np.clip,
        }
        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.FloorDiv,
            ast.Mod,
            ast.Pow,
            ast.USub,
            ast.UAdd,
            ast.Call,
            ast.Load,
            ast.Name,
            ast.Constant,
            ast.Tuple,
        )

        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(f"Unsupported expression syntax: {expression}")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in {"min", "max", "abs", "clip"}:
                    raise ValueError(f"Unsupported function in expression: {expression}")
            if isinstance(node, ast.Name) and node.id not in allowed_names:
                raise ValueError(f"Unsupported name in expression: {node.id}")

        return eval(compile(tree, "<channel-expression>", "eval"), {"__builtins__": {}}, allowed_names)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
