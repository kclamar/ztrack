from abc import abstractmethod
from pathlib import Path
from typing import List, Optional

from decord import VideoReader
from PyQt5 import QtCore, QtGui, QtWidgets

from .utils.frame_bar import FrameBar
from ._tracking_image_view import TrackingPlotWidget
from ztrack.utils.file import video_extensions


class MainWindow(QtWidgets.QMainWindow):
    closedSignal = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget = None, *, videoPaths=None, verbose=False):
        super().__init__(parent)
        if videoPaths is None:
            videoPaths = []
        self._videoPaths: List[str] = videoPaths
        self._verbose = verbose
        self._frameBar = FrameBar(self)
        self._useVideoFPS = True
        self._videoReader = None
        self._trackingImageView = TrackingPlotWidget(self)
        self._hBoxLayout = QtWidgets.QHBoxLayout()
        self._hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self._hBoxLayout.addWidget(self._trackingImageView)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.addWidget(self._frameBar)
        self._layout.addLayout(self._hBoxLayout)

        widget = QtWidgets.QWidget(self)
        widget.setLayout(self._layout)
        self.setCentralWidget(widget)

        menuBar = self.menuBar()

        actionOpenFiles = QtWidgets.QAction(self)
        actionOpenFiles.setText("&Open Files")
        actionOpenFiles.setShortcut("Ctrl+O")

        actionOpenFolders = QtWidgets.QAction(self)
        actionOpenFolders.setText("&Open Folders")
        actionOpenFolders.setShortcut("Ctrl+Shift+O")

        actionSetFPS = QtWidgets.QAction(self)
        actionSetFPS.setText("&Set FPS")

        actionAbout = QtWidgets.QAction(self)
        actionAbout.setText("&About")
        actionHelp = QtWidgets.QAction(self)
        actionHelp.setText("&Help")

        fileMenu = menuBar.addMenu("&File")
        viewMenu = menuBar.addMenu("&View")
        helpMenu = menuBar.addMenu("&Help")

        fileMenu.addAction(actionOpenFiles)
        fileMenu.addAction(actionOpenFolders)
        viewMenu.addAction(actionSetFPS)
        helpMenu.addAction(actionAbout)
        helpMenu.addAction(actionHelp)

        actionOpenFiles.triggered.connect(self._openFiles)
        actionOpenFolders.triggered.connect(self._openFolders)
        actionSetFPS.triggered.connect(self._setFPS)
        self._frameBar.valueChanged.connect(self._onFrameChanged)

        self.setMenuBar(menuBar)
        self.setWindowTitle("ztrack")
        self.setAcceptDrops(True)
        self._setEnabled(False)

    @property
    def _currentFrame(self):
        if self._videoReader is None:
            return None
        return self._videoReader[self._frameBar.value].asnumpy()

    def _setEnabled(self, b: bool):
        self.centralWidget().setEnabled(b)
        self._trackingImageView.setEnabled(b)

    @abstractmethod
    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        pass

    @property
    def _currentVideoPath(self) -> Optional[str]:
        if len(self._videoPaths) > 0:
            return self._videoPaths[0]
        return None

    @abstractmethod
    def _onFrameChanged(self):
        pass

    @abstractmethod
    def _openFiles(self):
        pass

    @abstractmethod
    def _openFolders(self):
        pass

    def _setFPS(self):
        def onCheckBoxStateChange(state: int):
            isEnabled = state == 0
            spinBox.setEnabled(isEnabled)
            label.setEnabled(isEnabled)

        def onAccepted():
            self._useVideoFPS = checkBox.isChecked()
            if not self._useVideoFPS:
                self._frameBar.fps = spinBox.value()
            else:
                if self._videoReader is not None:
                    self._frameBar.fps = int(self._videoReader.get_avg_fps())
            dialog.close()

        def onRejected():
            dialog.close()

        dialog = QtWidgets.QDialog(None)
        dialog.setWindowFlags(QtCore.Qt.WindowTitleHint)
        dialog.setWindowTitle("Set FPS")
        label = QtWidgets.QLabel(dialog)
        label.setText("FPS")
        spinBox = QtWidgets.QSpinBox(dialog)
        spinBox.setMinimum(0)
        spinBox.setMaximum(1000)
        spinBox.setValue(self._frameBar.fps)

        formLayout = QtWidgets.QFormLayout()
        formLayout.addRow(label, spinBox)

        checkBox = QtWidgets.QCheckBox(dialog)
        checkBox.setText("Use video FPS")

        buttonBox = QtWidgets.QDialogButtonBox(dialog)
        buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(formLayout)
        layout.addWidget(checkBox)
        layout.addWidget(buttonBox)
        dialog.setLayout(layout)
        dialog.setMinimumWidth(300)

        checkBox.stateChanged.connect(onCheckBoxStateChange)
        buttonBox.accepted.connect(onAccepted)
        buttonBox.rejected.connect(onRejected)

        checkBox.setChecked(self._useVideoFPS)

        dialog.exec()

    def updateVideo(self):
        if self._currentVideoPath is not None:
            self._videoReader = VideoReader(self._currentVideoPath)
            self._frameBar.maximum = len(self._videoReader) - 1
            if self._useVideoFPS:
                self._frameBar.fps = int(self._videoReader.get_avg_fps())
            self._onFrameChanged()
            h, w = self._videoReader[0].shape[:2]
            self._trackingImageView.setRoiDefaultSize(w, h)
            rect = QtCore.QRectF(0, 0, w, h)
            self._trackingImageView.setRoiMaxBounds(rect)
            self._setEnabled(True)
        else:
            self._setEnabled(False)

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.closedSignal.emit()
        super().closeEvent(a0)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            if all([Path(u.toLocalFile()).suffix in video_extensions for u in event.mimeData().urls()]):
                event.accept()
        else:
            event.ignore()
