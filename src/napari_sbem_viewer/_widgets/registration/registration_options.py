from qtpy.QtWidgets import QVBoxLayout, QVBoxLayout, QGroupBox, QComboBox, QStackedWidget

from napari_sbem_viewer._widgets.registration import AlignPlanes, ManualRegistration2, PrecomputedTransformation


class RegistrationOptions(QGroupBox):
    def __init__(self, viewer, parent=None):
        # TODO: Move RegistrationOptions into Registration class
        super().__init__("Registration options", parent=parent)
        self.viewer = viewer
        self.setLayout(QVBoxLayout())
        self.widgets_combo_box = QComboBox()
        self.stacked_widget = QStackedWidget()
        
        self.align_planes = AlignPlanes(self.viewer, parent=self)
        self.widgets_combo_box.addItem('Align planes')
        self.stacked_widget.addWidget(self.align_planes)
        
        # self.precomputed_transformation = PrecomputedTransformation(self.viewer, parent=self)
        # self.widgets_combo_box.addItem('Precomputed transformation')
        # self.stacked_widget.addWidget(self.precomputed_transformation)
        
        self.manual_registration = ManualRegistration2(self.viewer, parent=self)
        self.manual_registration.layout().setContentsMargins(0, 0, 0, 0)
        self.widgets_combo_box.addItem('Manual registration')
        self.stacked_widget.addWidget(self.manual_registration)
        
        self.widgets_combo_box.activated[int].connect(self.stacked_widget.setCurrentIndex)
        self.layout().addWidget(self.widgets_combo_box)
        self.layout().addWidget(self.stacked_widget)
        
        