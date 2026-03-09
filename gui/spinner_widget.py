from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QConicalGradient
from PySide6.QtWidgets import (
    QWidget
)


class SpinnerWidget(QWidget):

    """A custom spinning loader widget."""
    
    def __init__(self, parent=None, color=QColor(230, 80, 80), line_width=4):
        super().__init__(parent)
        self._angle = 0
        self._color = color
        self._line_width = line_width
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(40, 40)
        self.setAttribute(Qt.WA_TranslucentBackground)
    
    def _rotate(self):
        self._angle = (self._angle + 10) % 360
        self.update()
    
    def start(self):
        self._timer.start(16)  # ~60 FPS
        self.show()
    
    def stop(self):
        self._timer.stop()
        self.hide()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate the drawing area
        side = min(self.width(), self.height())
        margin = self._line_width + 2
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)
        
        # Create gradient for the arc
        gradient = QConicalGradient(rect.center(), -self._angle)
        gradient.setColorAt(0, self._color)
        gradient.setColorAt(0.7, QColor(self._color.red(), self._color.green(), self._color.blue(), 50))
        gradient.setColorAt(1, QColor(self._color.red(), self._color.green(), self._color.blue(), 0))
        
        # Draw the spinning arc
        pen = QPen()
        pen.setBrush(gradient)
        pen.setWidth(self._line_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # Draw arc (270 degrees visible)
        start_angle = int(self._angle * 16)
        span_angle = 270 * 16
        painter.drawArc(rect, start_angle, span_angle)
