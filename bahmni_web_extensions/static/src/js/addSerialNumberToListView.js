openerp.bahmni_web_extensions.addSerialNumberToListView = function(instance) {
    var QWeb = instance.web.qweb;
    instance.web.ListView.List.include({
        render_record: function (record) {
            var self = this;
            var index = this.records.indexOf(record);
            return QWeb.render('ListView.row', {
                columns: this.columns,
                options: this.options,
                record: record,
                rowIndex: index + 1, //CHANGE
                row_parity: (index % 2 === 0) ? 'even' : 'odd',
                view: this.view,
                render_cell: function () {
                    return self.render_cell.apply(self, arguments); }
            });
        }
    });
}