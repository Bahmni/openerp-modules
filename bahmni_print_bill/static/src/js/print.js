openerp.bahmni_sale_discount = function(instance) {

    var QWeb = instance.web.qweb;
    instance.bahmni_sale_discount.print = instance.web.form.FieldChar.extend({
        template: "test_button",
        init: function(parent, action) {
            this._super.apply(this, arguments);
            this._start = null;
            this.parent = parent
       },

       start: function() {
            $('button#bstart').click($.proxy(this.fetchAndPrint, this));  //link button to function
        },

        fetchAndPrint: function() {
            var self = this;
            this.rpc('/invoice/bill', {voucher_id: this.parent.datarecord.id}).done(function(bill) {self.printReceipt(bill)})
        },

        printReceipt: function(context) {
            var $ht = $(QWeb.render("Bill", context))[0];
            var hiddenFrame = $("#printBillFrame")[0]
    
            var doc = hiddenFrame.contentWindow.document.open("text/html", "replace");

            doc.write($ht.innerHTML);
            doc.close();
            hiddenFrame.contentWindow.print();

            window.location = "/?ts=1370260915528#page=0&limit=80&view_type=list&model=sale.order&menu_id=296&action=373"

            // $ht.print();
        },
    });

    instance.web.form.widgets.add('print', 'instance.bahmni_sale_discount.print');
}



