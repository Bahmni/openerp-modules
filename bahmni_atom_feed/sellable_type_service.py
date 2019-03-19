import logging

from reference_data_service import reference_data_service

_logger = logging.getLogger(__name__)


class sellable_type_service(reference_data_service):
    _name = "sellable.type.service"
    _auto = False

    def _get_category(self, ref_category=None):
    	if (not (ref_category and ref_category.strip())):
        	return "Others"
    	return ref_category

    def _get_category_hierarchy(self):
        return ["Services", "All Products"]