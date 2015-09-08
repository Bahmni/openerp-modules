import logging

from reference_data_service import reference_data_service

_logger = logging.getLogger(__name__)


class radiology_test_service(reference_data_service):
    _name = "radiology.test.service"
    _auto = False

    def _get_category(self):
        return "Radiology"

    def _get_category_hierarchy(self):
        return ["Services", "All Products"]
