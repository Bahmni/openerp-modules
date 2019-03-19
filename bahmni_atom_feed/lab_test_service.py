import logging

from reference_data_service import reference_data_service

_logger = logging.getLogger(__name__)


class lab_test_service(reference_data_service):
    _name = "lab.test.service"
    _auto = False

    def _get_category(self, ref_category=None):
        return "Test"

    def _get_category_hierarchy(self):
        return ["Lab", "Services", "All Products"]
