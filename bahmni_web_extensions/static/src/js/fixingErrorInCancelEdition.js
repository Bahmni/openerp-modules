openerp.bahmni_web_extensions.fixingErrorInCancelEdition = function(instance) {
    instance.web.ListView.include({

        cancel_edition: function (force) {
            var self = this;
            return this.with_event('cancel', {
                editor: this.editor,
                form: this.editor.form,
                cancel: false
            }, function () {
                return this.editor.cancel(force).then(function (attrs) {
                    if(attrs == null){
                        return;
                    }
                    if (attrs && attrs.id) {
                        var record = self.records.get(attrs.id);
                        if (!record) {
                            // Record removed by third party during edition
                            return
                        }
                        return self.reload_record(record);
                    }
                    var to_delete = self.records.find(function (r) {
                        return !r.get('id');
                    });
                    if (to_delete) {
                        self.records.remove(to_delete);
                    }
                });
            });
        },
    });
}
