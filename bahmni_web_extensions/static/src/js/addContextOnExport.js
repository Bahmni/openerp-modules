openerp.bahmni_web_extensions.addContextOnExport = function(instance) {
    instance.web.DataExport.include({
        init: function(parent, dataset) {
            this._super(parent, dataset);
            this.selectedIds = parent.groups && parent.groups.get_selection().ids || [];
        },

        on_click_export_data: function() {
            var self = this;
            var exported_fields = this.$el.find('#fields_list option').map(function () {
                // DOM property is textContent, but IE8 only knows innerText
                return {name: self.records[this.value] || this.value,
                        label: this.textContent || this.innerText};
            }).get();

            if (_.isEmpty(exported_fields)) {
                alert(_t("Please select fields to export..."));
                return;
            }

            exported_fields.unshift({name: 'id', label: 'External ID'});
            var export_format = this.$el.find("#export_format").val();
            instance.web.blockUI();
            this.session.get_file({
                url: '/web/export/' + export_format,
                data: {data: JSON.stringify({
                    model: this.dataset.model,
                    fields: exported_fields,
                    ids: this.selectedIds,
                    domain: this.dataset._model._domain,
                    context: this.dataset._model._context,
                    import_compat: Boolean(
                        this.$el.find("#import_compat").val())
                })},
                complete: instance.web.unblockUI
            });
        }
    })
}
