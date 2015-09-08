import logging

from reference_data_service import reference_data_service

_logger = logging.getLogger(__name__)


class lab_panel_service(reference_data_service):
    _name = "lab.panel.service"
    _auto = False

    def _get_category(self):
        return "Panel"

    def _get_category_hierarchy(self):
        return ["Lab", "Services", "All Products"]

