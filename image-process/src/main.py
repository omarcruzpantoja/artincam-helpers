from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageMath
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
DISPLAY_MAX_SIZE = (500, 500)
BATCH_SUFFIX = "_processed"
GRAYSCALE_WEIGHTS = (30, 59, 11)


class ImageLabel(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setScaledContents(False)
        self.setWordWrap(True)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Filter Viewer")
        self.resize(1400, 860)
        self.setMinimumSize(1080, 720)

        self.current_directory: Path | None = None
        self.image_paths: list[Path] = []
        self.original_image: Image.Image | None = None
        self.preview_image: Image.Image | None = None
        self.original_pixmap: QPixmap | None = None
        self.filtered_pixmap: QPixmap | None = None

        self.batch_input_directory: Path | None = None
        self.batch_output_directory: Path | None = None

        self.image_list = QListWidget()
        self.image_list.currentRowChanged.connect(self.on_image_selected)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setWordWrap(True)

        self.original_label = ImageLabel("No image selected")
        self.filtered_label = ImageLabel("No image selected")

        self.gray_radio = QRadioButton("Grayscale")
        self.red_radio = QRadioButton("Red pixels only")
        self.green_radio = QRadioButton("Green pixels only")
        self.blue_radio = QRadioButton("Blue pixels only")
        self.custom_radio = QRadioButton("Custom RGB scaling")
        self.custom_radio.setChecked(True)

        for radio in [
            self.gray_radio,
            self.red_radio,
            self.green_radio,
            self.blue_radio,
            self.custom_radio,
        ]:
            radio.toggled.connect(self.on_filter_toggled)

        self.red_slider, self.red_value_label = self._create_channel_slider(100)
        self.green_slider, self.green_value_label = self._create_channel_slider(100)
        self.blue_slider, self.blue_value_label = self._create_channel_slider(100)
        self._syncing_filter_presets = False

        self.red_slider.valueChanged.connect(lambda value: self.on_slider_changed("red", value))
        self.green_slider.valueChanged.connect(lambda value: self.on_slider_changed("green", value))
        self.blue_slider.valueChanged.connect(lambda value: self.on_slider_changed("blue", value))

        self.batch_input_label = QLabel("No input folder selected")
        self.batch_input_label.setWordWrap(True)

        self.batch_output_label = QLabel("No output folder selected")
        self.batch_output_label.setWordWrap(True)

        self.batch_summary_label = QLabel()
        self.batch_summary_label.setWordWrap(True)

        self.batch_status_label = QLabel("No batch job has been run yet")
        self.batch_status_label.setWordWrap(True)

        self._build_ui()
        self.update_channel_labels()
        self.update_batch_settings_summary()

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

        filter_group = QGroupBox("Filter options")
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(self.gray_radio)
        filter_layout.addWidget(self.red_radio)
        filter_layout.addWidget(self.green_radio)
        filter_layout.addWidget(self.blue_radio)
        filter_layout.addWidget(self.custom_radio)
        filter_group.setLayout(filter_layout)

        slider_group = QGroupBox("Channel values")
        slider_layout = QGridLayout()
        slider_layout.addWidget(QLabel("Red"), 0, 0)
        slider_layout.addWidget(self.red_slider, 0, 1)
        slider_layout.addWidget(self.red_value_label, 0, 2)
        slider_layout.addWidget(QLabel("Green"), 1, 0)
        slider_layout.addWidget(self.green_slider, 1, 1)
        slider_layout.addWidget(self.green_value_label, 1, 2)
        slider_layout.addWidget(QLabel("Blue"), 2, 0)
        slider_layout.addWidget(self.blue_slider, 2, 1)
        slider_layout.addWidget(self.blue_value_label, 2, 2)

        reset_sliders_button = QPushButton("Reset Sliders")
        reset_sliders_button.clicked.connect(self.reset_sliders)
        slider_layout.addWidget(reset_sliders_button, 3, 0, 1, 3)
        slider_group.setLayout(slider_layout)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Images in folder"))
        left_layout.addWidget(self.image_list)
        left_layout.addWidget(filter_group)
        left_layout.addWidget(slider_group)
        left_layout.addStretch(1)

        original_layout = QVBoxLayout()
        original_layout.addWidget(QLabel("Original"))
        original_layout.addWidget(self.original_label)

        filtered_layout = QVBoxLayout()
        filtered_layout.addWidget(QLabel("Altered"))
        filtered_layout.addWidget(self.filtered_label)

        preview_layout = QHBoxLayout()
        preview_layout.addLayout(original_layout, stretch=1)
        preview_layout.addLayout(filtered_layout, stretch=1)

        content_layout = QHBoxLayout()
        content_layout.addLayout(left_layout, stretch=0)
        content_layout.addLayout(preview_layout, stretch=1)

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
        controls_layout.addWidget(QLabel("Current settings from Prototype tab"))
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

    def _create_channel_slider(self, initial_value: int) -> tuple[QSlider, QLabel]:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 200)
        slider.setValue(initial_value)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(10)

        value_label = QLabel()
        value_label.setMinimumWidth(56)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return slider, value_label

    def on_slider_changed(self, _channel: str, _value: int) -> None:
        if self._syncing_filter_presets:
            self.update_channel_labels()
            return

        self.custom_radio.setChecked(True)
        self.update_channel_labels()
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def update_channel_labels(self) -> None:
        self.red_value_label.setText(f"{self.red_slider.value()}%")
        self.green_value_label.setText(f"{self.green_slider.value()}%")
        self.blue_value_label.setText(f"{self.blue_slider.value()}%")

    def reset_sliders(self) -> None:
        self.set_slider_values(100, 100, 100)
        self.custom_radio.setChecked(True)
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

    def sync_sliders_to_selected_filter(self) -> None:
        if self.gray_radio.isChecked():
            self.set_slider_values(*GRAYSCALE_WEIGHTS)
            return

        if self.red_radio.isChecked():
            self.set_slider_values(100, 0, 0)
            return

        if self.green_radio.isChecked():
            self.set_slider_values(0, 100, 0)
            return

        if self.blue_radio.isChecked():
            self.set_slider_values(0, 0, 100)
            return

    def set_slider_values(self, red: int, green: int, blue: int) -> None:
        self._syncing_filter_presets = True
        self.red_slider.setValue(red)
        self.green_slider.setValue(green)
        self.blue_slider.setValue(blue)
        self._syncing_filter_presets = False
        self.update_channel_labels()

    def on_filter_toggled(self, checked: bool) -> None:
        if not checked:
            return

        self.sync_sliders_to_selected_filter()
        self.refresh_filtered_image()
        self.update_batch_settings_summary()

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
            return

        filtered = self.apply_filter(self.preview_image)
        self.filtered_pixmap = self._to_pixmap(filtered)
        self.filtered_label.setPixmap(self.filtered_pixmap)
        self.filtered_label.setText("")

    def apply_filter(self, image: Image.Image) -> Image.Image:
        red_channel, green_channel, blue_channel = image.split()

        if self.gray_radio.isChecked():
            rw = self.red_slider.value()
            gw = self.green_slider.value()
            bw = self.blue_slider.value()

            total = max(rw + gw + bw, 1)

            # scale each channel using a lookup table
            r_scaled = red_channel.point(lambda x: x * rw / total)
            g_scaled = green_channel.point(lambda x: x * gw / total)
            b_scaled = blue_channel.point(lambda x: x * bw / total)

            gray = Image.merge("RGB", (r_scaled, g_scaled, b_scaled)).convert("L")

            return Image.merge("RGB", (gray, gray, gray))

        if self.red_radio.isChecked():
            red_channel = self.scale_channel(red_channel, self.red_slider.value())
            zero_channel = Image.new("L", red_channel.size, 0)
            return Image.merge("RGB", (red_channel, zero_channel, zero_channel))

        if self.green_radio.isChecked():
            green_channel = self.scale_channel(green_channel, self.green_slider.value())
            zero_channel = Image.new("L", green_channel.size, 0)
            return Image.merge("RGB", (zero_channel, green_channel, zero_channel))

        if self.blue_radio.isChecked():
            blue_channel = self.scale_channel(blue_channel, self.blue_slider.value())
            zero_channel = Image.new("L", blue_channel.size, 0)
            return Image.merge("RGB", (zero_channel, zero_channel, blue_channel))

        red_channel = self.scale_channel(red_channel, self.red_slider.value())
        green_channel = self.scale_channel(green_channel, self.green_slider.value())
        blue_channel = self.scale_channel(blue_channel, self.blue_slider.value())
        return Image.merge("RGB", (red_channel, green_channel, blue_channel))

    def scale_channel(self, channel: Image.Image, percent: int) -> Image.Image:
        factor = percent / 100.0
        lookup_table = [min(255, max(0, int(index * factor))) for index in range(256)]
        return channel.point(lookup_table)

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

    def get_filter_mode(self) -> str:
        if self.gray_radio.isChecked():
            return "Grayscale"
        if self.red_radio.isChecked():
            return "Red pixels only"
        if self.green_radio.isChecked():
            return "Green pixels only"
        if self.blue_radio.isChecked():
            return "Blue pixels only"
        return "Custom RGB scaling"

    def update_batch_settings_summary(self) -> None:
        label_name = "Channel weights" if self.gray_radio.isChecked() else "Channel values"
        summary = (
            f"Mode: {self.get_filter_mode()}"
            f"{label_name}:"
            f"Red: {self.red_slider.value()}%"
            f"Green: {self.green_slider.value()}%"
            f"Blue: {self.blue_slider.value()}%"
        )
        self.batch_summary_label.setText(summary)

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
                filtered = self.apply_filter(image)
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


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
